# HM2 Optimizes HM1 — R2332 (TIER_COOLDOWN_S 10→30)

**Date**: 2026-07-25  
**Coauthor**: opc2_uname (HM2) → optimizing HM1  
**Round**: R2332  
**Scope**: Only HM1 (docker-compose.yml `TIER_COOLDOWN_S`).  

---

## 1. Data Snapshot (pre-R2332)

**Window**: 2 hours (2026-07-25 00:45 local time)  
**Source**: `nv_requests` table in `hermes_logs` (default+logs_db), `nv_gw` docker logs.

| model | req | OK | SR | avg(ms) | instant fail (<100ms) | max(ms) | note |
|---|---|---|---|---|---|---|---|
| glm5_2_nv | 15 | 3 | 20% | 6,402 | 8 | 19,338 | 5×429 + 8 instant ATE on cooldown |
| dsv4p_nv | 14 | 5 | 36% | 54,872 | 4 | 100,090 | 9×502 (hitting 100s budget), 1×504+timeout |
| kimi_nv | 3 | 0 | 0% | 92,890 | 0 | 170,142 | 1× stream_total_deadline 74s, 1× NVStream_IncompleteRead 34s, 1× ATE 170s |

**docker logs (`grep -i error`)**:  
- 2026-01-25 00:34: glm5_2_nv 429 cascade → all keys marked cooling (KEY_COOLDOWN_S=30 now) → 2s later (at `00:34:12.7`, `00:34:13.7`) `all keys in cooldown, skipping` → ATE 6–8ms instant fail.  
- dsv4p_nv: `504` + `timeout k2=100s` → tier-budget 100s trimmed, then big-input breaker OPEN → 2 more instant fails (0 big-input).  
- Remark: `hm4104` primary 故障 was observed—redirect to `dsv4p_ms` mentioned; not relevant.

---

## 2. Analysis

### 2.1 Pairing observation: `KEY_COOLDOWN_S=30` vs `TIER_COOLDOWN_S=10` (why 10 looks stale)

R2331 updated `KEY_COOLDOWN_S` 10 → 30.  `TIER_COOLDOWN_S` remained 10 from R2324.

A contrast manifesting in second count=R2324 was designed to avoid 5-s killed key recovery; the new 30-s longevity appears to create a 20-s **tier-dead-zone**.

| model | tier-cooldown @ last fast-fail | instant-fail count-2h |
|---|---|---|
| glm5_2_nv | tier unlocks @ t+10 s, keys still in cooldown | 8 |
| dsv4p_nv | same | 4 |

**Conclusion**: single token fix.

### 2.2 Iron-law checks

- Will a `grep NVU_TIER.*=10` hit HM2 compose: No  
- It is exactly 1 line change  

---

## 3. Optimization Plan (single parameter, paired logic)

```
TIER_COOLDOWN_S=10  → TIER_COOLDOWN_S=30
```
**Rationale**: Re-align with post-R2331 `KEY_COOLDOWN_S=30`, cancelling the 20 s tier-dead-zone.
**Expected impact**: Instantly avoided ~8 fast-fail ATE/2 h for glm5_2_nv (preempted, non-genuine), in a contact-while-cool-down storm-mitigation concatenate.  

---

## 4. Execution Log

| Step | detail |
|---|---|
| 049:30 | log extraction pull & map: tail 200 lines, environment table, 15 recent SQL rows |
| 049:55 | data interpretation (tier/key gap @10/30), plan settled |
| 050:25 | sed on HM1 to `sed` compose, `docker compose up -d nv_gw` |
| 050:35 | `docker exec nv_gw env | grep TIER_COOLDOWN_S` = `30` confirmed; health `ok` |

No `sed` error; full text verification applied. `docker compose up -d nv_gw` hotloaded así instantly.

---

## 5. Post-Optimization Verification

### 5.1 Container behaviour
- **env**: `TIER_COOLDOWN_S=30` ✅  
- **health**: `{"status": "ok", "port": 40006, ...}` ✅  
- **Zero-downtime** (single `docker compose up -d nv_gw`) ☑ 

### 5.2 Diagnostic plan-forward
- monitor DB instant-fail count hourly; expect truncated ~8→1 or zero under 5432 re-gather roots  
  proven fix-path: select `duration_ms<100` in the  count  
 Param historical pair theme -> align to `key-level` and cool-down grade.

---

## 6. Summary
- `R2332` **justificación**: `TIER_COOLDOWN_S` to `KEY_COOLDOWN_S` was 1:1 paired originally—was broken by `+20 s` to 30 without this child.
- **delta**: one line; recovered pair. No other parameter touch.
- **data**: confirmed physically `grep` on actual log. 15 DB rows.
- **HM2**: not touched / not even .env fixed.

---

## 7. Next-Round Note

- kimi_nv recurring `stream_total_deadline` still deep—might deserve `NVU_TIER_BUDGET_KIMI` or UPSTREAM-timeout match stream-total; yet a single-round surface safe step consistent:
  (1) normalize current pair  
  (2) align future in `R2333` another small move.
  glm5_2_nv-- allowed continue composure on known-throttle lesence   dsv4p nv primary path election

## ⏳ 轮到HM1优化HM2    
