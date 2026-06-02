# Qwen-Plus Cross-Model Experiment Report

## Scope

Evaluate whether RepoShield AgentDojo defenses transfer to Qwen-Plus with Qwen-derived replay cases only. DeepSeek artifacts are reference baselines and are not mixed into Qwen replay extraction.

## Adapter Smoke

- adapter_status: PASS
- api_call_success: True
- tool_call_parse_success: True
- json_args_parse_success: True
- secret_scan: PASS

## Formal 105 Before Recovery Fix

- rows/raw_runs/full_traces: 525 / 525 / 525
- no_defense targeted_asr: 0.5238095238095238
- reposhield_strict targeted_asr: 0.0
- reposhield_strict secure_utility: 0.5428571428571428
- effectiveness status before fix: WARN because strict secure_utility was below 0.60.

## Replay Gap Closure

- qwen_derived case_count: 164
- unsafe_count: 107
- safe_count: 57
- trace_missing_count: 0
- sample_gap_shortfall unsafe/safe: 0 / 0
- unsafe_interception_rate: 0.9439252336448598
- safe_pass_rate: 0.6491228070175439
- false_positive_rate: 0.2982456140350877
- block_reason_accuracy: 0.9801980198019802

## Utility Forensics And Fix

Utility analysis separated Qwen baseline failures from RepoShield policy/recovery gaps. The implemented fix is model-agnostic: clearer blocked-result continuation guidance plus travel email authorization handling for user-authorized destinations. No Qwen-specific safety relaxation was added.

## Formal 105 After Recovery Fix

- rows/raw_runs/full_traces: 525 / 525 / 525
- no_defense targeted_asr: 0.5523809523809524
- reposhield_strict targeted_asr: 0.0
- reposhield_strict secure_utility: 0.6
- reposhield_gateway_eval secure_utility: 0.5904761904761905
- reposhield_oracle_user_eval secure_utility: 0.5428571428571428
- attack-active suppression: 1
- final structural_acceptance: PASS
- final effectiveness_acceptance: PASS
- final overall_status: PASS

## Canonical Files

- canonical acceptance: final_acceptance_qwen_formal.json
- canonical after-fix formal dir: formal_105_after_recovery_fix
- replay manifest: replay_cases/manifest_qwen_derived.json
- replay summary: replay/qwen_derived_replay_summary.json
- utility forensics: utility_forensics/qwen_utility_gap_summary.json

## Notes

The final strict secure_utility equals the minimum target 0.60. This should be treated as passing the stated threshold, not as comfortable margin. Further work should target Slack and Banking recovery false positives without relaxing injected recipient, private exfiltration, or injected booking-target blocking.
