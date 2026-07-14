---
name: cc-chain-layout-hm2
description: "Actual CC model chain on HM2 is cc4101→nv_gw/ms_gw (glm5_2_nv), NOT the legacy_*/40001/glm5.1 that CLAUDE.md describes"
metadata: 
  node_type: memory
  type: project
  originSessionId: 907f2f1a-6e16-485a-bd13-90e3997edabb
---

On HM2 (`opc2sname`), CC's own model chain is NOT the `legacy_*` (40000–40005 + port 4000) containers
described in `CLAUDE.md` — those are gone. Verified live 2026-07-09:

`~/.claude/settings.json` → `ANTHROPIC_BASE_URL=http://127.0.0.1:4101`, key `cc4101-token`, model `cc-glm5-2`.
→ container `cc4101` (port 4101, `PROXY_ROLE=cc4101`, anthropic→openai converter, source `/opt/cc-infra/proxy/cc4101/gateway/`).
  - primary: `nv_gw:40006` model `glm5_2_nv` (token `nv-gw-token`)
  - fallback: `ms_gw:40007` model `glm5_2_ms` (token `ms-gw-token`)
  - Knobs: `UPSTREAM_TIMEOUT=120` (R806), `PRIMARY_HEADER_TIMEOUT=25` (R828: 8->25; R825 的 8s 紧急止血值已在 R828 调回, 覆盖 p90 留余量, 超时切 fallback).
  - `MODEL_MAP` (config.py) maps ALL incoming model names — `cc-glm5-2`, `claude-opus-4-8`,
    `claude-sonnet-*`, `claude-haiku-*`, etc. — to `glm5_2_nv`. **CC actually runs NV glm5.2, NOT
    glm5.1 and NOT Claude**, regardless of what model name CC sends.

Sibling containers in the rebuilt (non-`legacy`) chain: `cx4102`(4102), `opclaw4103`(4103),
`hm4104`(4104), `oc4105`(4105); shared gateways `nv_gw`(40006), `ms_gw`(40007), `logs_db`(5432).
CC requests log to the `cc_requests` table in `hermes_logs` DB (columns: ts, request_model,
mapped_model, upstream_used, fallback_triggered, status, duration_ms, ttfb_ms, error_type;
host_machine='opc2sname' = HM2).

**Why:** CLAUDE.md's containers table and "CC runs glm5.1 on 40001" line are stale; trusting them
wastes a full re-investigation (confirmed this session). The only reliable current source is the
live `/opt/cc-infra` + `cc_requests` DB, since `/opt/cc-infra` is a live artifact, not in git.

**How to apply:** For CC-chain questions on HM2, inspect `cc4101` + query `cc_requests`, not
`legacy_*`. Expect CLAUDE.md's `legacy_*`/40001/glm5.1 references to be wrong until it's updated.
Always re-verify `settings.json` + `docker ps` + `cc4101 /health` before relying on specifics —
this layout drifts across rounds (R805–R826 reshaped it). If CLAUDE.md gets updated to match, this
memory is obsolete and should be deleted.


**R1245 update (2026-07-13):** timeout 值已校准为 live 实测 (PRIMARY_HEADER_TIMEOUT=25). primary 仍 DEGRADED (nv_gw glm5_2_nv 60s 卡死), 熔断器正确 OPEN, fallback ms_gw glm5_2_ms 撑着. 见 [[cc-config-audit-r1245]].
