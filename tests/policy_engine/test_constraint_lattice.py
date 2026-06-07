from agentbrake.models import PolicyDecision
from agentbrake.policy_engine.constraint_lattice import DecisionConstraints, constraints_to_decision
from agentbrake.policy_engine.decision_lattice import DecisionLattice
from agentbrake.policy_engine.rule_schema import RuleHit


def test_constraint_join_maps_to_minimum_public_decision():
    c = DecisionConstraints().join(DecisionConstraints(execution_env="sandbox", network_scope="deny"))

    assert c.execution_env == "sandbox"
    assert c.network_scope == "deny"
    assert constraints_to_decision(c) == "allow_in_sandbox"


def test_decision_lattice_records_constraint_trace():
    baseline = PolicyDecision("dec1", "act1", "allow", 10, [], [], "baseline")
    hit = RuleHit("R1", "approval_needed", "test", "allow", 20, ["needs_gate"], ["human_approval"])

    merged, path = DecisionLattice().merge(baseline, [hit])

    assert merged.decision == "sandbox_then_approval"
    assert path[-1]["via"] == "constraint_lattice"
    assert merged.rule_trace[-1]["engine"] == "constraint_lattice"
