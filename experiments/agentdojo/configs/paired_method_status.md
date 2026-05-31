# Paired Method Status

Default `paired_mini_manifest.json` only enables methods with distinct runner
implementations:

- `no_defense` -> `none`
- `agentdojo_tool_filter` -> `tool_filter`
- `reposhield_tool_firewall` -> `agentdojo_firewall`

Deferred methods:

- `gateway_only`: historical baseline; not enabled in paired mini until the
  runner implements a distinct `reposhield_gateway_only` defense.
- `reposhield_full`: reserved for future full-stack RepoShield; not enabled
  until `agentdojo_firewall_full` has a separate code path.
- `simple_denylist`: reserved until implemented as a separate runner path.
