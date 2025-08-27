"""
User and Organization Models
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, EmailStr, Field
import uuid


class UserRole(str, Enum):
    """User roles within organization"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class PlanType(str, Enum):
    """Subscription plan types"""
    FREE = "free"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Subscription status"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class Organization(BaseModel):
    """Organization model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str  # URL-friendly identifier
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Settings
    settings: dict = Field(default_factory=dict)
    
    class Config:
        orm_mode = True


class User(BaseModel):
    """User model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: Optional[str] = None
    password_hash: Optional[str] = None  # For local auth
    
    # Organization
    organization_id: Optional[str] = None
    role: UserRole = UserRole.MEMBER
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    
    # Status
    is_active: bool = True
    is_verified: bool = False
    
    class Config:
        orm_mode = True


class ApiKey(BaseModel):
    """API Key model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    key_hash: str  # Store hashed version only
    name: Optional[str] = None
    description: Optional[str] = None
    
    # Permissions
    scopes: List[str] = Field(default_factory=list)
    
    # Usage tracking
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    
    # Status
    is_active: bool = True
    expires_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True


class Subscription(BaseModel):
    """Subscription model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str
    
    # Plan details
    plan_type: PlanType = PlanType.FREE
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    
    # Stripe integration
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    
    # Billing cycle
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    
    # Trial
    trial_end: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


# Request/Response models for API

class UserCreate(BaseModel):
    """User creation request"""
    email: EmailStr
    password: str
    name: Optional[str] = None
    organization_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model (no sensitive data)"""
    id: str
    email: EmailStr
    name: Optional[str]
    organization_id: Optional[str]
    role: UserRole
    created_at: datetime
    is_verified: bool


class OrganizationCreate(BaseModel):
    """Organization creation request"""
    name: str
    slug: Optional[str] = None  # Auto-generate if not provided


class ApiKeyCreate(BaseModel):
    """API Key creation request"""
    name: Optional[str] = None
    description: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    """API Key response (with actual key only on creation)"""
    id: str
    name: Optional[str]
    description: Optional[str]
    key: Optional[str] = None  # Only provided on creation
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]