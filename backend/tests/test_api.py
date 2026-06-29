from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "mock_cloud": True}


def test_api_health_lists_providers():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mock_cloud"] is True
    assert set(body["providers"]) == {"aws", "gcp"}


@pytest.mark.parametrize(
    "provider,region",
    [("aws", "us-east-1"), ("gcp", "us-central1")],
)
def test_trigger_run_and_fetch_recommendations(provider, region):
    # TestClient executes BackgroundTasks synchronously before returning.
    resp = client.post("/api/analysis/run", json={"provider": provider})
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    status = client.get(f"/api/analysis/{run_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "completed"
    assert body["provider"] == provider
    assert body["region"] == region
    assert body["total_recommendations"] == 9
    assert body["total_estimated_savings_cents"] > 0

    recs = client.get("/api/recommendations", params={"run_id": run_id})
    assert recs.status_code == 200
    data = recs.json()
    assert len(data) == 9
    for r in data:
        assert r["provider"] == provider
        assert r["validation_status"] in {"approve", "needs_review", "reject"}
        assert r["validation_reasoning"]
        assert r["estimated_monthly_savings_usd"] > 0


def test_trigger_defaults_to_aws_when_no_body():
    resp = client.post("/api/analysis/run")
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]
    body = client.get(f"/api/analysis/{run_id}").json()
    assert body["provider"] == "aws"
