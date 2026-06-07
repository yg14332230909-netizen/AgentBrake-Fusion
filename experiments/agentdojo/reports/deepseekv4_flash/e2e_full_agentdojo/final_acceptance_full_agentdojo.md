# Full AgentDojo Final Acceptance

Structural acceptance: PASS
Effectiveness acceptance: PASS
Overall status: PASS

| check | status | detail |
|---|---|---|
| plan_exists | PASS | full_agentdojo_case_plan.json |
| plan_frozen | PASS | plan_frozen must be true |
| plan_model_attack_present | PASS | plan requires model and attack |
| plan_sha256_exists | PASS | full_agentdojo_case_plan.sha256 |
| plan_sha256_matches | PASS | sha256 must match frozen plan |
| frozen_plan_exists | PASS | full_agentdojo_case_plan_frozen.json |
| frozen_plan_sha256_exists | PASS | full_agentdojo_case_plan_frozen.sha256 |
| frozen_plan_matches_current_plan | PASS | frozen plan must match counted full_agentdojo_case_plan.json |
| frozen_plan_sha256_matches | PASS | frozen plan sha256 must match |
| full_run_manifest_exists | PASS | full_run_manifest.json |
| full_run_manifest_counts_match | PASS | manifest counts must match files and summary |
| per_rows_match_plan_methods | PASS | per-case rows must equal case_count x methods |
| method_case_counts_consistent | PASS | each method must cover the frozen plan |
| trace_files_exist | PASS | missing=0 |
| trace_schema_valid | PASS | full traces require agentdojo_trace_v1 |
| raw_full_counts_match_or_manifest | PASS | extra raw/full files require excluded_runs_manifest.json |
| no_api_key_or_local_path | PASS | reports must not contain API keys or local absolute paths |
| artifact_manifest_exists | PASS | artifact_manifest.json |
| artifact_manifest_summary_only | PASS | artifact_manifest must declare summary_only and raw_full_traces_committed=false |
| release_pointer_exists | PASS | release_artifact_url_or_path.txt |
| attack_active_summary_exists | PASS | attack_active_subset_summary.json |
| failure_clusters_exist | PASS | failure_clusters json/md |
| confirmation_summary_exists | PASS | confirmation_summary json/md |
| blocked_recovery_summary_exists | PASS | blocked_recovery_summary json/md |
| effectiveness_thresholds | PASS | AgentBrake full E2E thresholds |
| attack_active_thresholds | PASS | attack-active subset thresholds |
