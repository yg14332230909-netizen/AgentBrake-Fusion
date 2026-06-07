# Qwen-Plus Formal Attack-Active Subset

- case_count: 55

| method | cases | targeted_asr | suppression | secure_utility |
|---|---:|---:|---:|---:|
| no_defense | 55 | 1.0000 | 0.0000 | 0.0000 |
| tool_filter | 55 | 0.0000 | 1.0000 | 0.0909 |
| agentbrake_strict | 55 | 0.0000 | 1.0000 | 0.6545 |
| agentbrake_gateway_eval | 55 | 0.0000 | 1.0000 | 0.6364 |
| agentbrake_oracle_user_eval | 55 | 0.0000 | 1.0000 | 0.6727 |
