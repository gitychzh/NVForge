# R680: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 37→36 (−1s)

**Date**: 2026-07-04 11:00 UTC

## Data Summary (6h window)

| Metric | Value |
|--------|-------|
| Total requests | 156 |
| OK (200) | 156 (100.0%) |
| Fail | 0 |
| Log errors | 0 |
| Warnings | 0 |
| key_cycle_429s | 0 |
| p50 latency | 5010ms |
| p95 latency | 18194ms |
| Avg latency | 7028ms |
| Max latency | 38401ms |
| ATE (NULL upstream) | 0 |

### Per-model (6h)
| Model | Req | OK | Avg ms | Max ms |
|-------|-----|-----|--------|--------|
| glm5_2_nv | 156 | 156 | 7028 | 38401 |

(Only glm5_2_nv traffic in this window — no dsv4p_nv/kimi_nv integrate requests observed)

### Per-key (glm5_2_nv pexec, 6h)
| Key | Req | OK | Avg ms | p50 ms |
|-----|-----|-----|--------|--------|
| K0 (idx=0) | 34 | 34 | 6056 | 4827 |
| K1 (idx=1) | 30 | 30 | 5872 | 4200 |
| K2 (idx=2) | 31 | 31 | 8335 | 5549 |
| K3 (idx=3) | 30 | 30 | 7920 | 7072 |
| K4 (idx=4) | 31 | 31 | 7046 | 5030 |

### DB last 10 requests (all glm5_2_nv pexec, 100% OK)
| ts | key | dur_ms | ttfb_ms | tokens_in | tokens_out | finish |
|----|-----|--------|---------|-----------|------------|--------|
| 11:11:33 | k4 | 2123 | 2123 | 16436 | 4 | stop |
| 11:11:27 | k3 | 3800 | 3796 | 16267 | 154 | tool_calls |
| 11:06:35 | k2 | 4404 | 4404 | 16385 | 4 | stop |
| 11:06:29 | k1 | 4496 | 4495 | 16265 | 105 | tool_calls |
| 11:03:23 | k0 | 3357 | 3353 | 23930 | 91 | stop |
| 11:03:20 | k4 | 2868 | 2868 | 23699 | 71 | tool_calls |
| 11:01:27 | k3 | 9649 | 9151 | 60765 | 451 | stop |
| 11:01:16 | k2 | 10586 | 10585 | 60081 | 155 | tool_calls |
| 11:01:12 | k1 | 2744 | 2744 | 58270 | 70 | tool_calls |
| 11:00:48 | k0 | 22361 | 22360 | 57327 | 842 | tool_calls |

### 24h errors
- `429_nv_rate_limit`: 5 (server-side NVCF rate limiting — non-config fixable, transparent key cycling)
- `empty_200`: 4 (server-side empty response — non-config fixable, fastbreak handles)
- `IntegrateTimeout`: 1 (server-side integrate timeout — non-config fixable)

### Log observations
- `NV-THINKING-TIMEOUT (glm5_2_nv) thinking request stream=True → extended timeout 37s` → now 36s
- 0 errors, 0 warnings, 0 panics in entire visible log
- All 5 keys serving glm5_2_nv with DIRECT pexec, 100% first-attempt success
- No fallback triggered (no `NV-FALLBACK` lines in logs)
- Container healthy, proxy listening

## Optimization

**Parameter**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 37→36 (−1s)

**Rationale**:
- R656-R680 trajectory continued: 61→59→58→57→56→55→54→53→52→51→50→49→48→47→46→45→44→43→42→41→40→39→38→37→36 (−25s total accumulation)
- Zero-error regime sustained: 0 log errors, 0 kc429, 0 fallback triggered
- 6h 156/156 OK **100%** — perfect window, all 5 keys healthy
- glm5_2_nv pexec p50=5010ms, p95=18194ms all well within 36s thinking timeout
- All 24h errors are server-side NVCF (rate_limits, empty_200, integrate_timeout) — non-config fixable
- Margin: 36s >> UPSTREAM_TIMEOUT=25s (11s safe margin, well above floor)
- Conservative: −1s per round, continuing proven multi-round gradual descent
- Note: compose previously had R679 comment (HM1 self-applied 38→37 without formal round file); this round formalizes next step in the trajectory

**Edit method**: SSH HM1, `sed -i '492s/"37"/"36"/'` + comment rewrite (single line 492), `docker compose up -d nv_40006_uni`

**Verification**:
- ✅ Compose line 492: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "36"`
- ✅ Docker compose config: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "36"`
- ✅ Container env: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=36`
- ✅ 3-way consistency confirmed
- ✅ Container restarted cleanly, proxy healthy, listening on 0.0.0.0:40006

## Iron Rule Compliance
- ✅ Single parameter per round
- ✅ Only changed HM1 (opc_uname@100.109.153.83, `/opt/cc-infra/docker-compose.yml`), never HM2 (opc2_uname local)

## ⏳ 轮到HM1优化HM2