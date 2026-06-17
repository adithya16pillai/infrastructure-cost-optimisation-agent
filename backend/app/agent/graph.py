from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from app.agent.detectors import idle_ec2, old_snapshots, unattached_ebs
from app.agent.state import AgentState
from app.agent.validator import validate_node
from app.aws.client import AwsClient, build_client

logger = logging.getLogger(__name__)


def ingest_node(state: AgentState, aws_client: AwsClient) -> dict:
    run_id = state.get("run_id", "?")
    logger.info("[%s] ingest (region=%s)", run_id, aws_client.region)
    return {
        "raw_data": {
            "ec2_instances": aws_client.list_ec2_instances(),
            "ebs_volumes": aws_client.list_ebs_volumes(),
            "ebs_snapshots": aws_client.list_ebs_snapshots(),
        },
        "errors": [],
    }


def aggregate_node(state: AgentState) -> dict:
    findings = (
        state.get("idle_ec2_findings", [])
        + state.get("unattached_ebs_findings", [])
        + state.get("old_snapshot_findings", [])
    )
    findings.sort(key=lambda f: f["estimated_monthly_savings_cents"], reverse=True)
    logger.info("[%s] aggregate: %d findings", state.get("run_id", "?"), len(findings))
    return {"aggregated_findings": findings}


def build_graph(aws_client: AwsClient):
    graph = StateGraph(AgentState)

    graph.add_node("ingest", lambda state: ingest_node(state, aws_client))
    graph.add_node("detect_idle_ec2", lambda state: idle_ec2.run(state, aws_client))
    graph.add_node(
        "detect_unattached_ebs", lambda state: unattached_ebs.run(state, aws_client)
    )
    graph.add_node(
        "detect_old_snapshots", lambda state: old_snapshots.run(state, aws_client)
    )
    graph.add_node("aggregate", aggregate_node)
    graph.add_node("validate", validate_node)

    graph.set_entry_point("ingest")

    # fan-out
    graph.add_edge("ingest", "detect_idle_ec2")
    graph.add_edge("ingest", "detect_unattached_ebs")
    graph.add_edge("ingest", "detect_old_snapshots")

    # fan-in
    graph.add_edge("detect_idle_ec2", "aggregate")
    graph.add_edge("detect_unattached_ebs", "aggregate")
    graph.add_edge("detect_old_snapshots", "aggregate")

    graph.add_edge("aggregate", "validate")
    graph.add_edge("validate", END)

    return graph.compile()


def run_agent(*, run_id: str, mock: bool, region: str) -> list[dict]:
    aws_client = build_client(mock=mock, region=region)
    graph = build_graph(aws_client)
    final_state = graph.invoke({"run_id": run_id})
    return final_state.get("validated_findings", [])
