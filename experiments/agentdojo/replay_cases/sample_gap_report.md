# AgentDojo Replay Sample Gap Report

Trace completeness and benchmark sample sufficiency are reported separately.

- Trace missing count: 0
- Generated unsafe cases: 10
- Generated safe cases: 19
- Phase 1 unsafe target: 50
- Phase 1 safe target: 50
- Phase 1 unsafe shortfall: 40
- Phase 1 safe shortfall: 31
- Skipped successful attacks with missing sink/taxonomy gap: 13
- Estimated minimum additional DeepSeek calls for Phase 1: 71

Cases by suite:
- banking: 11
- slack: 5
- travel: 11
- workspace: 2

Cases by violation type:
- benign_user_requested_booking: 10
- benign_user_requested_payment: 5
- benign_user_requested_slack_message: 4
- booking_target_from_untrusted_source: 1
- calendar_side_effect: 2
- financial_commit_from_untrusted_source: 6
- private_data_exfiltration_to_external_sink: 1

Insufficient or missing coverage should be closed only by collecting additional same-model AgentDojo full traces. DeepSeek-chat logs may be used as reference only, not mixed into DeepSeekV4-Flash primary results.
