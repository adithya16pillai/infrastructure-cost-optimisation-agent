from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import RunStatus


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(
        String(20), default=RunStatus.RUNNING.value, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    mock_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Cloud provider this run analysed ("aws" | "gcp").
    provider: Mapped[str] = mapped_column(
        String(16), default="aws", nullable=False
    )

    # Denormalised for dashboard speed.
    total_recommendations: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    total_estimated_savings_cents: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Additive: region the run queried (needed to drive the agent).
    region: Mapped[str] = mapped_column(String(32), nullable=False)

    recommendations = relationship(
        "Recommendation",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AnalysisRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: RunStatus
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    mock_mode: bool
    provider: str
    total_recommendations: int
    total_estimated_savings_cents: int
    region: str


class TriggerAnalysisResponse(BaseModel):
    run_id: str
    status: RunStatus
