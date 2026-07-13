# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Project name: NVForge** (R787 rename of `hermes_improve_self`). GitHub repo is now
> `gitychzh/NVForge`; the local clone directory is still `~/hm_ps/hermes_improve_self` (the
> directory name was not renamed — only the repo was). GitHub auto-redirects the old URL, so
> old clones keep working, but `git remote set-url` has been applied on both hosts.
>
> **This working base** (`/home/opc_uname/cc_ps/cc_repair_hm`) is scratch, not the code. The
> actual artifacts live in two places — see "Repository layout" below. This file documents the
> `nv_gw` optimization effort so any future instance can be productive without re-deriving it.
> Naming was fully disambiguated in R680; litellm was fully removed in R681.

## What this is

**NVForge** is dual-host, symmetric LLM-gateway infrastructure focused on tuning a single
link: `nv_gw` (port 40006, the NV gateway → NVCF pexec/integrate).

Three independent agents — **hermes**, **openclaw**, **opencode** — run on two hosts as equal
peers (none belongs to another, none belongs to CC). Each has its own model chain. CC is
**infrastructure side**: it builds/tunes the gateways the agents point at, but does not own
the agents or their model-selection logic.

The optimization target is the `nv_gw` link above. **CC itself also runs through `nv_gw`/`ms_gw`**
(via the `cc4101` adapter, see below) — since R827 CC is no longer on a separate legacy
chain. The `legacy_*` containers (40000–40005 + 4000) that previously served CC's own glm5.1
chain were **retired in R827**; ports 40000–40005 and 4000 are closed on both hosts. Do not
resurrect them. R569 cancelled the dual-machine alternating-optimization ritual; CC now edits
both machines directly (still data-backed, still verified, still committed).

**Containers (both machines symmetric; R827 retired the `legacy_*` set, R680 names kept for the rest):**

| Port | Container | Role |
|---|---|---|
| 40006 | `nv_gw` | NV gateway (optimization target) — NVCF pexec/integrate, per-key SOCKS5/直连 |
| 40007 | `ms_gw` | MS gateway (backup) — ModelScope, 2D key×variant rotation |
| 5432  | `logs_db` | postgres `hermes_logs` DB (nv_requests, ms_requests, nv_tier_attempts, cc_requests) |
| 4101  | `cc4101` | CC's own adapter — anthropic→openai, primary `nv_gw`/`glm5_2_nv`, fallback `ms_gw`/`glm5_2_ms` (R805) |
| 4102  | `cx4102` | opencode adapter (same `cc-adapter` image) |
| 4103  | `opclaw4103` | openclaw adapter — does primary→ms_gw fallback on nv_gw 502 |
| 4104  | `hm4104` | hermes adapter |
| 4105  | `oc4105` | opencode secondary adapter |

`nv_gw`/`ms_gw` are the shared upstreams for all four adapters. Each adapter (`cc-adapter`
image) converts anthropic-format requests to openai-format and points at `nv_gw` (primary) +
`ms_gw` (fallback). CC's own config (`~/.claude/settings.json`) sets
`ANTHROPIC_BASE_URL=http://127.0.0.1:4101` — i.e. CC runs the **same `glm5_2_nv`/`glm5_2_ms`**
chain as the agents, not a separate glm5.1 chain.

## Roles & hosts

- **HM1** (this host): `opc_uname` @ `100.109.153.83`, hostname `opcsname` — git user `opc_uname`
- **HM2** (remote):  `opc2_uname` @ `100.109.57.26`, hostname `opc2sname` — git user `opc2_uname`

SSH to the peer: `ssh -p 222 <user>@<ip>`.

Systemd units (per host):
- HM1: `hermes-gateway.service` (user), `openclaw-gateway.service` (user), `opencode-web.service` (system).
- HM2: `hermes-gateway.service` (user), `openclaw-gateway.service` (user), `opencode-webui.service` (system).

The alternating-optimization systemd timer (`hermes_alt_optimize.service` / `.timer`) was
removed in R569. Only an `@reboot` bootstrap remains.

## Repository layout

| Path | What |
|---|---|
| `/home/opc_uname/hm_ps/hermes_improve_self` | **the shared git repo** (remote `git@github.com:gitychzh/NVForge.git`, branch `main`; R787 rename — local directory name kept as-is). Round files (`rounds/R<N>_*.md`), scripts, deploy artifacts, `upstream_*.py`. All optimization work is recorded here. |
| `/opt/cc-infra` (on **both** hosts) | docker-compose stack running the 9 containers. `docker-compose.yml` is the live config; `proxy/nv-gw/gateway/` is the nv_gw source (`config.py`, `upstream.py`, `handlers.py`, `db.py`); `proxy/ms-gw/gateway/` is the ms_gw source; `logs/nv_gw/`, `logs/ms_gw/` have error JSONL. |
| `/home/opc_uname/cc_ps/cc_repair_hm` | this working base (CLAUDE.md + scratch). |

HM1 and HM2 each have their own clone of `hermes_improve_self` plus the live `/opt/cc-infra`
stack. **Always commit changes to the repo** so the peer can pull.

## The iron rule (铁律)

From `rule.md` / `README.md` — highest priority (R569 dropped rules 1 & 5; the rest stand):

1. **改前必有数据** — every change backed by logs/DB/metrics, no guessing.
2. **改后必有验证** — end-to-end verify after deploying.
3. **聚焦 nv_gw** — only the 40006 NV link. (CC's own chain `cc4101`→`nv_gw`/`ms_gw` is not the
   optimization target either, but it rides the same `nv_gw` — so `nv_gw` health directly
   affects CC itself. The retired `legacy_*` 40000–40005 chain is gone; don't treat it as a live
   fallback to preserve.)
4. Network problems → use your own mihomo proxy (`socks5://127.0.0.1:9090` on HM1; HM2 docker
   daemon is already behind mihomo 7880).
5. **所有修改写入仓库** — commit so the next round can `git pull` and continue.

Judging criteria: fewer errors, faster requests, lower latency, stability first.
Architecture-level changes are now authorized (R569 dropped the "one parameter per round"
rule); the data/verify/focus/commit rules remain.

## The nv_gw link (the thing being tuned)

```
agent → 127.0.0.1:40006 (container nv_gw) → NVCF pexec/integrate
   → per-key 直连 (HM1) or per-key SOCKS5 mihomo 7894–7899 (HM2) → NVIDIA API
```

- nv_gw is a self-built proxy (`/opt/cc-infra/proxy/nv-gw/`, Dockerfile `FROM python:3.12-slim`,
  ENTRYPOINT `gateway_main.py`). **No litellm dependency** anywhere (R681 removed it fully).
- Per-model NVCF `function_id`s + `strip_params` live in `gateway/config.py` (env-overridable):
  glm5.1/glm5.2 strip `thinking_budget` (NVCF 400s otherwise); deepseek/kimi pass all params.
- Active model tiers (env `HM_NV_MODEL_TIERS`, both hosts aligned R580/R654): `dsv4p_nv`
  (hermes primary), `glm5_2_nv` (openclaw primary), `kimi_nv` (opencode primary).
  Fallback to `ms_gw` `glm5_2_ms` (R580).
- 5 NV API keys (`HM_NV_KEY1..5`) shared across models, each routed through its own mihomo
  port (`HM_NV_PROXY_URL1..5`) on HM2 to avoid same-IP rate limits; HM1 is direct (Japan IP).
- Gateway auth: `NVU_GATEWAY_API_KEY` (default `nv-gw-token` in config.py, also set in compose
  env). Agents send `Authorization: Bearer nv-gw-token`. `/health` is exempt.
- Tunable knobs: `UPSTREAM_TIMEOUT`, `TIER_TIMEOUT_BUDGET_S`, `MIN_OUTBOUND_INTERVAL_S`,
  `KEY_COOLDOWN_S`, `TIER_COOLDOWN_S`, `HM_CONNECT_RESERVE_S`,
  `NVU_FORCE_STREAM_UPGRADE_TIMEOUT`, `NVU_FORCE_STREAM_EXCLUDE_MODELS`. Each has a long
  commit comment tracking its R-number history.

## Data sources for "改前必有数据"

The `logs_db` container hosts the `hermes_logs` DB on both hosts. Tables:
- `nv_requests` — nv_gw request-level (success/error, duration).
- `ms_requests` — ms_gw request-level.
- `nv_tier_attempts` — per-key tier errors (`NVCFPexecSSLEEOFError`, `NVCFPexecTimeout`,
  `all_tiers_exhausted`, …).

Round files typically report a 30-min window + 10-min burst window success rate and a
per-error breakdown before proposing a change.

Raw logs: `/opt/cc-infra/logs/nv_gw/hm_error_detail.YYYY-MM-DD.jsonl` (HM1 local; HM2 over SSH).

## Common commands

Run on the host where the artifact lives. HM1 = local; HM2 = over SSH.

```bash
# --- repo (HM1, local) ---
cd ~/hm_ps/hermes_improve_self
git pull --ff-only origin main
git log --oneline -5                     # see recent rounds
ls -1t rounds/R*_*.md | head             # newest round file

# --- nv_gw health / config ---
curl -s http://localhost:40006/health
docker exec nv_gw env | grep -E "TIER_TIMEOUT_BUDGET|UPSTREAM_TIMEOUT|MIN_OUTBOUND|KEY_COOLDOWN|NVU_FORCE_STREAM"
docker ps --filter name=nv_gw
# HM2:
ssh -p 222 opc2_uname@100.109.57.26 'curl -s http://localhost:40006/health'
ssh -p 222 opc2_uname@100.109.57.26 'docker exec nv_gw env | grep -E "TIER_TIMEOUT_BUDGET|UPSTREAM_TIMEOUT|MIN_OUTBOUND|KEY_COOLDOWN"'

# --- restart after a config.py / compose change (source-change needs build) ---
cd /opt/cc-infra && docker compose up -d nv_gw                          # env/compose change
cd /opt/cc-infra && docker compose build nv_gw && docker compose up -d nv_gw   # gateway/*.py change
# HM2:
ssh -p 222 opc2_uname@100.109.57.26 'cd /opt/cc-infra && docker compose up -d nv_gw'

# --- query metrics from hermes_logs ---
docker exec logs_db psql -U litellm -d hermes_logs -c "select count(*) from nv_requests;"
# HM2:
ssh -p 222 opc2_uname@100.109.57.26 'docker exec logs_db psql -U litellm -d hermes_logs -c "select count(*) from nv_requests;"'
```

## Deploying a change (workflow)

1. **Gather data** from `hermes_logs` DB / error JSONL for a 30-min window.
2. **Plan** the change; record the plan in a round file before executing.
3. **Edit** `/opt/cc-infra` (compose env) or `proxy/nv-gw/gateway/*.py`. For in-container
   patches, `docker exec nv_gw cp` a backup first (`*.py.bak.RNN`); for source edits, edit the
   bind-mounted `gateway/` dir and restart (no rebuild needed for bind-mount; rebuild only if
   Dockerfile/requirements change).
4. **Verify**: `curl /health`, `docker ps`, error log over the next window.
5. **Write** `rounds/R<N>_<summary>.md` (summary, param table, data, expected effect,
   verification checklist).
6. **Commit + push** to `origin/main`.

## Agent config (independent APPs — edit with care)

The three agents' configs are agent-owned namespaces. CC only touches the gateway-side fields
needed to keep them pointing at the right local gateway:

- hermes: `~/.hermes/config.yaml` — `provider: nv_gw`, `providers.nv_gw.api_key: nv-gw-token`,
  fallback `ms_gw` + `ms-gw-token`; `model.default: dsv4p_nv`.
- openclaw: `~/.openclaw/openclaw.json` — `primary: nv_gw/glm5_2_nv`, `fallbacks: [ms_gw/glm5_2_ms]`,
  provider apiKey `nv-gw-token`/`ms-gw-token`; HM2 also has `memorySearch` pointing at nv_gw
  `/v1/embeddings`.
- opencode: `~/.config/opencode/opencode.jsonc` — `model: nv_gw/kimi_nv`, provider block
  baseURL `http://127.0.0.1:40006/v1`.

Do **not** change model selection, thinking strength, or tool_calls logic — those are the
agents' own behavior. (openclaw/opencode thinking is selectable; hermes' NV/MS chain is
hardcoded medium by `chat_completions.py:426` — not CC's to change.)

CC's own config (`~/.claude/settings.json`) points `ANTHROPIC_BASE_URL` at
`http://127.0.0.1:4101` (`cc4101`, token `cc4101-token`, frontend model `cc-glm5-2`) — the
**same** `nv_gw`/`ms_gw` chain as the agents, via the `cc4101` adapter. R827 retired the old
legacy 40001 glm5.1 chain; the three `settings.json.bak.*` that still pointed at 40001 were
removed in R1245.

## Gotchas

- `docker-compose.yml` on each host has many `.bak.R*` siblings — never edit a backup; edit
  the live `docker-compose.yml` and let the next round add the next backup.
- nv_gw image is rebuilt from `/opt/cc-infra/proxy/nv-gw`; `gateway/*.py` changes need
  `docker compose build nv_gw && docker compose up -d nv_gw` only if not bind-mounted.
  Current setup bind-mounts `gateway/`, so most edits just need `docker compose up -d nv_gw`
  (or `docker restart nv_gw`).
- `~/hm_ps/hermes_improve_self/upstream_current.py` is a snapshot of the live nv_gw
  `upstream.py` for cross-round diffing (live source is in `/opt/cc-infra/proxy/nv-gw/gateway/`).
- Hidden contracts (R680 cc2 red-team found these): `db.py` default `NVU_DB_HOST`,
  `config.py` default `NVU_GATEWAY_API_KEY`, `NO_PROXY` whitelist in compose must list all
  service names, `X-MS-Proxy` header value. When renaming, update all of them together.
- HM2 docker daemon is behind mihomo (7880) for docker.io access; HM1 uses a registry-mirror.
  If a base image pull hangs, check the daemon proxy first.
- A `config.yaml.corrupt.*.bak` next to an agent config means a prior write was recovered —
  diff before trusting the current file.
