"""
Authentication Service
Handles user authentication, JWT tokens, and API keys
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from pydantic import EmailStr
import logging

from src.models.user import (
    User, Organization, ApiKey, 
    UserCreate, UserLogin, UserResponse,
    ApiKeyCreate, ApiKeyResponse
)

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 30


class AuthService:
    """Authentication service"""
    
    def __init__(self, storage=None):
        self.storage = storage  # Database connection
        
    # Password utilities
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    # JWT utilities
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    # User management
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user and organization"""
        
        # Check if user already exists
        if self.storage:
            existing = await self.storage.execute_query(
                "SELECT id FROM users WHERE email = $1",
                [user_data.email]
            )
            if existing:
                raise ValueError("User with this email already exists")
        
        # Create organization if name provided
        org_id = None
        if user_data.organization_name:
            org_id = str(secrets.token_hex(16))
            slug = user_data.organization_name.lower().replace(" ", "-")
            
            if self.storage:
                await self.storage.execute_query(
                    """
                    INSERT INTO organizations (id, name, slug, created_at)
                    VALUES ($1, $2, $3, $4)
                    """,
                    [org_id, user_data.organization_name, slug, datetime.utcnow()]
                )
                
                # Create default quota for organization
                await self.storage.execute_query(
                    """
                    INSERT INTO quotas (organization_id, created_at)
                    VALUES ($1, $2)
                    """,
                    [org_id, datetime.utcnow()]
                )
        
        # Create user
        user = User(
            email=user_data.email,
            name=user_data.name,
            password_hash=self.hash_password(user_data.password),
            organization_id=org_id,
            role="owner" if org_id else "member"
        )
        
        if self.storage:
            await self.storage.execute_query(
                """
                INSERT INTO users (id, email, name, password_hash, organization_id, role, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                [user.id, user.email, user.name, user.password_hash, 
                 user.organization_id, user.role, user.created_at]
            )
        
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            organization_id=user.organization_id,
            role=user.role,
            created_at=user.created_at,
            is_verified=user.is_verified
        )
    
    async def authenticate_user(self, email: EmailStr, password: str) -> Optional[User]:
        """Authenticate a user by email and password"""
        
        if not self.storage:
            # Demo user for testing
            if email == "demo@conceptdb.com" and password == "demo123":
                return User(
                    id="demo-user",
                    email=email,
                    name="Demo User",
                    organization_id="demo-org",
                    role="owner"
                )
            return None
        
        # Get user from database
        result = await self.storage.execute_query(
            "SELECT * FROM users WHERE email = $1",
            [email]
        )
        
        if not result:
            return None
            
        user_data = result[0]
        
        # Verify password
        if not self.verify_password(password, user_data.get("password_hash", "")):
            return None
        
        # Update last login
        await self.storage.execute_query(
            "UPDATE users SET last_login_at = $1 WHERE id = $2",
            [datetime.utcnow(), user_data["id"]]
        )
        
        return User(**user_data)
    
    async def login(self, login_data: UserLogin) -> Dict[str, str]:
        """Login user and return tokens"""
        
        user = await self.authenticate_user(login_data.email, login_data.password)
        
        if not user:
            raise ValueError("Invalid email or password")
        
        # Create tokens
        token_data = {
            "sub": user.id,
            "email": user.email,
            "org_id": user.organization_id,
            "role": user.role
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from JWT token"""
        
        payload = self.decode_token(token)
        
        if not payload:
            return None
        
        if payload.get("type") != "access":
            return None
        
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        if not self.storage:
            # Return demo user for testing
            return User(
                id=user_id,
                email=payload.get("email", "demo@conceptdb.com"),
                organization_id=payload.get("org_id", "demo-org"),
                role=payload.get("role", "member")
            )
        
        # Get user from database
        result = await self.storage.execute_query(
            "SELECT * FROM users WHERE id = $1",
            [user_id]
        )
        
        if not result:
            return None
            
        return User(**result[0])
    
    # API Key management
    
    def generate_api_key(self) -> str:
        """Generate a new API key"""
        # Format: ck_live_<random_string>
        return f"ck_live_{secrets.token_urlsafe(32)}"
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def create_api_key(self, organization_id: str, key_data: ApiKeyCreate) -> ApiKeyResponse:
        """Create a new API key"""
        
        # Generate key
        api_key = self.generate_api_key()
        key_hash = self.hash_api_key(api_key)
        
        # Create API key object
        key_obj = ApiKey(
            organization_id=organization_id,
            key_hash=key_hash,
            name=key_data.name,
            description=key_data.description,
            scopes=key_data.scopes,
            expires_at=key_data.expires_at
        )
        
        if self.storage:
            await self.storage.execute_query(
                """
                INSERT INTO api_keys (id, organization_id, key_hash, name, description, scopes, expires_at, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                [key_obj.id, key_obj.organization_id, key_obj.key_hash,
                 key_obj.name, key_obj.description, key_obj.scopes,
                 key_obj.expires_at, key_obj.created_at]
            )
        
        return ApiKeyResponse(
            id=key_obj.id,
            name=key_obj.name,
            description=key_obj.description,
            key=api_key,  # Only return actual key on creation
            created_at=key_obj.created_at,
            expires_at=key_obj.expires_at,
            last_used_at=None
        )
    
    async def validate_api_key(self, api_key: str) -> Optional[ApiKey]:
        """Validate an API key"""
        
        key_hash = self.hash_api_key(api_key)
        
        if not self.storage:
            # Demo API key for testing
            if api_key == "ck_live_demo_key":
                return ApiKey(
                    id="demo-key",
                    organization_id="demo-org",
                    key_hash=key_hash,
                    name="Demo API Key"
                )
            return None
        
        # Get API key from database
        result = await self.storage.execute_query(
            """
            SELECT * FROM api_keys 
            WHERE key_hash = $1 
            AND is_active = true
            AND (expires_at IS NULL OR expires_at > $2)
            """,
            [key_hash, datetime.utcnow()]
        )
        
        if not result:
            return None
        
        key_data = result[0]
        
        # Update last used time
        await self.storage.execute_query(
            """
            UPDATE api_keys 
            SET last_used_at = $1, usage_count = usage_count + 1
            WHERE id = $2
            """,
            [datetime.utcnow(), key_data["id"]]
        )
        
        return ApiKey(**key_data)
    
    async def revoke_api_key(self, key_id: str, organization_id: str) -> bool:
        """Revoke an API key"""
        
        if not self.storage:
            return True
        
        result = await self.storage.execute_query(
            """
            UPDATE api_keys 
            SET is_active = false 
            WHERE id = $1 AND organization_id = $2
            """,
            [key_id, organization_id]
        )
        
        return bool(result)