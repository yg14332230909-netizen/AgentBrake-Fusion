# Cross-Model Summary

Scope: formal 105 E2E only. Full AgentDojo for Qwen is not run in this stage.

| model | no_defense_asr | strict_asr | strict_user_utility | strict_secure_utility | utility_retention |
|---|---:|---:|---:|---:|---:|
| deepseek-v4-flash | 0.2762 | 0.0000 | 0.7524 | 0.7524 | 0.9875 |
| qwen-plus | 0.5238 | 0.0000 | 0.5429 | 0.5429 | 1.1633 |

Interpretation:
- Different no_defense ASR reflects different natural attack sensitivity.
- Attack-active subset is the core security comparison when baseline ASR differs.
- Replay and E2E are different metrics and should not be treated as equivalent.
- Qwen-derived replay cases come from Qwen traces and are not mixed with DeepSeek-derived cases.
- Formal E2E uses the same frozen task plan as DeepSeek, so model-level comparison is appropriate.
