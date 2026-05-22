from reposhield.policy_engine.facts import PolicyFact, PolicyFactSet
from reposhield.policy_engine.invariants import InvariantEngine


def test_semantic_invariant_registry_keeps_legacy_ids():
    facts = PolicyFactSet([
        PolicyFact.of("asset", "touched_type", "secret_file", evidence_refs=["asset1"]),
        PolicyFact.of("contract", "forbidden_file_touch", True, evidence_refs=["asset1"]),
    ])

    hits = InvariantEngine().evaluate(facts)

    assert hits[0].rule_id == "INV-SECRET-001"
    assert hits[0].constraints["execution_env"] == "none"


def test_history_secret_taint_with_network_is_secret_egress():
    facts = PolicyFactSet([
        PolicyFact.of("history", "secret_taint", True, evidence_refs=["state1"]),
        PolicyFact.of("action", "network_capability", True, evidence_refs=["act1"]),
    ])

    hits = InvariantEngine().evaluate(facts)

    assert {hit.rule_id for hit in hits} == {"INV-EGRESS-001"}
