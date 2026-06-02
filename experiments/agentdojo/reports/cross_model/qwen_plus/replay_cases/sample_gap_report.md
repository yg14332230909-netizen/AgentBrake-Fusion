# AgentDojo Replay Sample Gap Report

Trace completeness and benchmark sample sufficiency are reported separately.

- Trace missing count: 0
- Generated unsafe cases: 107
- Generated safe cases: 57
- Phase 1 unsafe target: 50
- Phase 1 safe target: 50
- Phase 1 unsafe shortfall: 0
- Phase 1 safe shortfall: 0
- Skipped successful attacks with missing sink/taxonomy gap: 161
- Estimated minimum additional same-model calls for Phase 1: 0

Cases by suite:
- banking: 58
- slack: 33
- travel: 22
- workspace: 51

Cases by violation type:
- benign_file_or_workspace_side_effect: 27
- benign_user_requested_booking: 16
- benign_user_requested_payment: 12
- benign_user_requested_slack_message: 2
- booking_target_from_untrusted_source: 6
- calendar_side_effect: 4
- destructive_file_operation: 5
- financial_commit_from_untrusted_source: 46
- membership_expansion_from_untrusted_source: 10
- message_recipient_from_untrusted_source: 13
- private_data_exfiltration: 15
- private_data_exfiltration_to_external_sink: 8

Insufficient or missing coverage should be closed only by collecting additional same-model AgentDojo full traces. Cross-model traces may be used as reference only, not mixed into the primary replay benchmark.
