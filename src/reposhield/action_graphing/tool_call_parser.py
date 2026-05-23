"""Tool-call and history dependency enrichment."""
from __future__ import annotations

from ..models import ActionEdge, ActionNode, new_id
from .base import GraphBuildContext, GraphFragment


def enrich_with_tool_dependencies(fragment: GraphFragment, ctx: GraphBuildContext) -> GraphFragment:
    state = ctx.session_state
    if state is None or not state.secret_taint:
        return fragment
    network_nodes = [node for node in fragment.nodes if node.semantic_action == "send_network_request"]
    if not network_nodes:
        return fragment
    history_node = ActionNode(
        new_id("anode"),
        ctx.action.action_id,
        "read_secret_file",
        ctx.action.tool,
        "history.secret_taint",
        list(state.touched_secret_assets or ["history.secret_taint"]),
        list(ctx.action.source_ids),
        False,
        0.55,
        metadata={
            "parser_name": "tool_call_dependency",
            "inferred": True,
            "state_hash": state.state_hash,
            "source": "persistent_session_state",
        },
    )
    fragment.nodes.insert(0, history_node)
    for node in network_nodes:
        fragment.edges.append(
            ActionEdge(
                new_id("aedge"),
                history_node.node_id,
                node.node_id,
                "memoryflow",
                evidence_refs=[state.session_state_id, ctx.action.action_id],
                confidence=0.55,
                metadata={"parser": "tool_call_dependency", "inferred": True, "state_hash": state.state_hash},
            )
        )
    fragment.confidence = min(fragment.confidence, 0.55)
    return fragment
