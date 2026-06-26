# Qwen-Plus Cross-Model Experiment Report

## Canonical Status

- canonical_acceptance: final_acceptance_qwen_formal.json
- canonical_summary: formal_105_after_recovery_fix/e2e_summary.json
- case_selection_source_model: deepseek-v4-flash
- evaluation_model: qwen-plus
- structural_acceptance: PASS
- effectiveness_acceptance: PASS
- overall_status: PASS

## Adapter Smoke

- adapter_status: PASS
- api_call_success: True
- tool_call_parse_success: True
- json_args_parse_success: True

## Formal 105 After Recovery Fix

- rows/raw_runs/full_traces: 525 / 525 / 525
- no_defense targeted_asr: 0.5523809523809524
- tool_filter user_utility: 0.047619047619047616
- agentbrake_strict targeted_asr: 0.0
- agentbrake_strict user_utility: 0.6
- agentbrake_strict secure_utility: 0.6
- agentbrake_gateway_eval secure_utility: 0.5904761904761905
- agentbrake_oracle_user_eval secure_utility: 0.5428571428571428
- attack-active suppression: 1

## Replay Gap Closure

- qwen_derived case_count: 164
- unsafe_count: 107
- safe_count: 57
- trace_missing_count: 0
- sample_gap_shortfall unsafe/safe: 0 / 0
- unsafe_interception_rate: 0.9439252336448598
- safe_pass_rate: 0.6842105263157895
- false_positive_rate: 0.2982456140350877
- block_reason_accuracy: 0.9801980198019802

## Artifact Cleanup

Generic checker outputs are retained under e2e_formal_105/legacy_acceptance and are explicitly non-canonical. Cross-model comparison files now use after-fix canonical Qwen metrics.

## Full AgentDojo E2E

- canonical_acceptance: e2e_full_agentdojo/final_acceptance_full_agentdojo_5method.json
- canonical_summary: e2e_full_agentdojo/e2e_full_5method_summary.json
- overall_status: PASS
- rows/raw_runs/full_traces: 4745 / 4745 / 4745
- full_trace_missing: 0
- no_defense targeted_asr: 0.291886195995785
- tool_filter user_utility: 0.04741833508956796
- agentbrake_strict targeted_asr: 0.002107481559536354
- agentbrake_strict user_utility: 0.6122233930453108
- agentbrake_strict secure_utility: 0.6122233930453108
- agentbrake_gateway_eval secure_utility: 0.6027397260273972
- agentbrake_oracle_user_eval secure_utility: 0.6143308746048473
- attack-active case_count: 277
- agentbrake_strict attack-active suppression: 0.9927797833935018

## Validation

- ruff: PASS
- unit policy tests: PASS
- secret_scan: PASS
- local_path_scan: PASS
