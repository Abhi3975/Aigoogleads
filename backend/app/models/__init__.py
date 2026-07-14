"""SQLAlchemy ORM models.

Importing every model here ensures they are registered on ``Base.metadata``
so Alembic autogeneration and ``create_all`` see the full schema.
"""

from app.models.agent import AgentMemory, AgentRun, AgentStep, AIInsight
from app.models.api_key import APIKey
from app.models.audit_log import AuditLog
from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.campaign import (
    AudienceProfile,
    BudgetConfiguration,
    BusinessProfile,
    CampaignBlueprint,
    CampaignExecutionLog,
    ProductInformation,
    WebsiteAnalysis,
)
from app.models.enums import AuditAction, OrgPlan, OrgRole
from app.models.google_ads import GoogleAdsAccount, GoogleAdsConnection
from app.models.metrics import (
    AdMetric,
    CampaignMetric,
    DailyPerformanceReport,
    KeywordMetric,
)
from app.models.notification import Notification
from app.models.optimization import OptimizationLog, OptimizationPolicy
from app.models.organization import Organization, OrganizationMembership
from app.models.refresh_token import RefreshToken
from app.models.usage import UsageRecord
from app.models.user import User

__all__ = [
    "AIInsight",
    "APIKey",
    "AdMetric",
    "AgentMemory",
    "AgentRun",
    "AgentStep",
    "AudienceProfile",
    "AuditAction",
    "AuditLog",
    "Base",
    "BudgetConfiguration",
    "BusinessProfile",
    "CampaignBlueprint",
    "CampaignExecutionLog",
    "CampaignMetric",
    "DailyPerformanceReport",
    "GoogleAdsAccount",
    "GoogleAdsConnection",
    "KeywordMetric",
    "Notification",
    "OptimizationLog",
    "OptimizationPolicy",
    "OrgPlan",
    "OrgRole",
    "Organization",
    "OrganizationMembership",
    "ProductInformation",
    "RefreshToken",
    "SoftDeleteMixin",
    "TimestampMixin",
    "UUIDMixin",
    "UsageRecord",
    "User",
    "WebsiteAnalysis",
]
