# AgentBrake-Fusion AgentDojo Phase 1.2 Effect Improvement Delta

- case_count: 200
- unsafe cases: 69
- safe cases: 131
- trace_missing_count: 0
- workspace.safe sample_count: 43

## Metrics

| metric | before | after | target |
|---|---:|---:|---|
| unsafe_interception_rate | 1.000000 | 0.985507 | >=0.95 |
| safe_pass_rate | 0.786517 | 0.938931 | >=0.85 |
| false_positive_rate | 0.202247 | 0.053435 | <=0.15 |
| block_reason_accuracy | 1.000000 | 1.000000 | >=0.95 |

## Domain Metrics

| domain | before | after |
|---|---:|---:|
| banking.safe | 0.857143 | 1.000000 |
| banking.unsafe | 1.000000 | 1.000000 |
| slack.safe | 0.571429 | 0.904762 |
| slack.unsafe | 1.000000 | 1.000000 |
| travel.safe | 0.888889 | 0.888889 |
| travel.unsafe | 1.000000 | 1.000000 |
| workspace.safe | 0.000000 | 0.906977 |
| workspace.unsafe | 1.000000 | 0.952381 |

## Remaining Warnings

- release_url_reachable_or_summary_only_declared: summary_only mode declared; public full ZIP is unavailable, canonical committed summaries are the review path
