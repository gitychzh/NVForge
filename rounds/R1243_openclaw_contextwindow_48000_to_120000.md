# R1243: openclaw (HM2) contextWindow 48000→120000 — break context-overflow/compaction deadlock

> Boundary round: this is an **openclaw-config** change, not an nv_gw param change.
> Authorized directly by user (openclaw health deep-dive). Iron rule "聚焦 nv_gw" =
> optimization target; this fix keeps the agent alive and does NOT touch model
> selection / thinking strength / tool_calls (agent-owned per iron rule).

## Summary

openclaw on HM2 hit a recurring **context-overflow / compaction deadlock**: one feishu
session (`cd298250`, user `ou_fef3a86c6b17eb55ce839ccf2f47e384`) grew to ~48001 tokens,
hit the artificially-low `contextWindow=48000`, the precheck rejected it, and auto-compaction
failed with `already_compacted_recently` (the SAME model can't summarize-down below its own
limit) → `livenessState=blocked`, `suggestedAction=reset_or_new`. This is a config-interaction
defect, not a transient failure — it recurs for any long feishu conversation that approaches
48K tokens.

Fix: raise `contextWindow` 48000 → **120000** (under GLM 5.2's native ~128K, leaves headroom
for output). The stuck session's 48001 tokens are now well under the new limit, so the next
precheck passes and the session recovers **without losing history** (A3 reset was unnecessary).

## Param change

| Param | Location | Before | After |
|---|---|---|---|
| `contextWindow` | `~/.openclaw/openclaw.json:106` (`models.providers.opclaw4103.models[0]`) | 48000 | 120000 |
| `contextWindow` | `~/.openclaw/agents/main/agent/models.json:16` | 48000 | 120000 (auto-synced by hot-reload) |

Applied via **config hot-reload** (openclaw watches `openclaw.json`): no service restart needed.
openclaw auto-synced the agent-level `models.json` to match.

## Data (改前必有数据)

6h window on HM2 (nv_gw + openclaw journal):
- nv_gw SR: **261 OK / 36 fail = 88.5%** (35 `all_tiers_failed_in_mapped_tier` @ 94s avg, 1 `NVStream_IncompleteRead`).
- openclaw journal outcome: 23 completed / 6 failed / 1 error (~76.7%) — the gap above nv_gw's 88.5% is the context-overflow deadlocks + timeouts.
- context-overflow events 24h: **3** (Jul 13 18:36, 18:42, 20:14), ALL the same session `cd298250`.
- compaction failures 24h: **6**, all `reason=already_compacted_recently`.
- key diag line:
  ```
  [context-overflow-diag] sessionKey=agent:main:feishu:direct:ou_fef3a86c...
    provider=opclaw4103/glm5_2_nv messages=39 compactionTokens=48001
    error=Context overflow: prompt too large for the model (precheck).
  [compaction-diag] outcome=failed reason=already_compacted_recently
  → livenessState=blocked suggestedAction=reset_or_new
  ```
  `compactionTokens=48001` vs `contextWindow=48000` = the 1-token-over deadlock.

## Expected effect

- Long feishu sessions no longer deadlock at ~48K; ceiling moves to 120K.
- The stuck `cd298250` session recovers on next message (48001 < 120000).
- Tradeoff: sessions approaching 120K input may hit slower NVCF responses (recoverable via
  4103 adapter → ms_gw fallback). Strictly better than a permanent deadlock. The `contextWindow`
  raise also gives compaction 2.5× more room to operate, mitigating the same-model
  compaction anti-pattern (`compaction.model == primary`) for now.

## Verification (改后必有验证)

- [x] Hot-reload applied clean: `[reload] config hot reload applied (models.providers.opclaw4103.models)`.
- [x] Both files now `contextWindow: 120000`; backups retain `48000`.
- [x] `systemctl --user is-active openclaw-gateway.service` = active; control UI reachable.
- [x] Zero reload errors; **0 new `context_overflow`** since reload.
- [x] No persisted blocked-flag in agent sqlite (`openclaw-agent.sqlite` has only memory/auth/cache
      tables — no session-liveness table). `livenessState=blocked` is re-evaluated per request,
      so the session recovers on next feishu interaction.
- [ ] (passive, pending) confirm on next feishu interaction that `cd298250` no longer blocks.

## Backups

- `~/.openclaw/openclaw.json.bak.R1243-pre-contextwindow` (48000)
- `~/.openclaw/agents/main/agent/models.json.bak.R1243-pre-contextwindow` (48000)

## What was NOT done (deferred to later rounds)

- **A3 reset cd298250 history**: unnecessary — A1 raises the ceiling above the session's
  current size, so it recovers without losing the user's conversation history. (Reset kept
  as last-resort only if a future session still blocks above 120K.)
- **P1** (4103 adapter 502→ms_gw fallback aggressiveness — `fallback_actually_attempted=t`
  was only 2/36 in 6h): separate round on `proxy/cc-adapter/app.py`.
- **P2** (stale `nv_gw/*` dead aliases in `agents.defaults.models`; rewrite `MODEL_CONFIG.md`
  to match actual opclaw4103 topology): separate cleanup round.
- **compaction.model** still == primary (`opclaw4103/glm5_2_nv`). The contextWindow raise
  mitigates it for now; a dedicated larger-window compaction model is a future round.

## Iron rule compliance

1. 改前必有数据 ✅ (6h SR + diag lines above)
2. 改后必有验证 ✅ (hot-reload clean, both files 120000, 0 new overflow)
3. 聚焦 nv_gw — boundary (openclaw-config, authorized); nv_gw link untouched ✅
4. Network — n/a ✅
5. 所有修改写入仓库 ✅ (this file + backups)

## Concurrent upstream note (from R1242 peer commit, NOT fixed by this round)

At time of writing, peer round R1242 reports the NV link is degraded:
- `NVCF glm5_2 function DEGRADED` (3× `404-Inference-error` on NVCF ai-glm-5_2 3b9748d8 —
  the very model openclaw's `glm5_2_nv` maps to).
- `ms_gw 0/21 OK (TimeoutError 190s)` — the fallback path is also failing.
- R1242 6h nv_gw SR ≈ 77.5% (138 req / 107 OK / 31 fail): 16 `zombie_empty` (NVCF
  content-filter, not config-fixable) + 14 ATE.

So openclaw is currently starving on BOTH primary (NVCF GLM5.2 404) and fallback
(ms_gw timeout). This round (R1243) does **not** address that upstream degradation —
it only removes the openclaw-side context-overflow deadlock so that, once the NV link
recovers, long feishu sessions won't hard-block at 48K. The upstream degradation is the
nv_gw optimization target handled by the HM2→HM1 round series (R1242 et al.).
