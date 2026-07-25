# R2354: HM2→HM1 Optimization Round

**Role**: HM2 execution (optimize HM1)  
**Timestamp**: 2026-07-25 19:26 UTC  
**Commit**: R2354 (HM2→HM1): NOP. cron false trigger, R2353 still deploying data, only 1h post-restart for kimi_nv. Single param, no delta.  
**Agent**: HM2 (opc2_uname)

---

## 1. HM1 State Collection (nv_gw / 40006)

### 1.1 Container Runtime
- `nv_gw`: Up 53 min at R2353 baseline (10:25 UTC restart), healthy
- `logs_db`: postgres:16-alpine, up 8 days, healthy
- Host: opcsname, uptime 8 days 18h, load 0.31  
- Container renamed from `hm40006` → `nv_gw` (confirmed by `docker ps` on HM1)

### 1.2 docker exec nv_gw env — all budget params
```
NVU_EMPTY_200_FASTBREAK=3                  # R2351
NVU_TIER_BUDGET_KIMI_NV=220                # ← R2353 set
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_FAIL_N=2
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
NVU_BIG_INPUT_THRESHOLD=250000
KEY_COOLDOWN_S=30
TIER_COOLDOWN_S=30
NVU_STREAM_FIRST_BYTE_DEADLINE_S=15
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_DB_ENABLED=1
```

### 1.3 DB Data — post-R2353 (10:25 UTC)

#### 3-hour window (since deploy, ~53 min active at check)
| model       | total | 200 OK | failed | SR%    | avg_ok_dur |
|-------------|-------|--------|--------|--------|------------|
| kimi_nv     | 6     | 6      | 0      | 100.0% | 88.9 s     |
| glm5_2_nv   | 4     | 4      | 0      | 100.0% | 9.1 s      |
| dsv4p_nv    | 0     | 0      | 0      | —      | —          |

#### 6-hour window (mix of 210→220)
| model       | total | 200 OK | failed | SR%    |
|-------------|-------|--------|--------|--------|
| kimi_nv     | 50    | 37     | 13     | 74.0%  |
| glm5_2_nv   | 29    | 16     | 13     | 55.2%  |
| dsv4p_nv    | 12    | 0      | 12     | 0.0%   |

#### 24-hour window
| model       | total | 200 OK | failed | SR%    | avg_ok_dur |
|-------------|-------|--------|--------|--------|------------|
| kimi_nv     | 139   | 101    | 38     | 72.7%  | 58.1 s    |
| glm5_2_nv   | 121   | 54     | 67     | 44.6%  | 17.6 s    |
| dsv4p_nv    | 53    | 14     | 39     | 26.4%  | 47.0 s    |

#### ATE bucket analysis (6h failed; includes pre-220)
| model       | dur bucket | count |
|-------------|------------|-------|
| dsv4p_nv    | <5s        | 12    |
| glm5_2_nv   | <5s        | 8     |
| glm5_2_nv   | 5-60s      | 3     |
| glm5_2_nv   | 51s        | 2     |
| kimi_nv     | 61-120s    | 1     |
| kimi_nv     | 140-200s   | 7     |
| kimi_nv     | 210s       | 1     |

#### tier_attempt error types (6h)
| tier       | error_type                 | count |
|------------|-----------------------------|-------|
| glm5_2_nv  | NVCFPexecRemoteDisconnected | 1     |
| glm5_2_nv  | NVCFPexecTimeout            | 1     |
| kimi_nv    | empty_200                   | 20    |
| kimi_nv    | NVCFPexecRemoteDisconnected | 7     |
| kimi_nv    | NVCFPexecSSLEOFError        | 2     |

Post-220 tier_attempts (10:25+): empty_200=5, RemoteDisconnected=1.

### 1.4 NVCF gateway log summary (last 100 lines, recent errors)
- **Broken pipe** (9x): downstream client disconnects after partial write, harmless
- **THINKING-TIMEOUT** (5x): expected for kimi_nv reasoning models, 66s extension in effect
- **EMPTY-200** (5x): kimi_nv key-specific transient, FASTBREAK=3 triggers 2-key trial → success
- **CONN error** (1x): Remote end closed connection without response, not config-fixable
- Zero new error patterns. All known NVCF-side behavior.

---

## 2. Data Analysis: 介入四条 (Intervention Criteria)

### 2.1 有可修故障 ❌
- 所有 error 类型均为已知 NVCF-side 行为: `empty_200` (key-specific transient), `RemoteDisconnected` (NVCF host-level), `BrokenPipe` (downstream-only — harmless)
- `zombie_empty_completion` (1x, 6h) at 9s duration → caught by breaker, no action needed
- No new error pattern, no config-fixable fault.

### 2.2 有真实 ATE ❌
- **kimi_nv post-220**: 6/6 = 100% SR, zero ATE in deployment window
- **6h ATEs**: almost all pre-220 (budget=210), 210s ATE in DB at 09:29 (pre-220) and one at 210s on transition edge
- No post-deploy ATE trend

### 2.3 参数未到底 ❌
- Candidates and their risk/benefit:
  | Parameter | Current | Proposed Delta | Risk | Post-220 Evidence |
  |-----------|---------|---------------|------|-------------------|
  | KIMI_NV   | 220     | 230           | low  | 100% SR post-deploy |
  | GLM5_2_NV | 210     | 220           | med  | ATEs <5s (breaker), not budget ceiling |
  | DSV4P_NV  | 180     | —             | high | 0% SR variant, not priority |
  | FASTBREAK | 3       | 4             | med  | 20 empty_200 in 6h → only 2 rescue per 3-cycle; 4th would probe k4 |

- **All candidates risky**: no data shows the ceiling is still being hit. KIMI_NV post-220 at 100% SR with no ATE.

### 2.4 有可优化参数 ✅ / ❌
- Floating: KIMI_NV→230 (low risk), GLM5_2_NV→220 (med risk), FASTBREAK=3→4 (risky to increase key cycles without post-220 evidence of new failure pattern)
- GLM5_2_NV ATEs (<5s, 8 count) are **instant breaker**, not budget ceiling. GLM budget already medical-grade. Budget increase won't fix instant-fail pattern.

**Intervention conclusion**: TRUE FALSE FALSE FALSE — no single parameter change is justified. R2354 NOP.

---

## 3. Execution Process

**None** — per iron-law, HM1 config is frozen this round.  
No docker-compose.yml edit. No container restart. No commit to /opt/cc-infra.

Premature R2354 confirmed: script detected "我提交的" post-R2353 commit as HM1-trigger, thus auto-scheduled HM2. This round is **verification+cot record only**.

---

## 4. Change List

| File | Change | Note |
|----------------------------|-----------|------|
| `/opt/cc-infra/docker-compose.yml` | None | NOP round — no HM1 edit |

---

## 5. 变更数量统计

| **Zero parameter changes this round** | 0  |
| **Parameters modified in last round (R2353)** | 1 (`NVU_TIER_BUDGET_KIMI_NV` 210→220) |
| **R2353 kimi_nv post-deploy SR (N=6)** | 100.0%  |

---

## ⏳ 轮到HM1优化HM2
