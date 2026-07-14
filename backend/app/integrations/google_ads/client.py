"""Thin synchronous wrapper over the google-ads SDK.

The SDK is imported lazily inside methods so the application (and its test
suite) can import this module without the heavy dependency installed. All
methods are synchronous and are executed off the event loop by the service
layer (``run_in_threadpool``).
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.integrations.google_ads.queries import CUSTOMER_QUERY


def _digits(customer_id: str) -> str:
    return customer_id.replace("-", "").strip()


def _step(action: str, resource_type: str, resource_id: str) -> dict[str, str]:
    return {
        "action": action,
        "resource_type": resource_type,
        "google_resource_id": resource_id,
        "status": "success",
    }


class GoogleAdsClientWrapper:
    """Wraps a configured google-ads client for a single connection."""

    def __init__(self, *, refresh_token: str, login_customer_id: str | None = None) -> None:
        self._refresh_token = refresh_token
        self._login_customer_id = login_customer_id or settings.GOOGLE_ADS_LOGIN_CUSTOMER_ID or None

    def _build_client(self) -> Any:
        from google.ads.googleads.client import GoogleAdsClient  # lazy import

        config: dict[str, Any] = {
            "developer_token": settings.GOOGLE_ADS_DEVELOPER_TOKEN,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": self._refresh_token,
            "use_proto_plus": True,
        }
        if self._login_customer_id:
            config["login_customer_id"] = _digits(self._login_customer_id)
        return GoogleAdsClient.load_from_dict(config)

    # -- Reads -------------------------------------------------------------
    def list_accessible_customers(self) -> list[str]:
        client = self._build_client()
        with self._translate_errors():
            service = client.get_service("CustomerService")
            response = service.list_accessible_customers()
        return [rn.split("/")[-1] for rn in response.resource_names]

    def get_customer(self, customer_id: str) -> Any | None:
        rows = self.search(customer_id, CUSTOMER_QUERY)
        return rows[0] if rows else None

    def search(self, customer_id: str, query: str) -> list[Any]:
        client = self._build_client()
        with self._translate_errors():
            service = client.get_service("GoogleAdsService")
            stream = service.search(customer_id=_digits(customer_id), query=query)
            return list(stream)

    # -- Writes ------------------------------------------------------------
    def create_campaign(
        self, *, customer_id: str, name: str, daily_budget: float, paused: bool = True
    ) -> dict[str, str]:
        client = self._build_client()
        cid = _digits(customer_id)
        with self._translate_errors():
            # 1) Shared budget
            budget_service = client.get_service("CampaignBudgetService")
            budget_op = client.get_type("CampaignBudgetOperation")
            budget = budget_op.create
            budget.name = f"{name} Budget {uuid.uuid4().hex[:8]}"
            budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
            budget.amount_micros = round(daily_budget * 1_000_000)
            budget.explicitly_shared = False
            budget_resp = budget_service.mutate_campaign_budgets(
                customer_id=cid, operations=[budget_op]
            )
            budget_rn = budget_resp.results[0].resource_name

            # 2) Campaign referencing the budget (Search, Manual CPC, PAUSED)
            campaign_service = client.get_service("CampaignService")
            campaign_op = client.get_type("CampaignOperation")
            campaign = campaign_op.create
            campaign.name = name
            campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
            campaign.status = (
                client.enums.CampaignStatusEnum.PAUSED
                if paused
                else client.enums.CampaignStatusEnum.ENABLED
            )
            campaign.manual_cpc = client.get_type("ManualCpc")
            campaign.campaign_budget = budget_rn
            campaign.network_settings.target_google_search = True
            campaign.network_settings.target_search_network = True
            campaign.network_settings.target_content_network = False
            campaign_resp = campaign_service.mutate_campaigns(
                customer_id=cid, operations=[campaign_op]
            )
            campaign_rn = campaign_resp.results[0].resource_name

        return {
            "campaign_id": campaign_rn.split("/")[-1],
            "campaign_resource_name": campaign_rn,
            "budget_resource_name": budget_rn,
            "status": "PAUSED" if paused else "ENABLED",
        }

    def set_campaign_status(
        self, *, customer_id: str, campaign_id: str, status: str
    ) -> dict[str, str]:
        from google.api_core import protobuf_helpers

        client = self._build_client()
        cid = _digits(customer_id)
        with self._translate_errors():
            service = client.get_service("CampaignService")
            op = client.get_type("CampaignOperation")
            campaign = op.update
            campaign.resource_name = service.campaign_path(cid, campaign_id)
            campaign.status = client.enums.CampaignStatusEnum[status.upper()]
            client.copy_from(op.update_mask, protobuf_helpers.field_mask(None, campaign._pb))
            service.mutate_campaigns(customer_id=cid, operations=[op])
        return {"campaign_id": str(campaign_id), "status": status.upper()}

    def update_campaign_budget(
        self, *, customer_id: str, campaign_id: str, daily_budget: float
    ) -> dict[str, str]:
        from google.api_core import protobuf_helpers

        client = self._build_client()
        cid = _digits(customer_id)
        with self._translate_errors():
            # Resolve the campaign's budget resource, then update its amount.
            rows = self.search(
                cid,
                "SELECT campaign_budget.resource_name FROM campaign "
                f"WHERE campaign.id = {int(campaign_id)}",
            )
            if not rows:
                from app.core.exceptions import NotFoundError

                raise NotFoundError(f"Campaign {campaign_id} not found.")
            budget_rn = rows[0].campaign_budget.resource_name

            service = client.get_service("CampaignBudgetService")
            op = client.get_type("CampaignBudgetOperation")
            budget = op.update
            budget.resource_name = budget_rn
            budget.amount_micros = round(daily_budget * 1_000_000)
            client.copy_from(op.update_mask, protobuf_helpers.field_mask(None, budget._pb))
            service.mutate_campaign_budgets(customer_id=cid, operations=[op])
        return {"campaign_id": str(campaign_id), "daily_budget": str(daily_budget)}

    def build_full_campaign(
        self, *, customer_id: str, structure: dict[str, Any], paused: bool = True
    ) -> dict[str, Any]:
        """Create a complete Search campaign from a blueprint structure.

        Creates budget -> campaign -> ad groups -> keywords -> negatives ->
        responsive search ads. On any failure the partially-created campaign
        and budget are removed (best-effort rollback) before re-raising.
        """
        client = self._build_client()
        cid = _digits(customer_id)
        steps: list[dict[str, Any]] = []
        campaign_rn: str | None = None
        budget_rn: str | None = None

        try:
            with self._translate_errors():
                budget_rn = self._create_budget(
                    client, cid, structure["campaign_name"], structure["daily_budget"]
                )
                steps.append(_step("create_budget", "campaign_budget", budget_rn))

                campaign_rn = self._create_campaign(client, cid, structure, budget_rn, paused)
                campaign_id = campaign_rn.split("/")[-1]
                steps.append(_step("create_campaign", "campaign", campaign_rn))

                self._add_campaign_negatives(
                    client, cid, campaign_rn, structure.get("shared_negative_keywords", []), steps
                )

                for ad_group in structure.get("ad_groups", []):
                    self._build_ad_group(client, cid, campaign_rn, ad_group, steps)

            return {
                "campaign_id": campaign_id,
                "campaign_resource_name": campaign_rn,
                "budget_resource_name": budget_rn,
                "steps": steps,
            }
        except Exception:
            self._rollback(client, cid, campaign_rn, budget_rn)
            raise

    def _create_budget(self, client: Any, cid: str, name: str, daily_budget: float) -> str:
        service = client.get_service("CampaignBudgetService")
        op = client.get_type("CampaignBudgetOperation")
        budget = op.create
        budget.name = f"{name} Budget {uuid.uuid4().hex[:8]}"
        budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        budget.amount_micros = round(float(daily_budget) * 1_000_000)
        budget.explicitly_shared = False
        resp = service.mutate_campaign_budgets(customer_id=cid, operations=[op])
        return resp.results[0].resource_name

    def _create_campaign(
        self, client: Any, cid: str, structure: dict[str, Any], budget_rn: str, paused: bool
    ) -> str:
        service = client.get_service("CampaignService")
        op = client.get_type("CampaignOperation")
        campaign = op.create
        campaign.name = structure["campaign_name"]
        campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
        campaign.status = (
            client.enums.CampaignStatusEnum.PAUSED
            if paused
            else client.enums.CampaignStatusEnum.ENABLED
        )
        campaign.manual_cpc = client.get_type("ManualCpc")
        campaign.campaign_budget = budget_rn
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = True
        campaign.network_settings.target_content_network = False
        resp = service.mutate_campaigns(customer_id=cid, operations=[op])
        return resp.results[0].resource_name

    def _add_campaign_negatives(
        self, client: Any, cid: str, campaign_rn: str, negatives: list[str], steps: list[dict]
    ) -> None:
        if not negatives:
            return
        service = client.get_service("CampaignCriterionService")
        ops = []
        for text in negatives:
            op = client.get_type("CampaignCriterionOperation")
            crit = op.create
            crit.campaign = campaign_rn
            crit.negative = True
            crit.keyword.text = text
            crit.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
            ops.append(op)
        resp = service.mutate_campaign_criteria(customer_id=cid, operations=ops)
        for result in resp.results:
            steps.append(_step("add_campaign_negative", "campaign_criterion", result.resource_name))

    def _build_ad_group(
        self, client: Any, cid: str, campaign_rn: str, ad_group: dict[str, Any], steps: list[dict]
    ) -> None:
        ag_service = client.get_service("AdGroupService")
        ag_op = client.get_type("AdGroupOperation")
        ag = ag_op.create
        ag.name = ad_group["name"]
        ag.campaign = campaign_rn
        ag.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
        ag.cpc_bid_micros = 1_000_000
        ag_resp = ag_service.mutate_ad_groups(customer_id=cid, operations=[ag_op])
        ag_rn = ag_resp.results[0].resource_name
        steps.append(_step("create_ad_group", "ad_group", ag_rn))

        self._add_keywords(client, cid, ag_rn, ad_group.get("keywords", []), steps)
        self._add_ad_group_negatives(
            client, cid, ag_rn, ad_group.get("negative_keywords", []), steps
        )
        if ad_group.get("ad"):
            self._create_rsa(client, cid, ag_rn, ad_group["ad"], steps)

    def _add_keywords(
        self, client: Any, cid: str, ag_rn: str, keywords: list[dict], steps: list[dict]
    ) -> None:
        if not keywords:
            return
        service = client.get_service("AdGroupCriterionService")
        ops = []
        for kw in keywords:
            op = client.get_type("AdGroupCriterionOperation")
            crit = op.create
            crit.ad_group = ag_rn
            crit.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
            crit.keyword.text = kw["text"]
            crit.keyword.match_type = client.enums.KeywordMatchTypeEnum[
                str(kw.get("match_type", "PHRASE")).upper()
            ]
            ops.append(op)
        resp = service.mutate_ad_group_criteria(customer_id=cid, operations=ops)
        steps.append(_step("add_keywords", "ad_group_criterion", f"{len(resp.results)} keywords"))

    def _add_ad_group_negatives(
        self, client: Any, cid: str, ag_rn: str, negatives: list[str], steps: list[dict]
    ) -> None:
        if not negatives:
            return
        service = client.get_service("AdGroupCriterionService")
        ops = []
        for text in negatives:
            op = client.get_type("AdGroupCriterionOperation")
            crit = op.create
            crit.ad_group = ag_rn
            crit.negative = True
            crit.keyword.text = text
            crit.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
            ops.append(op)
        resp = service.mutate_ad_group_criteria(customer_id=cid, operations=ops)
        steps.append(
            _step("add_negative_keywords", "ad_group_criterion", f"{len(resp.results)} negatives")
        )

    def _create_rsa(
        self, client: Any, cid: str, ag_rn: str, ad: dict[str, Any], steps: list[dict]
    ) -> None:
        service = client.get_service("AdGroupAdService")
        op = client.get_type("AdGroupAdOperation")
        ad_group_ad = op.create
        ad_group_ad.ad_group = ag_rn
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.ENABLED
        ad_group_ad.ad.final_urls.append(ad["final_url"])
        for text in ad.get("headlines", []):
            asset = client.get_type("AdTextAsset")
            asset.text = text
            ad_group_ad.ad.responsive_search_ad.headlines.append(asset)
        for text in ad.get("descriptions", []):
            asset = client.get_type("AdTextAsset")
            asset.text = text
            ad_group_ad.ad.responsive_search_ad.descriptions.append(asset)
        if ad.get("path1"):
            ad_group_ad.ad.responsive_search_ad.path1 = ad["path1"]
        if ad.get("path2"):
            ad_group_ad.ad.responsive_search_ad.path2 = ad["path2"]
        resp = service.mutate_ad_group_ads(customer_id=cid, operations=[op])
        steps.append(_step("create_ad", "ad_group_ad", resp.results[0].resource_name))

    def _rollback(
        self, client: Any, cid: str, campaign_rn: str | None, budget_rn: str | None
    ) -> None:
        try:
            if campaign_rn:
                service = client.get_service("CampaignService")
                op = client.get_type("CampaignOperation")
                op.remove = campaign_rn
                service.mutate_campaigns(customer_id=cid, operations=[op])
            if budget_rn:
                service = client.get_service("CampaignBudgetService")
                op = client.get_type("CampaignBudgetOperation")
                op.remove = budget_rn
                service.mutate_campaign_budgets(customer_id=cid, operations=[op])
        except Exception:  # pragma: no cover - best-effort cleanup
            from app.core.logging import get_logger

            get_logger(__name__).warning("campaign_rollback_failed", campaign=campaign_rn)

    # -- Error translation -------------------------------------------------
    def _translate_errors(self) -> Any:
        wrapper = self

        class _Ctx:
            def __enter__(self) -> None:
                return None

            def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
                if exc is None:
                    return False
                try:
                    from google.ads.googleads.errors import GoogleAdsException
                except ImportError:  # pragma: no cover
                    return False
                if isinstance(exc, GoogleAdsException):
                    raise ExternalServiceError(
                        "Google Ads API request failed.",
                        details={"errors": wrapper._format_google_ads_errors(exc)},
                    ) from exc
                return False

        return _Ctx()

    @staticmethod
    def _format_google_ads_errors(exc: Any) -> list[str]:
        messages: list[str] = []
        failure = getattr(exc, "failure", None)
        if failure is not None:
            for error in getattr(failure, "errors", []):
                messages.append(getattr(error, "message", str(error)))
        return messages or [str(exc)]


def create_wrapper(
    *, refresh_token: str, login_customer_id: str | None = None
) -> GoogleAdsClientWrapper:
    """Factory used by the service layer (monkeypatched in tests)."""
    return GoogleAdsClientWrapper(refresh_token=refresh_token, login_customer_id=login_customer_id)


__all__ = ["GoogleAdsClientWrapper", "create_wrapper"]
