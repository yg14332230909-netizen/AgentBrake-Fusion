# DeepSeekV4-Flash AgentDojo Experiment

Date: 2026-05-31

Model/API source: DeepSeekV4-Flash via OpenAI-compatible API.

Base URL type: `https://api.deepseek.com`

Model ID: `deepseek-v4-flash`

AgentDojo version: `v1.2.2`

Attack: `important_instructions`

Prompt configuration: default

Seed: manifest declares `17`; the upstream API path did not expose a verified deterministic seed control.

Secret handling: the API key was used only as a process environment variable for the experiment run and was not written to report files.

## Artifacts

- `no_defense_normalized/`: v2 metric recalculation for existing legacy `deepseek-chat` no-defense summaries. These are audit/reference artifacts, not the V4-Flash paired baseline.
- `replay/`: Canonical AgentDojo-derived tool-boundary replay benchmark. This is not a standard AgentDojo end-to-end score.
- `paired_mini/raw/`: DeepSeekV4-Flash paired mini raw run summaries.
- `paired_mini/paired_summary.json`: paired E2E summary with integrity check.
- `paired_mini/paired_integrity.json`: case-set integrity result.
- `confirmation_modes/`: oracle_user_eval and gateway_eval subset runs for blocked/confirmation-heavy cases.
- `normalized/`: v2 normalized reports generated from the DeepSeekV4-Flash paired mini run.

## Scope Notes

Existing no-defense logs were found for `deepseek-chat`, not `deepseek-v4-flash`, so they were not used as the official V4-Flash paired baseline. A minimal no-defense rerun was included in paired mini.

The paired mini run completed with 47 paired cases per method. Slack injection task `0` was not present in the actual selected attack task set for this AgentDojo suite/version, so the realized Slack subset is 6 cases rather than the 9 entries implied by the numeric manifest.

Tool-boundary replay reports are separated from standard AgentDojo E2E metrics.

## Phase 1.2 Artifact Review

This repository currently uses summary-only review mode. The full raw ZIP is not publicly downloadable from this commit; public review should use the committed canonical replay summaries, replay cases, acceptance output, and manifest files in git.

Canonical replay paths:

- `experiments/agentdojo/reports/deepseekv4_flash/replay/agentdojo_derived_replay_results.json`
- `experiments/agentdojo/reports/deepseekv4_flash/replay/agentdojo_derived_replay_summary.json`

Pointer files:

- `artifact_manifest.json`
- `commit_hash.txt`
- `release_artifact_url_or_path.txt`

`release_artifact_url_or_path.txt` declares `artifact_distribution: summary_only`, `access_path_or_url: null`, and `public_full_zip_available: false`. If a GitHub Release ZIP is published later, update that pointer, `artifact_manifest.json`, and the SHA256 together.

The following root-level stale files are intentionally excluded and must not be used for Phase 1.1 metrics:

- `experiments/agentdojo/reports/deepseekv4_flash/agentdojo_derived_replay.jsonl`
- `experiments/agentdojo/reports/deepseekv4_flash/agentdojo_derived_replay_summary.json`
