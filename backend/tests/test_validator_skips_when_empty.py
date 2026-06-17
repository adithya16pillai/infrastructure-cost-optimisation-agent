from __future__ import annotations

from app.agent import validator


def test_no_api_call_when_findings_empty(monkeypatch):
    monkeypatch.setattr(validator.settings, "anthropic_api_key", "test-key")

    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        raise AssertionError("the Anthropic client must not be built for empty findings")

    monkeypatch.setattr(validator, "_get_client", boom)

    out = validator.validate_node(
        {"run_id": "t", "aggregated_findings": [], "errors": []}
    )

    assert out["validated_findings"] == []
    assert calls["n"] == 0
