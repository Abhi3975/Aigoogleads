"""Shared enumerations used across ORM models and schemas."""

from __future__ import annotations

import enum


class OrgRole(str, enum.Enum):
    """Role of a user within an organization (RBAC).

    Ordered from most to least privileged; used for permission checks.
    """

    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"


class OrgPlan(str, enum.Enum):
    """Billing plan for an organization (billing-ready architecture)."""

    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class AuditAction(str, enum.Enum):
    """High-level categories of auditable actions."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    EXECUTE = "execute"
