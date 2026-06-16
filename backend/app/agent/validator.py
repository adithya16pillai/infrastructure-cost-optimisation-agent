"""LLM validation layer.

Reviews each aggregated finding for feasibility (can this safely be done?) and
risk (what could break?), returning a structured verdict. Uses the Anthropic SDK
directly so the call is transparent.

When no ANTHROPIC_API_KEY is configured, a deterministic heuristic stands in so
the app still runs end-to-end with zero setup.

Robustness (per PRD): unparseable model output falls back to `needs_review` with
the raw output retained; API/transport errors are caught, recorded in
`state["errors"]`, and that finding is marked `needs_review`.
"""
from __future__ import annotations

import json
import logging
from typing import Literal

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class ValidationVerdict(BaseModel):
    status: Literal["approve", "needs_review", "reject"]
    reasoning: str = Field(..., max_length=600)
    risk_factors: list[str] = Field(default_factory=list, max_length=5)


SYSTEM_PROMPT = """You are a senior cloud engineer reviewing automated AWS cost-saving recommendations
before they are shown to a human operator. Your job is to assess whether the
recommendation is safe to act on and whether the evidence supports it.

For each recommendation, output a JSON object matching this schema exactly:
{
  "status": "approve" | "needs_review" | "reject",
  "reasoning": "<one or two sentences>",
  "risk_factors": ["<short risk>", ...]   // up to 5, can be empty
}

Decision guide:
- approve: evidence is strong and the action is reversible or low risk.
- needs_review: evidence is suggestive but context is missing (e.g. production
  tags, batch workloads with low average CPU, snapshots that may be retention).
- reject: evidence is too weak, contradictory, or the resource is clearly
  load-bearing.

Be conservative on anything tagged production or with compliance/retention
keywords in descriptions. Output ONLY the JSON object, no preamble."""


def format_user_message(finding: dict) -> str:
    dollars = finding["estimated_monthly_savings_cents"] / 100
    return (
        f"Finding type: {finding['finding_type']}\n"
        f"Resource: {finding['resource_type']} {finding['resource_id']} "
        f"in {finding['region']}\n"
        f"Estimated monthly savings: ${dollars:.2f}\n"
        f"Evidence:\n{json.dumps(finding['evidence'], indent=2)}"
    )


# --- Claude client (lazy singleton) ----------------------------------------

_client = None


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic

        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _validate_one(finding: dict) -> tuple[ValidationVerdict, str]:
    user_msg = format_user_message(finding)
    resp = _get_client().messages.create(
        model=settings.validator_model,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = next((b.text for b in resp.content if b.type == "text"), "").strip()
    try:
        data = json.loads(raw)
        verdict = ValidationVerdict(**data)
    except Exception:
        # Fail safe: surface for human review, store raw for debugging.
        return (
            ValidationVerdict(
                status="needs_review",
                reasoning="Validator returned unparseable output; defaulting to needs_review.",
                risk_factors=[],
            ),
            raw,
        )
    return verdict, raw


# --- Heuristic fallback (no API key) ---------------------------------------


def _heuristic(finding: dict) -> ValidationVerdict:
    ftype = finding["finding_type"]
    ev = finding["evidence"]

    if ftype == "unattached_ebs":
        return ValidationVerdict(
            status="approve",
            reasoning=(
                "Unattached volumes incur cost with no compute benefit. Snapshot first "
                "for safety, then delete. Low operational risk."
            ),
            risk_factors=["data loss if the volume is still needed"],
        )
    if ftype == "old_snapshot":
        age = ev.get("age_days", 0)
        if age >= 365:
            return ValidationVerdict(
                status="approve",
                reasoning=(
                    f"Snapshot is {age} days old, well past any reasonable retention. "
                    "Very unlikely to be needed for recovery; safe to delete."
                ),
                risk_factors=[],
            )
        return ValidationVerdict(
            status="needs_review",
            reasoning=(
                f"Snapshot is {age} days old. Confirm it is not part of an active backup "
                "or compliance retention chain before deleting."
            ),
            risk_factors=["possible compliance/retention requirement"],
        )
    if ftype == "idle_ec2":
        tags = ev.get("tags", {}) or {}
        env = str(tags.get("Environment", "")).lower()
        name = str(tags.get("Name", "")).lower()
        if "prod" in env or "prod" in name:
            return ValidationVerdict(
                status="needs_review",
                reasoning=(
                    "Low CPU but the instance is tagged/named like production. Confirm it "
                    "is not a warm standby or burst-capacity host before stopping."
                ),
                risk_factors=["production-tagged", "possible warm standby"],
            )
        return ValidationVerdict(
            status="approve",
            reasoning=(
                f"Sustained CPU of {ev.get('avg_cpu_percent')}% over "
                f"{ev.get('days_observed')} days indicates the instance is idle. "
                "Stopping or rightsizing should be safe."
            ),
            risk_factors=["verify no scheduled jobs depend on it"],
        )

    return ValidationVerdict(
        status="needs_review",
        reasoning="Unrecognised recommendation type; routing to human review.",
        risk_factors=[],
    )


# --- Graph node ------------------------------------------------------------


def validate_node(state) -> dict:
    """Review each aggregated finding for feasibility and risk."""
    findings = state.get("aggregated_findings", [])
    if not findings:
        # Empty findings list: skip the validator entirely (no API call).
        return {"validated_findings": []}

    errors = list(state.get("errors", []))
    validated: list[dict] = []

    use_llm = settings.has_llm
    logger.info(
        "[%s] validating %d findings (%s)",
        state.get("run_id", "?"),
        len(findings),
        f"Claude:{settings.validator_model}" if use_llm else "heuristic",
    )

    for f in findings:
        if not use_llm:
            verdict = _heuristic(f)
            validated.append(
                {
                    **f,
                    "validation_status": verdict.status,
                    "validation_reasoning": verdict.reasoning,
                    "validation_raw": verdict.model_dump_json(),
                }
            )
            continue

        try:
            verdict, raw = _validate_one(f)
            validated.append(
                {
                    **f,
                    "validation_status": verdict.status,
                    "validation_reasoning": verdict.reasoning,
                    "validation_raw": raw,
                }
            )
        except Exception as e:  # noqa: BLE001 - API/transport error
            logger.error("Validator error on %s: %s", f["resource_id"], e)
            errors.append(f"Validator error on {f['resource_id']}: {e}")
            validated.append(
                {
                    **f,
                    "validation_status": "needs_review",
                    "validation_reasoning": f"Validator failed: {e}",
                    "validation_raw": "",
                }
            )

    return {"validated_findings": validated, "errors": errors}
