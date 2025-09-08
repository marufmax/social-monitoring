"""
This package contains all SQLAlchemy ORM models.

By importing them here, we make them discoverable by SQLAlchemy's declarative base
and by migration tools like Alembic. We also expose them for easy importing
elsewhere in the application.
"""
from .base import (
    Base,
    BaseModel,
    TimestampMixin,
    UUIDMixin,
    SoftDeleteMixin,
    AuditMixin,
    StatusEnum,
    PriorityEnum,
    SeverityEnum,
)
from .user import SuperTokensUser, AppUser
from .workspace import Workspace, WorkspaceMember, SubscriptionPlan, UsageTracking
from .platform import Platform
from .monitor import Monitor
from .social import SocialUser, InfluencerCategory
from .mention import Mention, MonitorMention, MentionFingerprint
from .mention_category import MentionCategory, MentionCategoryAssignment
from .collaboration import MentionAssignment, MentionResponse
from .alert import AlertRule, Alert, AlertDelivery
from .notification import NotificationQueue, NotificationTemplate, NotificationPreference
from .analytics import MonitorAnalyticsHourly
from .integration import IntegrationProvider
from .export import DataExport
from .system import SystemConfiguration, AuditLog, SystemHealth


__all__ = [
    # Base classes and Mixins from .base
    "Base",
    "BaseModel",
    "TimestampMixin",
    "UUIDMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    "StatusEnum",
    "PriorityEnum",
    "SeverityEnum",

    # Models from .user
    "SuperTokensUser",
    "AppUser",

    # Models from .workspace
    "Workspace",
    "WorkspaceMember",
    "WorkspaceInvitation",

    # Models from .platform
    "Platform",

    # Models from .monitor
    "Monitor",
    "MonitorKeyword",
    "MonitorPlatform",

    # Models from .social
    "SocialPost",
    "SocialProfile",

    # Models from .mention
    "Mention",

    # Models from .mention_category
    "MentionCategory",

    # Models from .collaboration
    "MentionAssignment",
    "MentionResponse",

    # Models from .alert
    "AlertRule",
    "Alert",

    # Models from .notification
    "Notification",

    # Models from .analytics
    "AnalyticsReport",

    # Models from .integration
    "Integration",

    # Models from .export
    "ExportJob",

    # Models from .system
    "SystemSetting",
]
