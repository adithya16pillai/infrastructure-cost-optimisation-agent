from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.analysis_run import (
    AnalysisRun,
    AnalysisRunOut,
    TriggerAnalysisResponse,
)
from app.models.enums import RunStatus
from app.models.recommendation import Recommendation, RecommendationOut
from app.services import analysis_service

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "mock_aws": settings.mock_aws,
        "llm_enabled": settings.has_llm,
    }


@router.post("/analysis/run", response_model=TriggerAnalysisResponse, status_code=202)
def trigger_analysis(
    background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> TriggerAnalysisResponse:
    run = analysis_service.create_run(
        db, mock=settings.mock_aws, region=settings.aws_region
    )
    background_tasks.add_task(analysis_service.execute_run, run.id)
    return TriggerAnalysisResponse(run_id=run.id, status=RunStatus(run.status))


@router.get("/analysis/{run_id}", response_model=AnalysisRunOut)
def get_run(run_id: str, db: Session = Depends(get_db)) -> AnalysisRun:
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/runs", response_model=list[AnalysisRunOut])
def list_runs(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
) -> list[AnalysisRun]:
    return list(
        db.scalars(
            select(AnalysisRun).order_by(AnalysisRun.started_at.desc()).limit(limit)
        ).all()
    )


@router.get("/recommendations", response_model=list[RecommendationOut])
def list_recommendations(
    run_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[Recommendation]:
    stmt = select(Recommendation).order_by(
        Recommendation.estimated_monthly_savings_cents.desc()
    )
    if run_id:
        stmt = stmt.where(Recommendation.run_id == run_id)
    return list(db.scalars(stmt).all())
