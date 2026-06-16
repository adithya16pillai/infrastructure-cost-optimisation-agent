"""Orchestration between the API layer, the LangGraph agent, and storage."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.agent.graph import run_agent
from app.db import SessionLocal
from app.models.analysis_run import AnalysisRun
from app.models.enums import RunStatus, ValidationStatus
from app.models.recommendation import Recommendation

logger = logging.getLogger(__name__)


def create_run(db: Session, *, mock: bool, region: str) -> AnalysisRun:
    run = AnalysisRun(
        id=str(uuid.uuid4()),
        status=RunStatus.RUNNING.value,
        mock_mode=mock,
        region=region,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    logger.info("[%s] run created (mock=%s region=%s)", run.id, mock, region)
    return run


def _persist_findings(db: Session, run_id: str, findings: list[dict]) -> int:
    """Persist findings, returning the total estimated savings in cents."""
    total_cents = 0
    for f in findings:
        total_cents += f["estimated_monthly_savings_cents"]
        db.add(
            Recommendation(
                id=str(uuid.uuid4()),
                run_id=run_id,
                resource_type=f["resource_type"],
                resource_id=f["resource_id"],
                region=f["region"],
                finding_type=f["finding_type"],
                estimated_monthly_savings_cents=f["estimated_monthly_savings_cents"],
                evidence=f.get("evidence", {}),
                validation_status=f.get(
                    "validation_status", ValidationStatus.PENDING.value
                ),
                validation_reasoning=f.get("validation_reasoning"),
                validation_raw=f.get("validation_raw"),
                title=f.get("title", ""),
                description=f.get("description", ""),
            )
        )
    db.commit()
    return total_cents


def execute_run(run_id: str) -> None:
    """Run the agent for an existing run id. Manages its own DB session so it is
    safe to call from a FastAPI BackgroundTask."""
    db = SessionLocal()
    try:
        run = db.get(AnalysisRun, run_id)
        if run is None:
            logger.error("execute_run: run %s not found", run_id)
            return

        run.status = RunStatus.RUNNING.value
        db.commit()

        findings = run_agent(run_id=run_id, mock=run.mock_mode, region=run.region)
        total_cents = _persist_findings(db, run_id, findings)

        run.status = RunStatus.COMPLETED.value
        run.completed_at = datetime.utcnow()
        run.total_recommendations = len(findings)
        run.total_estimated_savings_cents = total_cents
        db.commit()
        logger.info("[%s] run completed with %d recommendations", run_id, len(findings))
    except Exception as exc:  # noqa: BLE001 - record failure, never crash worker
        logger.exception("[%s] run failed", run_id)
        db.rollback()
        run = db.get(AnalysisRun, run_id)
        if run is not None:
            run.status = RunStatus.FAILED.value
            run.error = str(exc)
            run.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def run_analysis_sync(*, mock: bool, region: str) -> str:
    """Convenience for tests: create and execute a run synchronously."""
    db = SessionLocal()
    try:
        run = create_run(db, mock=mock, region=region)
        run_id = run.id
    finally:
        db.close()
    execute_run(run_id)
    return run_id
