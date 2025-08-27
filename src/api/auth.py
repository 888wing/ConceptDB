"""
Authentication API endpoints
Handles user registration, login, and authentication
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging
from datetime import timedelta

from src.models.user import UserCreate, UserLogin, UserResponse, ApiKeyCreate, ApiKeyResponse
from src.services.auth_service import AuthService
from src.services.quota_service import QuotaService
from src.core.pg_storage import PostgreSQLStorage
import os

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Security scheme for Swagger UI
security = HTTPBearer()

# Initialize services (will be injected from main app)
auth_service: Optional[AuthService] = None
quota_service: Optional[QuotaService] = None
pg_storage: Optional[PostgreSQLStorage] = None


def init_auth_services(storage: PostgreSQLStorage):
    """Initialize authentication services"""
    global auth_service, quota_service, pg_storage
    pg_storage = storage
    auth_service = AuthService(storage=storage)
    quota_service = QuotaService(storage=storage)
    logger.info("Auth services initialized")


# Dependency functions

async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """Extract and validate user from JWT token"""
    if not auth_service:
        raise HTTPException(status_code=500, detail="Auth service not initialized")
    
    token = credentials.credentials
    user = await auth_service.get_current_user(token)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_from_api_key(
    x_api_key: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """Extract and validate user from API key"""
    if not x_api_key:
        return None
    
    if not auth_service:
        raise HTTPException(status_code=500, detail="Auth service not initialized")
    
    # API keys should start with "ck_live_"
    if not x_api_key.startswith("ck_live_"):
        return None
    
    api_key = await auth_service.validate_api_key(x_api_key)
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    
    # Return organization context from API key
    return {
        "organization_id": api_key.organization_id,
        "api_key_id": api_key.id,
        "scopes": api_key.scopes,
        "is_api_key": True
    }


async def get_current_user(
    token_user: Optional[Dict] = None,
    api_key_user: Optional[Dict] = Depends(get_current_user_from_api_key)
) -> Dict[str, Any]:
    """Get current user from either JWT token or API key"""
    # Try API key first
    if api_key_user:
        return api_key_user
    
    # Fall back to JWT token
    if token_user:
        return token_user
    
    # No authentication provided
    raise HTTPException(
        status_code=401,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer, X-API-Key"},
    )


# Public endpoints (no auth required)

@router.post("/register", response_model=Dict[str, Any])
async def register_user(user_data: UserCreate):
    """
    Register a new user and create organization
    """
    try:
        if not auth_service:
            raise HTTPException(status_code=500, detail="Auth service not initialized")
        
        # Create user and organization
        user = await auth_service.create_user(user_data)
        
        # Initialize quota for new organization
        if user.organization_id and quota_service:
            await quota_service.initialize_organization_quota(user.organization_id)
        
        # Generate tokens
        tokens = await auth_service.login(UserLogin(
            email=user_data.email,
            password=user_data.password
        ))
        
        return {
            "success": True,
            "message": "User registered successfully",
            "data": {
                "user": user.dict(),
                **tokens
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", response_model=Dict[str, Any])
async def login_user(login_data: UserLogin):
    """
    Authenticate user and return JWT tokens
    """
    try:
        if not auth_service:
            raise HTTPException(status_code=500, detail="Auth service not initialized")
        
        tokens = await auth_service.login(login_data)
        
        return {
            "success": True,
            "message": "Login successful",
            "data": tokens
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token
    """
    try:
        if not auth_service:
            raise HTTPException(status_code=500, detail="Auth service not initialized")
        
        # Decode and validate refresh token
        payload = auth_service.decode_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Generate new access token
        token_data = {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "org_id": payload.get("org_id"),
            "role": payload.get("role")
        }
        
        access_token = auth_service.create_access_token(token_data)
        
        return {
            "success": True,
            "data": {
                "access_token": access_token,
                "token_type": "bearer"
            }
        }
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(status_code=401, detail="Token refresh failed")


# Protected endpoints (require authentication)

@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    current_user: Dict = Depends(get_current_user_from_token)
):
    """
    Get current user information
    """
    try:
        return {
            "success": True,
            "data": {
                "user": current_user
            }
        }
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user information")


@router.post("/api-keys", response_model=Dict[str, Any])
async def create_api_key(
    key_data: ApiKeyCreate,
    current_user: Dict = Depends(get_current_user_from_token)
):
    """
    Create a new API key for the organization
    """
    try:
        if not auth_service:
            raise HTTPException(status_code=500, detail="Auth service not initialized")
        
        # Check if user has permission to create API keys
        if current_user.get("role") not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Create API key
        api_key = await auth_service.create_api_key(
            organization_id=current_user.get("organization_id"),
            key_data=key_data
        )
        
        return {
            "success": True,
            "message": "API key created successfully",
            "data": api_key.dict()
        }
    except Exception as e:
        logger.error(f"API key creation failed: {e}")
        raise HTTPException(status_code=500, detail="API key creation failed")


@router.get("/api-keys", response_model=Dict[str, Any])
async def list_api_keys(
    current_user: Dict = Depends(get_current_user_from_token)
):
    """
    List all API keys for the organization
    """
    try:
        if not pg_storage:
            raise HTTPException(status_code=500, detail="Storage not initialized")
        
        # Check if user has permission to view API keys
        if current_user.get("role") not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get API keys from database
        result = await pg_storage.execute_query(
            """
            SELECT id, name, description, last_used_at, usage_count, 
                   is_active, expires_at, created_at
            FROM api_keys
            WHERE organization_id = $1
            ORDER BY created_at DESC
            """,
            [current_user.get("organization_id")]
        )
        
        api_keys = []
        if result:
            for row in result:
                api_keys.append({
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "last_used_at": row["last_used_at"],
                    "usage_count": row["usage_count"],
                    "is_active": row["is_active"],
                    "expires_at": row["expires_at"],
                    "created_at": row["created_at"]
                })
        
        return {
            "success": True,
            "data": {
                "api_keys": api_keys,
                "count": len(api_keys)
            }
        }
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(status_code=500, detail="Failed to list API keys")


@router.delete("/api-keys/{key_id}", response_model=Dict[str, Any])
async def revoke_api_key(
    key_id: str,
    current_user: Dict = Depends(get_current_user_from_token)
):
    """
    Revoke an API key
    """
    try:
        if not auth_service:
            raise HTTPException(status_code=500, detail="Auth service not initialized")
        
        # Check if user has permission to revoke API keys
        if current_user.get("role") not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Revoke API key
        success = await auth_service.revoke_api_key(
            key_id=key_id,
            organization_id=current_user.get("organization_id")
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")
        
        return {
            "success": True,
            "message": "API key revoked successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key revocation failed: {e}")
        raise HTTPException(status_code=500, detail="API key revocation failed")


@router.post("/logout", response_model=Dict[str, Any])
async def logout_user(
    current_user: Dict = Depends(get_current_user_from_token)
):
    """
    Logout user (client should discard tokens)
    """
    try:
        # In a more complex implementation, we might:
        # - Blacklist the token
        # - Clear refresh tokens
        # - Update last_logout_at timestamp
        
        return {
            "success": True,
            "message": "Logged out successfully"
        }
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")


@router.put("/password", response_model=Dict[str, Any])
async def change_password(
    old_password: str,
    new_password: str,
    current_user: Dict = Depends(get_current_user_from_token)
):
    """
    Change user password
    """
    try:
        if not auth_service or not pg_storage:
            raise HTTPException(status_code=500, detail="Services not initialized")
        
        # Get user from database
        result = await pg_storage.execute_query(
            "SELECT * FROM users WHERE id = $1",
            [current_user.get("sub")]
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = result[0]
        
        # Verify old password
        if not auth_service.verify_password(old_password, user_data["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid old password")
        
        # Hash new password
        new_password_hash = auth_service.hash_password(new_password)
        
        # Update password
        await pg_storage.execute_query(
            """
            UPDATE users 
            SET password_hash = $1, updated_at = CURRENT_TIMESTAMP
            WHERE id = $2
            """,
            [new_password_hash, current_user.get("sub")]
        )
        
        return {
            "success": True,
            "message": "Password changed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(status_code=500, detail="Password change failed")