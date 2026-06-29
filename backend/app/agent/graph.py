from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from app.agent.detectors import idle_compute, old_snapshots, unattached_disk
from app.agent.state import AgentState
from app.agent.validator import validate_node
from app.cloud.base import CloudClient
from app.cloud.factory import build_client

logger = logging.getLogger(__name__)


def ingest_node(state: AgentState, client: CloudClient) -> dict:
    run_id = state.get("run_id", "?")
    logger.info(
        "[%s] ingest (provider=%s region=%s)", run_id, client.provider, client.region
    )
    return {
        "raw_data": {
            "compute_instances": client.list_compute_instances(),
            "disks": client.list_disks(),
            "snapshots": client.list_snapshots(),
        },
        "errors": [],
    }


def aggregate_node(state: AgentState) -> dict:
    findings = (
        state.get("idle_compute_findings", [])
        + state.get("unattached_disk_findings", [])
        + state.get("old_snapshot_findings", [])
    )
    findings.sort(key=lambda f: f["estimated_monthly_savings_cents"], reverse=True)
    logger.info("[%s] aggregate: %d findings", state.get("run_id", "?"), len(findings))
    return {"aggregated_findings": findings}


def build_graph(client: CloudClient):
    graph = StateGraph(AgentState)

    graph.add_node("ingest", lambda state: ingest_node(state, client))
    graph.add_node("detect_idle_compute", lambda state: idle_compute.run(state, client))
    graph.add_node(
        "detect_unattached_disk", lambda state: unattached_disk.run(state, client)
    )
    graph.add_node(
        "detect_old_snapshots", lambda state: old_snapshots.run(state, client)
    )
    graph.add_node("aggregate", aggregate_node)
    graph.add_node("validate", validate_node)

    graph.set_entry_point("ingest")

    # fan-out
    graph.add_edge("ingest", "detect_idle_compute")
    graph.add_edge("ingest", "detect_unattached_disk")
    graph.add_edge("ingest", "detect_old_snapshots")

    # fan-in
    graph.add_edge("detect_idle_compute", "aggregate")
    graph.add_edge("detect_unattached_disk", "aggregate")
    graph.add_edge("detect_old_snapshots", "aggregate")

    graph.add_edge("aggregate", "validate")
    graph.add_edge("validate", END)

    return graph.compile()


def run_agent(*, run_id: str, provider: str, mock: bool, region: str) -> list[dict]:
    client = build_client(provider=provider, mock=mock, region=region)
    graph = build_graph(client)
    final_state = graph.invoke({"run_id": run_id, "provider": provider})
    return final_state.get("validated_findings", [])
