# DeepSeekV4-Flash AgentDojo Corrected Summary

This report separates standard AgentDojo E2E mini evaluation, smoke replay, AgentDojo-derived tool-boundary replay, confirmation subsets, and blocked recovery debug. Replay benchmarks are not standard AgentDojo E2E scores.

## Paired Mini E2E

Real AgentDojo paired mini evaluation for `deepseek-v4-flash` and `important_instructions`.

| suite | tool calls | blocked | repeated | user utility | targeted ASR |
|---|---:|---:|---:|---:|---:|
| banking | 70 | 4 | 1 | 0.500000 | 0.000000 |
| slack | 18 | 6 | 1 | 0.333333 | 0.000000 |
| travel | 93 | 6 | 3 | 0.625000 | 0.000000 |
| workspace | 20 | 0 | 0 | 1.000000 | 0.000000 |

## Smoke Replay

Manual/semi-manual sanity benchmark only. It is not used as the official AgentDojo-derived benchmark score. The legacy 24-case smoke result must not be compared with the trace-derived replay case count.

## AgentDojo-Derived Tool-Boundary Replay

- standard_agentdojo_e2e_score: `false`
- Source: real AgentDojo full traces only.
- case_count: 144
- unsafe_interception_rate: 1.000000
- safe_pass_rate: 0.786517
- false_positive_rate: 0.202247
- block_reason_accuracy: 1.000000
- unsafe cases: 55
- safe cases: 89
- local allow candidates not counted: 22
- skipped no-sink/taxonomy gaps: 65
- Phase 1 shortfall: unsafe 0, safe 0

Domain pass rates:

- banking.safe: 42/49 = 0.857143
- banking.unsafe: 18/18 = 1.000000
- slack.safe: 12/21 = 0.571429
- slack.unsafe: 27/27 = 1.000000
- travel.safe: 16/18 = 0.888889
- travel.unsafe: 3/3 = 1.000000
- workspace.safe: 0/1 = 0.000000
- workspace.unsafe: 7/7 = 1.000000

Counts by violation type:

- benign_file_or_workspace_side_effect: 1
- benign_user_requested_booking: 18
- benign_user_requested_payment: 49
- benign_user_requested_slack_message: 21
- booking_target_from_untrusted_source: 3
- calendar_side_effect: 2
- financial_commit_from_untrusted_source: 18
- membership_expansion_from_untrusted_source: 14
- message_channel_from_untrusted_source: 1
- message_recipient_from_untrusted_source: 1
- private_data_exfiltration: 5
- private_data_exfiltration_to_external_sink: 11

## Confirmation Subsets

Confirmation subset normalized aggregate was regenerated separately from the main paired-mini aggregate.

```csv
suite,method,sample_count,user_utility,targeted_asr,security_rate,secure_utility,tool_call_count,blocked_tool_call_count,repeated_block_count
banking,agentdojo_firewall,8,1.000000,0.000000,1.000000,1.000000,62,0,0
slack,agentdojo_firewall,8,0.500000,0.000000,1.000000,0.500000,28,7,0
travel,agentdojo_firewall,16,0.375000,0.000000,1.000000,0.375000,89,2,0
```

Focused confirmation recovery rerun after policy changes:

| suite | mode | user utility | security | confirmation execute | repeated block |
|---|---|---:|---:|---:|---:|
| banking | oracle_user_eval | 1.0 | 1.0 | 1.0 | 0.0 |
| banking | gateway_eval | 1.0 | 1.0 | 1.0 | 0.0 |
| slack | oracle_user_eval | 0.5 | 1.0 | 1.0 | 0.0 |
| slack | gateway_eval | 0.5 | 1.0 | 1.0 | 0.0 |
| travel | oracle_user_eval | 0.375 | 1.0 | 1.0 | 0.0 |
| travel | gateway_eval | 0.375 | 1.0 | 1.0 | 0.0 |

## Blocked Recovery Debug

- analyzed cases: 14
- blocked_injected_action_recovery_failed: 5
- confirmation_not_executed: 4
- repeated_same_blocked_action: 5

## Stale Metric Guard

Derived replay case_count, safe_pass_rate, and false_positive_rate above are copied from the canonical summary at `experiments/agentdojo/reports/deepseekv4_flash/replay/agentdojo_derived_replay_summary.json`, with detailed decisions in `experiments/agentdojo/reports/deepseekv4_flash/replay/agentdojo_derived_replay_results.json`. Smoke replay metrics and root-level legacy replay files are intentionally not presented as official benchmark scores.
