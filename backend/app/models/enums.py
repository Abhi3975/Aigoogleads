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


# Privilege ranking (higher number = more privileged). Used by RBAC checks:
# a member satisfies a required role when their rank >= the required rank.
ROLE_RANK: dict[OrgRole, int] = {
    OrgRole.VIEWER: 10,
    OrgRole.ANALYST: 20,
    OrgRole.MANAGER: 30,
    OrgRole.ADMIN: 40,
    OrgRole.OWNER: 50,
}


def role_rank(role: OrgRole) -> int:
    """Return the numeric privilege rank of a role."""
    return ROLE_RANK[role]


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
