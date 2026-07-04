# R681: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 36→35 (−1s)

**Date**: 2026-07-04 11:33 UTC

## Data Summary (6h window)

### DB Summary
- Total: 216, OK: 212, Fail: 4, Success: 98.1%
- Avg: 13753ms, p50: 4802ms, p95: 36863ms, Max: 494127ms

### Per-Model (6h)
- glm5_2_nv: 202 req, 199 OK (98.5%), avg=6764ms, max=65265ms
- dsv4p_nv: 10 req, 9 OK (90%), avg=154931ms, max=494127ms
- kimi_nv: 4 req, 4 OK (100%), avg=13763ms, max=29294ms

### Error Breakdown (6h + 24h)
- 6h: 4 `all_tiers_exhausted` — server-side, non-config-fixable
- 24h: 4 `all_tiers_exhausted` — zero in recent hours
- Zero log errors, zero kc429, zero fallback

### PEXEC vs INTEGRATE TTFB (6h)
- pexec: 203 req, 200 OK, avg TTFB=6114ms, p50 TTFB=4559ms, p95 TTFB=14652ms, avg dur=6339ms
- integrate: 13 req, 12 OK, avg TTFB=70092ms, p50 TTFB=80025ms, p95 TTFB=98414ms, avg dur=129529ms

### Per-Key Per-Model (glm5_2_nv, dominant workload)
- K0: 42/42 OK, p50=4231ms
- K1: 38/38 OK, p50=3901ms
- K2: 40/40 OK, p50=4402ms
- K3: 39/39 OK, p50=6462ms
- K4: 40/40 OK, p50=4682ms
- All 5 keys 100% OK

### Hourly Trend
```
22:00: 4/4 OK avg=3780ms
23:00: 12/9 OK avg=9610ms (3 ATE)
00:00: 4/4 OK avg=4056ms
01:00: 4/4 OK avg=18776ms (1 ATE)
02:00: 19/18 OK avg=84179ms (dsv4p dominate)
03:00: 4/4 OK avg=2949ms
04:00: 4/4 OK avg=2840ms
05:00: 3/3 OK avg=2566ms
06:00: 2/2 OK avg=2222ms
07:00: 2/2 OK avg=2458ms
08:00: 3/3 OK avg=2615ms
09:00: 35/35 OK avg=4728ms
10:00: 98/98 OK avg=8140ms
11:00: 22/22 OK avg=6280ms ← 10:00-11:30 all clean
```

### Last 10 Requests (all fresh)
```
11:33:20 glm5_2_nv K3 200 2734ms
11:31:34 glm5_2_nv K2 200 2940ms
11:31:27 glm5_2_nv K1 200 4914ms
11:26:35 glm5_2_nv K0 200 2733ms
11:26:27 glm5_2_nv K4 200 6002ms
11:21:32 glm5_2_nv K3 200 2717ms
11:21:27 glm5_2_nv K2 200 2560ms
11:16:32 glm5_2_nv K1 200 2108ms
11:16:27 glm5_2_nv K0 200 2577ms
11:11:33 glm5_2_nv K4 200 2123ms
```
All 10 recent = 200 OK, no errors, no fallback

### Container Logs (errors/warns)
Zero errors. Only normal operational messages:
- NV-INJECT-THINKING / NV-THINKING-TIMEOUT (routine, glm5_2_nv thinking injection)
- NV-RR restored counter = normal startup artifact

## Optimization Decision

**Parameter**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 36→35 (−1s)

**Rationale**: R656-R681 trajectory continued. The system is in a strong zero-error regime: 6h 216req/212OK 98.1%, 4 ATE are server-side non-config-fixable. pexec p95 TTFB=14652ms << UPSTREAM_TIMEOUT=25s, margin ~10s. Deeper force-stream can shave additional latency for thinking-aware streaming requests without risking timeout failures. The trajectory from 61→35 has accumulated −26s total reduction with sustained zero-error stability. Single param — continue until signal of tension appears.

**Trajectory**: 61→59→58→57→56→55→54→53→52→51→50→49→48→47→46→45→44→43→42→41→40→39→38→37→36→35 (−26s total)

## Execution

### Method: sed (R672 pattern, line-anchored)
```bash
# Verify line 492
grep -n 'NVU_FORCE_STREAM_UPGRADE_TIMEOUT' /opt/cc-infra/docker-compose.yml

# Value change
sed -i '492s/"36"/"35"/' /opt/cc-infra/docker-compose.yml

# Comment rewrite (full line)
sed -i '492s|.*|<new line with R681 comment>|' /opt/cc-infra/docker-compose.yml

# Restart
cd /opt/cc-infra && docker compose up -d nv_40006_uni
```

### 3-Way Consistency Verified
- ✅ Compose line 492: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "35"`
- ✅ Docker compose config: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "35"`
- ✅ Container env: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=35`
- ✅ Container restarted cleanly: `nv_40006_uni Recreated → Started`

## Iron Rule Compliance
- ✅ Single parameter per round
- ✅ Only changed HM1 (opc_uname@100.109.153.83, `/opt/cc-infra/docker-compose.yml`), never HM2 (opc2_uname local)

## ⏳ 轮到HM1优化HM2