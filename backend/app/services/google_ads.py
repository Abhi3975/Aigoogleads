"""Google Ads service — orchestrates OAuth, token storage, and API access.

Sensitive refresh tokens are encrypted at rest. Synchronous SDK calls are run
off the event loop via ``run_in_threadpool``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestMeta
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.security import decrypt_secret, encrypt_secret
from app.integrations.google_ads import client as ads_client
from app.integrations.google_ads.mappers import map_campaign, map_customer, map_metrics
from app.integrations.google_ads.queries import CAMPAIGNS_QUERY, campaign_metrics_query
from app.models.google_ads import GoogleAdsAccount, GoogleAdsConnection
from app.repositories.google_ads import (
    GoogleAdsAccountRepository,
    GoogleAdsConnectionRepository,
)
from app.schemas.google_ads import (
    CampaignMetricsOut,
    CampaignOut,
    CreateCampaignRequest,
    CreateCampaignResult,
)
from app.services.audit import AuditService

logger = get_logger(__name__)


class GoogleAdsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.connections = GoogleAdsConnectionRepository(session)
        self.accounts = GoogleAdsAccountRepository(session)
        self.audit = AuditService(session)

    # -- Connection / tokens ----------------------------------------------
    async def store_connection(
        self,
        *,
        organization_id: uuid.UUID,
        authorized_by_user_id: uuid.UUID | None,
        refresh_token: str,
        scopes: str,
        login_customer_id: str | None,
        meta: RequestMeta | None = None,
    ) -> GoogleAdsConnection:
        """Persist (or replace) an org's Google Ads connection with an
        encrypted refresh token."""
        existing = await self.connections.get_active_for_org(organization_id)
        encrypted = encrypt_secret(refresh_token)
        if existing is not None:
            connection = await self.connections.update(
                existing,
                refresh_token_encrypted=encrypted,
                scopes=scopes,
                login_customer_id=login_customer_id,
                status="active",
            )
        else:
            connection = await self.connections.create(
                organization_id=organization_id,
                authorized_by_user_id=authorized_by_user_id,
                refresh_token_encrypted=encrypted,
                scopes=scopes,
                login_customer_id=login_customer_id,
                status="active",
            )
        await self.audit.record(
            "google_ads.connect",
            actor_user_id=authorized_by_user_id,
            organization_id=organization_id,
            resource_type="google_ads_connection",
            resource_id=str(connection.id),
            meta=meta,
        )
        await self.session.commit()
        await self.session.refresh(connection)
        return connection

    async def require_connection(self, organization_id: uuid.UUID) -> GoogleAdsConnection:
        connection = await self.connections.get_active_for_org(organization_id)
        if connection is None:
            raise NotFoundError(
                "No active Google Ads connection for this organization.",
                error_code="google_ads_not_connected",
            )
        return connection

    def _wrapper_for(self, connection: GoogleAdsConnection) -> Any:
        refresh_token = decrypt_secret(connection.refresh_token_encrypted)
        return ads_client.create_wrapper(
            refresh_token=refresh_token,
            login_customer_id=connection.login_customer_id,
        )

    async def disconnect(self, organization_id: uuid.UUID) -> None:
        connection = await self.connections.get_active_for_org(organization_id)
        if connection is None:
            return
        await self.connections.update(connection, status="revoked")
        await self.session.commit()

    # -- Accounts ----------------------------------------------------------
    async def sync_accounts(self, organization_id: uuid.UUID) -> list[GoogleAdsAccount]:
        connection = await self.require_connection(organization_id)
        wrapper = self._wrapper_for(connection)

        customer_ids = await run_in_threadpool(wrapper.list_accessible_customers)
        synced: list[GoogleAdsAccount] = []
        for customer_id in customer_ids:
            row = await run_in_threadpool(wrapper.get_customer, customer_id)
            info = map_customer(row) if row is not None else {"customer_id": customer_id}
            account = await self.accounts.upsert(
                organization_id=organization_id,
                connection_id=connection.id,
                customer_id=info.get("customer_id", customer_id),
                descriptive_name=info.get("descriptive_name"),
                currency_code=info.get("currency_code"),
                time_zone=info.get("time_zone"),
                is_manager=bool(info.get("is_manager", False)),
                is_test_account=bool(info.get("is_test_account", False)),
            )
            synced.append(account)

        connection.last_synced_at = datetime.now(UTC)
        await self.session.commit()
        return await self.accounts.list_for_org(organization_id)

    async def list_accounts(self, organization_id: uuid.UUID) -> list[GoogleAdsAccount]:
        return await self.accounts.list_for_org(organization_id)

    async def _require_account(
        self, organization_id: uuid.UUID, customer_id: str
    ) -> GoogleAdsAccount:
        account = await self.accounts.get_by_customer_id(organization_id, customer_id)
        if account is None:
            raise NotFoundError(
                "Account not linked to this organization; sync accounts first.",
                error_code="account_not_linked",
            )
        return account

    # -- Campaigns & metrics ----------------------------------------------
    async def list_campaigns(
        self, organization_id: uuid.UUID, customer_id: str
    ) -> list[CampaignOut]:
        connection = await self.require_connection(organization_id)
        await self._require_account(organization_id, customer_id)
        wrapper = self._wrapper_for(connection)
        rows = await run_in_threadpool(wrapper.search, customer_id, CAMPAIGNS_QUERY)
        return [map_campaign(row) for row in rows]

    async def get_campaign_metrics(
        self, organization_id: uuid.UUID, customer_id: str, date_range: str
    ) -> list[CampaignMetricsOut]:
        connection = await self.require_connection(organization_id)
        await self._require_account(organization_id, customer_id)
        query = campaign_metrics_query(date_range)
        wrapper = self._wrapper_for(connection)
        rows = await run_in_threadpool(wrapper.search, customer_id, query)
        return [map_metrics(row) for row in rows]

    async def create_campaign(
        self,
        *,
        organization_id: uuid.UUID,
        customer_id: str,
        data: CreateCampaignRequest,
        actor_user_id: uuid.UUID | None = None,
        meta: RequestMeta | None = None,
    ) -> CreateCampaignResult:
        connection = await self.require_connection(organization_id)
        account = await self._require_account(organization_id, customer_id)
        if account.is_manager:
            raise ValidationError("Cannot create campaigns directly under a manager account.")

        wrapper = self._wrapper_for(connection)
        result = await run_in_threadpool(
            wrapper.create_campaign,
            customer_id=customer_id,
            name=data.name,
            daily_budget=data.daily_budget,
            paused=data.start_paused,
        )
        await self.audit.record(
            "google_ads.create_campaign",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type="campaign",
            resource_id=result["campaign_id"],
            context={"customer_id": customer_id, "name": data.name},
            meta=meta,
        )
        await self.session.commit()
        return CreateCampaignResult(**result)

    # -- Mutations used by the Execution agent -----------------------------
    async def set_campaign_status(
        self,
        *,
        organization_id: uuid.UUID,
        customer_id: str,
        campaign_id: str,
        status: str,
        actor_user_id: uuid.UUID | None = None,
        meta: RequestMeta | None = None,
    ) -> dict[str, str]:
        connection = await self.require_connection(organization_id)
        await self._require_account(organization_id, customer_id)
        wrapper = self._wrapper_for(connection)
        result = await run_in_threadpool(
            wrapper.set_campaign_status,
            customer_id=customer_id,
            campaign_id=campaign_id,
            status=status,
        )
        await self.audit.record(
            "google_ads.set_campaign_status",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type="campaign",
            resource_id=str(campaign_id),
            context={"status": status.upper(), "customer_id": customer_id},
            meta=meta,
        )
        await self.session.commit()
        return result

    async def update_campaign_budget(
        self,
        *,
        organization_id: uuid.UUID,
        customer_id: str,
        campaign_id: str,
        daily_budget: float,
        actor_user_id: uuid.UUID | None = None,
        meta: RequestMeta | None = None,
    ) -> dict[str, str]:
        connection = await self.require_connection(organization_id)
        await self._require_account(organization_id, customer_id)
        wrapper = self._wrapper_for(connection)
        result = await run_in_threadpool(
            wrapper.update_campaign_budget,
            customer_id=customer_id,
            campaign_id=campaign_id,
            daily_budget=daily_budget,
        )
        await self.audit.record(
            "google_ads.update_budget",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type="campaign",
            resource_id=str(campaign_id),
            context={"daily_budget": daily_budget, "customer_id": customer_id},
            meta=meta,
        )
        await self.session.commit()
        return result

    # -- Helpers -----------------------------------------------------------
    @staticmethod
    def duplicate_guard(existing: GoogleAdsConnection | None) -> None:
        if existing is not None and existing.status == "active":
            raise ConflictError("Google Ads is already connected for this organization.")
