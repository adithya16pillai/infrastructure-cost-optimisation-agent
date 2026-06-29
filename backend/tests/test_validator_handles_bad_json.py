from __future__ import annotations

from types import SimpleNamespace

from app.agent import validator


def _finding() -> dict:
    return {
        "provider": "aws",
        "finding_type": "unattached_disk",
        "resource_type": "disk",
        "resource_id": "vol-0unatt001",
        "region": "us-east-1",
        "estimated_monthly_savings_cents": 4000,
        "evidence": {"size_gb": 500, "disk_type": "gp3"},
    }


def _fake_client_returning(text: str):
    def create(**kwargs):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])

    return SimpleNamespace(messages=SimpleNamespace(create=create))


def test_bad_json_falls_back_and_preserves_raw(monkeypatch):
    monkeypatch.setattr(validator.settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(validator, "_get_client", lambda: _fake_client_returning("not json"))

    state = {"run_id": "t", "aggregated_findings": [_finding()], "errors": []}
    out = validator.validate_node(state)

    f = out["validated_findings"][0]
    assert f["validation_status"] == "needs_review"
    assert f["validation_raw"] == "not json"
    # A parse failure is not a transport error; nothing appended to errors.
    assert out["errors"] == []
