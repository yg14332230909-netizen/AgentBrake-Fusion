"""ActionGraph construction for compound commands and multi-step tool calls."""
from __future__ import annotations

import re
from dataclasses import asdict

from .models import ActionEdge, ActionGraph, ActionIR, ActionNode, new_id, sha256_text

PARSER_VERSION = "action-graph-v1"


def ensure_action_graph(action: ActionIR, *, run_id: str = "run_default") -> ActionGraph:
    existing = action.metadata.get("action_graph")
    if isinstance(existing, dict) and existing.get("graph_id"):
        action.graph_id = str(existing["graph_id"])
        return _graph_from_dict(existing)
    graph = build_action_graph(action, run_id=run_id)
    action.graph_id = graph.graph_id
    action.metadata["action_graph_id"] = graph.graph_id
    action.metadata["action_graph"] = asdict(graph)
    return graph


def build_action_graph(action: ActionIR, *, run_id: str = "run_default") -> ActionGraph:
    parts = action.command_parts or [action.raw_action]
    nodes: list[ActionNode] = []
    edges: list[ActionEdge] = []
    graph_id = new_id("agraph")

    for idx, part in enumerate(parts):
        node_id = new_id("anode")
        nodes.append(
            ActionNode(
                node_id=node_id,
                action_id=action.action_id,
                semantic_action=action.semantic_action if len(parts) == 1 else _semantic_hint(part, action.semantic_action),
                tool=action.tool,
                target=_target_hint(part, action.affected_assets),
                affected_assets=list(action.affected_assets),
                source_ids=list(action.source_ids),
                side_effect=action.side_effect or _has_side_effect(part),
                confidence=action.parser_confidence,
                metadata={"raw_part": part, "part_index": idx},
            )
        )
        if idx > 0:
            relation = _edge_relation(action.raw_action, idx)
            edges.append(ActionEdge(new_id("aedge"), nodes[idx - 1].node_id, node_id, relation, evidence_refs=[action.action_id]))

    if len(nodes) == 1 and _looks_like_pipe(action.raw_action):
        nodes[0].metadata["pipe_like"] = True

    return ActionGraph(
        graph_id=graph_id,
        run_id=run_id,
        root_action_id=action.action_id,
        raw_action_hash=sha256_text(action.raw_action),
        nodes=nodes,
        edges=edges,
        parser_version=PARSER_VERSION,
        complete=True,
        metadata={"raw_action": action.raw_action, "compound": len(nodes) > 1},
    )


def _graph_from_dict(data: dict) -> ActionGraph:
    return ActionGraph(
        graph_id=str(data["graph_id"]),
        run_id=str(data.get("run_id") or "run_default"),
        root_action_id=str(data.get("root_action_id") or ""),
        raw_action_hash=str(data.get("raw_action_hash") or ""),
        nodes=[ActionNode(**node) for node in data.get("nodes", [])],
        edges=[ActionEdge(**edge) for edge in data.get("edges", [])],
        parser_version=str(data.get("parser_version") or PARSER_VERSION),
        complete=bool(data.get("complete", True)),
        metadata=dict(data.get("metadata") or {}),
    )


def _edge_relation(raw: str, idx: int) -> str:
    before = raw
    separators = re.findall(r"&&|\|\||\||;|>|>>", before)
    sep = separators[idx - 1] if idx - 1 < len(separators) else ";"
    if sep == "|":
        return "pipe"
    if sep in {">", ">>"}:
        return "redirect"
    if sep in {"&&", "||"}:
        return "controlflow"
    return "sequence"


def _looks_like_pipe(raw: str) -> bool:
    return "|" in raw or ">" in raw


def _semantic_hint(part: str, fallback: str) -> str:
    low = part.lower()
    if any(token in low for token in ("curl", "wget", "invoke-webrequest", "http://", "https://")):
        return "send_network_request"
    if ".env" in low or "secret" in low:
        return "read_secret_file"
    if "npm install" in low or "pip install" in low:
        return "install_registry_dependency"
    if "npm test" in low or "pytest" in low:
        return "run_tests"
    return fallback


def _target_hint(part: str, fallback_assets: list[str]) -> str | None:
    host = re.search(r"https?://([^/\s'\"]+)", part, re.I)
    if host:
        return host.group(1)
    path = re.search(r"(\.env[\w.-]*|\.github/workflows/[^\s'\"`|;]+|[A-Za-z0-9_./-]+\.(?:js|py|yml|yaml|json))", part)
    if path:
        return path.group(1)
    return fallback_assets[0] if fallback_assets else None


def _has_side_effect(part: str) -> bool:
    return bool(re.search(r"\b(curl|wget|npm install|pip install|rm|mv|cp|echo|tee|sed -i|publish)\b|>|>>", part, re.I))
