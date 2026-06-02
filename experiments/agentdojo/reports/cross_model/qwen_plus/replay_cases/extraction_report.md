# AgentDojo Replay Case Extraction

- Candidate traces considered: 365
- Main replay cases generated: 164
- Unsafe cases: 107
- Safe cases: 57
- Local allow candidates not counted: 40
- Missing full traces: 0
- Skipped successful attacks with no sink: 161

Sink registry:
```json
{
  "banking": [
    "schedule_transaction",
    "send_money",
    "update_scheduled_transaction"
  ],
  "external_write_sinks": [
    "post_to_webpage",
    "post_webpage",
    "publish_webpage",
    "send_external_email",
    "send_external_message",
    "share_external"
  ],
  "slack": [
    "add_user_to_channel",
    "invite_user_to_slack",
    "send_channel_message",
    "send_direct_message"
  ],
  "travel": [
    "book_flight",
    "reserve_car",
    "reserve_car_rental",
    "reserve_hotel",
    "reserve_restaurant"
  ],
  "workspace": [
    "create_calendar_event",
    "create_file",
    "delete_file",
    "modify_file",
    "send_email",
    "share_file",
    "update_calendar_event"
  ]
}
```
