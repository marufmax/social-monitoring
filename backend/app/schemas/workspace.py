"""
Workspace-related schemas
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
from app.models.workspace import WorkspaceRole


class CreateWorkspaceRequest(BaseModel):
    """Create workspace request"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UpdateWorkspaceRequest(BaseModel):
    """Update workspace request"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[Dict[str, Any]] = None


class InviteMemberRequest(BaseModel):
    """Invite member request"""

    email: str = Field(..., description="Email of user to invite")
    role: WorkspaceRole = Field(WorkspaceRole.MEMBER, description="Role to assign")
    permissions: Optional[Dict[str, Any]] = Field(
        None, description="Custom permissions"
    )


class UpdateMemberRequest(BaseModel):
    """Update member request"""

    role: Optional[WorkspaceRole] = None
    permissions: Optional[Dict[str, Any]] = None


class WorkspaceMemberResponse(BaseModel):
    """Workspace member response"""

    user_id: str
    role: str
    permissions: Dict[str, Any]
    joined_at: datetime
    user: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class WorkspaceResponse(BaseModel):
    """Workspace response"""

    id: str
    name: str
    slug: str
    description: Optional[str]
    settings: Dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = None
    user_role: Optional[str] = None

    class Config:
        from_attributes = True
