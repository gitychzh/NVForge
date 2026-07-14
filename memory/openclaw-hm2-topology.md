---
name: openclaw-hm2-topology
description: "openclaw on HM2 — actual model chain, the opclaw4103 adapter, and the context-overflow/compaction deadlock root cause"
metadata: 
  node_type: memory
  type: project
  originSessionId: 13c6d667-ae5f-405b-8d9c-1a5b711d865c
---

openclaw on HM2 (this host) — actual topology, verified 2026-07-13. Differs from both CLAUDE.md and the workspace `MODEL_CONFIG.md` (both stale).

**Chain:** feishu/user → OpenClaw Gateway (node, port **18789**, systemd `openclaw-gateway.service`) → provider `opclaw4103` (baseUrl `http://127.0.0.1:4103/v1`, a `cc-adapter` docker container image `cc-adapter:latest`) → primary `nv_gw:40006` (glm5_2_nv) + fallback `ms_gw:40007` (glm5_2_ms). The 4103 adapter does primary→ms_gw fallback on nv_gw 502.

**Three sibling adapters** (all `cc-adapter`): `cc4101` (4101, CC's own chain — matches [[cc-chain-layout-hm2]]), `cx4102` (4102, opencode), `opclaw4103` (4103, openclaw).

**Config** (`~/.openclaw/openclaw.json` + `~/.openclaw/agents/main/agent/models.json`): primary `opclaw4103/glm5_2_nv`, `fallbacks: []` (adapter handles fallback instead), `contextWindow: 120000` (R1243 改, 原 48000; 见下文 R1243 update), `maxTokens: 32768`, `thinkingDefault: medium`, `compaction.model: opclaw4103/glm5_2_nv` (SAME as primary — anti-pattern), `compaction.timeoutSeconds: 120`, `compaction.reserveTokens: 8000`. `memorySearch.remote.baseUrl: http://127.0.0.1:4103/v1`, model `nvidia/nv-embed-v1`. Stale dead aliases in `agents.defaults.models`: `nv_gw/dsv4p_nv`, `nv_gw/glm5_2_nv` (no `nv_gw` provider exists — inert). Config frozen since R843C (Jul 11); rounds R844–R1118 were nv_gw-only.

**Root cause of context-overflow deadlock:** `contextWindow=48000` is artificially low (GLM5.2 natively ~128K). When a session hits ~48001 tokens, precheck rejects it AND compaction fails with `already_compacted_recently` because the SAME model can't summarize-down below its own limit → `livenessState=blocked`, `suggestedAction=reset_or_new`. One feishu session (cd298250, user ou_fef3a86c6b17eb55ce839ccf2f47e384) hit this repeatedly on Jul 13 (18:36, 18:42, 20:14). Fix direction: raise contextWindow toward ~120000, and/or set compaction.model to a different/larger model.

**R1243 update (2026-07-13):** contextWindow 已从 48000 改到 120000, compaction 死锁根因已消除 (48001<120000 不再顶上限). 备份 openclaw.json.bak.R1243. 见 commit 6ba9efb.

**Why:** non-obvious — the deadlock is a config interaction, not a transient failure, and will recur for any long feishu conversation.
**How to apply:** when investigating openclaw "blocked" sessions or compaction failures, check `contextWindow` vs `compactionTokens` in the `[context-overflow-diag]` log line first. Config edits need `systemctl --user restart openclaw-gateway`. Don't touch thinking strength / model selection / tool_calls (agent-owned per iron rule). Adapter source: `docker exec opclaw4103 cat /app/gateway/app.py`.
