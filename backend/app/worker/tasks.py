"""Celery task wrappers around the async jobs."""

from __future__ import annotations

import uuid

from app.core.db import AsyncSessionLocal
from app.core.logging import get_logger
from app.worker import jobs
from app.worker.celery_app import celery_app
from app.worker.runtime import run_async

logger = get_logger(__name__)


async def _fetch_all() -> int:
    async with AsyncSessionLocal() as session:
        targets = await jobs.find_metrics_targets(session)
    for organization_id, customer_id in targets:
        fetch_metrics.delay(str(organization_id), customer_id)
    return len(targets)


async def _run_all_optimizations() -> int:
    async with AsyncSessionLocal() as session:
        targets = await jobs.find_optimization_targets(session)
    for organization_id, customer_id in targets:
        optimize_account.delay(str(organization_id), customer_id)
    return len(targets)


async def _generate_all_reports() -> int:
    async with AsyncSessionLocal() as session:
        targets = await jobs.find_metrics_targets(session)
    for organization_id, customer_id in targets:
        generate_report.delay(str(organization_id), customer_id)
    return len(targets)


@celery_app.task(name="app.worker.tasks.fetch_all_metrics")
def fetch_all_metrics() -> int:
    return run_async(_fetch_all())


@celery_app.task(name="app.worker.tasks.run_all_optimizations")
def run_all_optimizations() -> int:
    return run_async(_run_all_optimizations())


@celery_app.task(name="app.worker.tasks.generate_all_reports")
def generate_all_reports() -> int:
    return run_async(_generate_all_reports())


@celery_app.task(name="app.worker.tasks.fetch_metrics", bind=True, max_retries=3)
def fetch_metrics(self, organization_id: str, customer_id: str) -> int:  # type: ignore[no-untyped-def]
    async def _job() -> int:
        async with AsyncSessionLocal() as session:
            return await jobs.fetch_metrics_job(session, uuid.UUID(organization_id), customer_id)

    return run_async(_job())


@celery_app.task(name="app.worker.tasks.optimize_account", bind=True, max_retries=2)
def optimize_account(self, organization_id: str, customer_id: str) -> dict:  # type: ignore[no-untyped-def]
    async def _job() -> dict:
        async with AsyncSessionLocal() as session:
            return await jobs.optimize_account_job(session, uuid.UUID(organization_id), customer_id)

    return run_async(_job())


@celery_app.task(name="app.worker.tasks.generate_report", bind=True, max_retries=2)
def generate_report(self, organization_id: str, customer_id: str) -> str:  # type: ignore[no-untyped-def]
    async def _job() -> str:
        async with AsyncSessionLocal() as session:
            result = await jobs.generate_report_job(
                session, uuid.UUID(organization_id), customer_id
            )
            return str(result)

    return run_async(_job())
