"""
Request/Response schemas for authentication endpoints.
"""
from datetime import datetime
from typing import Optional, Dict, List, Any

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from app.schemas.workspace import WorkspaceResponse


class SignUpRequest(BaseModel):
    """Sign up Request Schema"""
    email: EmailStr = Field(..., title="Email address")
    password: str = Field(..., min_length=8, max_length=128, title="Password")
    name: Optional[str] = Field(None, max_length=50, title="Full name")
    timezone: Optional[str] = Field("UTC", description="User timezone")
    language: Optional[str] = Field("en", description="Preferred language")

    @field_validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",
                "name": "John Sina",
            }
        }
    )

class SignInRequest(BaseModel):
    """Sign in request schema"""
    email: EmailStr
    password: str = Field(..., min_length=4)

class SocialAuthRequest(BaseModel):
    """Social authentication request schema"""
    name: str = Field(..., min_length=2, max_length=100)
    timezone: Optional[str] = "UTC"
    language: Optional[str] = "en"

class UserProfileResponse(BaseModel):
    """User response schema"""
    user_id: str
    name: str
    timezone: str
    language: str
    preferences: Dict[str, Any]
    consent_marketing: bool
    created_at: datetime

    workspaces: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True

class UserProfileRequest(BaseModel):
    """User profile update request schema"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    timezone: Optional[str] = Field(None, min_length=1, max_length=50)
    language: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class UserResponse(BaseModel):
    """User response schema"""

    user_id: str
    name: str
    display_name: Optional[str]
    full_display_name: str
    timezone: str
    language: str
    preferences: Dict[str, Any]
    consent_marketing: bool
    created_at: datetime
    workspaces: List[WorkspaceResponse] = []

    class Config:
        from_attributes = True

    @classmethod
    def from_user_with_workspaces(cls, user, workspace_memberships=None):
        """Create UserResponse from user with workspace memberships"""
        workspaces = []
        if workspace_memberships:
            for membership in workspace_memberships:
                ws = membership.workspace
                if ws:
                    workspaces.append(
                        WorkspaceResponse(
                            id=str(ws.id),
                            name=ws.name,
                            slug=ws.slug,
                            description=getattr(ws, "description", None),
                            settings=ws.settings,
                            created_by=ws.owner_id,
                            created_at=ws.created_at,
                            updated_at=ws.updated_at,
                            member_count=len(ws.members) if ws.members else 0,
                            user_role=membership.role.value
                            if hasattr(membership.role, "value")
                            else membership.role,
                        )
                    )

        return cls(
            user_id=user.user_id,
            name=user.name,
            display_name=user.display_name,
            full_display_name=user.full_display_name,
            timezone=user.timezone,
            language=user.language,
            preferences=user.preferences,
            consent_marketing=user.consent_marketing,
            created_at=user.created_at,
            workspaces=workspaces,
        )

class UpdateProfileRequest(BaseModel):
    """Update user profile request"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    timezone: Optional[str] = None
    language: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None