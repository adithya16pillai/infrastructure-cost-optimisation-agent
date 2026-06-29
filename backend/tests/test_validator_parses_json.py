from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agent import validator


def _finding() -> dict:
    return {
        "provider": "aws",
        "finding_type": "idle_compute",
        "resource_type": "compute",
        "resource_id": "i-0idle001",
        "region": "us-east-1",
        "estimated_monthly_savings_cents": 7008,
        "evidence": {"avg_cpu_percent": 2.0, "days_observed": 14, "tags": {}},
    }


def _fake_client_returning(text: str):
    def create(**kwargs):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])

    return SimpleNamespace(messages=SimpleNamespace(create=create))


@pytest.mark.parametrize("status", ["approve", "needs_review", "reject"])
def test_verdict_status_flows_through(monkeypatch, status):
    monkeypatch.setattr(validator.settings, "anthropic_api_key", "test-key")
    text = '{"status": "%s", "reasoning": "evidence reviewed", "risk_factors": ["x"]}' % status
    monkeypatch.setattr(validator, "_get_client", lambda: _fake_client_returning(text))

    state = {"run_id": "t", "aggregated_findings": [_finding()], "errors": []}
    out = validator.validate_node(state)

    f = out["validated_findings"][0]
    assert f["validation_status"] == status
    assert f["validation_reasoning"] == "evidence reviewed"
    assert out["errors"] == []
