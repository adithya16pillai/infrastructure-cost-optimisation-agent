"""Recommendation ORM model and API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import FindingType, ResourceType, ValidationStatus


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )

    resource_type: Mapped[str] = mapped_column(String(16), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    region: Mapped[str] = mapped_column(String(32), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False)

    # Money is always stored as integer cents to avoid float drift.
    estimated_monthly_savings_cents: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Detector-specific facts (CPU avg, age days, volume size, etc.).
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Validation outcome (filled by PRD 04's validator; defaults to pending).
    validation_status: Mapped[str] = mapped_column(
        String(20), default=ValidationStatus.PENDING.value, nullable=False
    )
    validation_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Raw LLM output, retained for debugging / when JSON parsing fails.
    validation_raw: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Additive (not in PRD 01 table, used by the dashboard cards).
    title: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    run = relationship("AnalysisRun", back_populates="recommendations")


# --- API schemas -----------------------------------------------------------


class RecommendationOut(BaseModel):
    """Full read model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    resource_type: ResourceType
    resource_id: str
    region: str
    finding_type: FindingType
    estimated_monthly_savings_cents: int
    evidence: dict
    validation_status: ValidationStatus
    validation_reasoning: str | None = None
    title: str
    description: str
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def estimated_monthly_savings_usd(self) -> float:
        return round(self.estimated_monthly_savings_cents / 100, 2)


class RecommendationSummary(BaseModel):
    """Lightweight projection for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    resource_id: str
    finding_type: FindingType
    estimated_monthly_savings_cents: int
    validation_status: ValidationStatus
