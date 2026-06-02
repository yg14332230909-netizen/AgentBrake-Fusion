# Qwen-Plus Cross-Model Experiment Report

## Purpose
Evaluate whether RepoShield AgentDojo defenses transfer from DeepSeekV4-Flash to Qwen-Plus without mixing replay cases across models.

## Model
- model_key: qwen_plus
- model_id: qwen-plus
- provider: alibaba_dashscope
- adapter: openai_compatible_chat
- API key: environment variable only

## Adapter Smoke
- status: PASS
- tool_call_parse_success: true
- trace_saved: true

## Sample Source
Formal E2E uses the same frozen 105-case plan as DeepSeek. Replay cases are derived only from Qwen-Plus no_defense traces.

## Formal 105 E2E
- case_count: 105
- per_case_rows: 525
- no_defense targeted_asr: 0.5238095238095238
- reposhield_strict targeted_asr: 0.0
- reposhield_strict secure_utility: 0.5428571428571428
- tool_filter user_utility: 0.047619047619047616
- attack_active_suppression_rate: 1.0

## Qwen-Derived Replay
- case_count: 70
- unsafe_count: 44
- safe_count: 26
- trace_missing: 0
- unsafe_interception_rate: 0.9318181818181818
- safe_pass_rate: 0.7307692307692307
- false_positive_rate: 0.15384615384615385

## Full AgentDojo
Status: SKIPPED in this stage. Reasons: Qwen formal strict secure_utility is below the recommended 0.60 threshold, and Qwen-derived replay sample coverage has shortfalls (unsafe 6, safe 24). Full run should proceed only after accepting this utility/replay coverage risk and the larger cost envelope.

## Tool-Filter Baseline
tool_filter user_utility: 0.047619047619047616

## Failure Clusters
See `e2e_formal_105/failure_clusters.json` and `replay/agentdojo_derived_replay_summary.json`.

## Limitations
- Formal secure utility is below the recommended Qwen threshold.
- Replay cases from formal traces do not meet the 50/50 safe/unsafe target.
- Full AgentDojo Qwen is not run in this stage.

## Recommendation
Proceed to a larger Qwen run only if the utility shortfall is acceptable or after recovery tuning is planned.
