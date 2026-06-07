# Cross-Model Formal Comparison

| model | scope | no_defense_asr | strict_asr | strict_user_utility | strict_secure_utility | strict_vs_tool_filter_gap | overall |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| deepseek-v4-flash | formal_105 | 0.2761904761904762 | 0.0 | 0.7523809523809524 | 0.7523809523809524 | 0.704761904761904784 | WARN |
| qwen-plus | formal_105_after_recovery_fix | 0.5523809523809524 | 0.0 | 0.6 | 0.6 | 0.552380952380952384 | PASS |

- Qwen metrics use after-fix canonical artifacts only.
- Qwen replay cases are Qwen-derived and not mixed with DeepSeek traces.
