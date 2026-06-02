# AgentDojo Replay Sample Gap Report

Trace completeness and benchmark sample sufficiency are reported separately.

- Trace missing count: 0
- Generated unsafe cases: 44
- Generated safe cases: 26
- Phase 1 unsafe target: 50
- Phase 1 safe target: 50
- Phase 1 unsafe shortfall: 6
- Phase 1 safe shortfall: 24
- Skipped successful attacks with missing sink/taxonomy gap: 30
- Estimated minimum additional same-model calls for Phase 1: 30

Cases by suite:
- banking: 21
- slack: 11
- travel: 17
- workspace: 21

Cases by violation type:
- benign_file_or_workspace_side_effect: 9
- benign_user_requested_booking: 13
- benign_user_requested_payment: 2
- benign_user_requested_slack_message: 2
- booking_target_from_untrusted_source: 4
- calendar_side_effect: 3
- destructive_file_operation: 1
- financial_commit_from_untrusted_source: 19
- membership_expansion_from_untrusted_source: 2
- message_recipient_from_untrusted_source: 6
- private_data_exfiltration: 8
- private_data_exfiltration_to_external_sink: 1

Insufficient or missing coverage should be closed only by collecting additional same-model AgentDojo full traces. Cross-model traces may be used as reference only, not mixed into the primary replay benchmark.
