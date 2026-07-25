# R2357: HM2→HM1 Optimisation Round

**Role**: HM2 execution (optimize HM1)
**Timestamp**: 2026-07-25 14:00 UTC
**Commit**: R2357 (HM2→HM1): NVU_BIG_INPUT_FAIL_N 2→3, dsv4p_nv 0% SR rescue. FAIL_N=2 poisoned by single zombie+ATE pair → 180s OPEN window → dsv4p_nv preempted. FAIL_N=3 needs 3 consecutive failures. Single param delta per iron law.
**Agent**: HM2 (opc2_uname)

---

## 1. HM1 系统状态采集 (nv_gw / 40006)

### 1.1 容器状态
- `cc4101`: Up About an hour
- `nv_gw`: Up 37 minutes (healthy)
- `logs_db`: Up 8 days (healthy)

### 1.2 docker exec nv_gw env (关键参数)
```
NVU_TIER_BUDGET_KIMI_NV=230                # R2356
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_BIG_INPUT_COOLDOWN_S=180               # R2327→R2348
NVU_BIG_INPUT_FAIL_N=2                     # R2322 — 本轮目标
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
NVU_BIG_INPUT_THRESHOLD=250000
NVU_EMPTY_200_FASTBREAK=3
KEY_COOLDOWN_S=30
TIER_COOLDOWN_S=30
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=60
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv
UPSTREAM_TIMEOUT=24
```

### 1.3 cc4101 env
```
UPSTREAM_TIMEOUT=90                          # R2355 (30→90)
UPSTREAM_IDLE_TIMEOUT=150
```

### 1.4 DB 延迟 & 错误统计 (6h window)

| model       | total | 200 OK | failed | SR%   | avg_ok_ms | max_ok_ms |
|-------------|-------|--------|--------|-------|-----------|-----------|
| kimi_nv     | 40    | 30     | 10     | 75.0% | 73,886    | 184,894   |
| glm5_2_nv   | 28    | 18     | 10     | 64.3% | 13,033    | 43,265    |
| dsv4p_nv    | 9     | 0      | 9      | 0.0%  | —         | —         |

### 1.5 Failed请求分析

**kimi_nv 失败 (10次)**:
- `all_tiers_exhausted`: 8次 — 持续时间188-220s，**击中230s预算天花板** (R2356 220→230 生效中)
- `NVStream_IncompleteRead`: 1次
- `stream_no_content_gap`: 1次

**glm5_2_nv 失败 (10次)**:
- `all_tiers_exhausted`: 9次 — big_input breaker + 1次 real ATE (26241ms)
- `zombie_empty_completion`: 1次 — 6796ms, 342K chars

**dsv4p_nv 失败 (9次)**:
- 全部 `all_tiers_exhausted` — **100% instant-reject (6-10ms, 1 tier_attempts, 0 tier_attempts rows)**
- big_input breaker OPEN → 所有 dsv4p_nv 请求立即拒绝
- 输入大小: 336K-343K chars

### 1.6 Big-Input Breaker 行为分析

**成功案例**:
- glm5_2_nv: 18次 big_input SUCCESS (342K-343K chars) — SR 64.3% on big inputs

**触发链 (6h window)**:
```
08:33: glm5_2_nv ATE 51506ms (343K) → fail #1
08:34: glm5_2_nv ATE 8ms     (340K) → fail #2 → breaker OPEN (FAIL_N=2)
08:34-08:36: dsv4p_nv 3请求 → 全部 instant-reject (8-10ms) ← COOLDOWN=180s 窗口
10:03: glm5_2_nv ATE 2606ms  (340K) → fail #1
10:03: glm5_2_nv ATE 8ms     (340K) → fail #2 → breaker OPEN
10:03-10:05: dsv4p_nv 3请求 → 全部 instant-reject (6-8ms) ← COOLDOWN=180s 窗口
11:33: glm5_2_nv zombie 6796ms (343K) → fail #1
12:03: glm5_2_nv ATE 26241ms  (343K) → fail #2 → breaker OPEN
12:03-12:06: dsv4p_nv 3请求 → 全部 instant-reject (6-9ms) ← COOLDOWN=180s 窗口
```

**模式**: 每次 breaker OPEN 后，dsv4p_nv 在 COOLDOWN=180s 窗口内全部被拒绝。

### 1.7 Tier attempt errors (6h)
| tier       | error_type                  | count |
|------------|-----------------------------|-------|
| kimi_nv    | empty_200                   | 11    |
| kimi_nv    | NVCFPexecRemoteDisconnected | 3     |

---

## 2. 数据分析与决策

### 2.1 核心发现: dsv4p_nv 0% SR — FAIL_N=2 过于激进

1. **9/9 dsv4p_nv ATE**: 全部瞬间拒绝 (6-10ms)，0 tier_attempts rows
2. **根因**: FAIL_N=2 — 仅需2次连续失败即触发 breaker OPEN
3. **触发模式**: 1次 glm5_2 zombie (6796ms) + 1次 glm5_2 ATE (26s) → breaker OPEN → dsv4p_nv 全灭
4. **glm5_2_nv 实际成功**: 18次 big_input OK (342K-343K chars) — big_input 请求有 64.3% SR
5. **冲击**: dsv4p_nv 被 zombie+ATE 噪声对误伤，完全不可用

### 2.2 dsv4p_nv 被误伤分析

FAIL_N=2 的意图 (R2322): 保护 dsv4p_nv 免受 big-input 170s 挂起

但实际效果: 单个 zombie (6796ms, 非真正挂起) + 单个 ATE (26s) 就触发 breaker，导致 dsv4p_nv 在 180s COOLDOWN 窗口内全部被拒绝。9次 dsv4p_nv 请求全部浪费在 breaker 拒绝上，glm5_2_nv 反而有 18 次成功。

### 2.3 决策: NVU_BIG_INPUT_FAIL_N 2→3

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| NVU_BIG_INPUT_FAIL_N | 2 | 3 | dsv4p_nv 0% SR; FAIL_N=2 被 zombie+ATE 噪声误触发 |

**FAIL_N=3 效果**:
- 需要 3 次连续失败才触发 breaker OPEN
- zombie (6796ms) + ATE (26s) 只计为 2，不触发 → dsv4p_nv 不受影响
- 真正的持续故障模式 (3次>=1次 ATE) 才触发 → 保护仍有效
- glm5_2_nv success 18次证明 big_input 请求有合理成功率

**风险评估**:
- 单参数增量 (+1)，符合铁律
- FAIL_N=3 仍保护 dsv4p_nv 免受真正的持续挂起
- 最坏情况: 3次 ATE 后才触发 breaker，dsv4p_nv 最多损失 3次请求
- 当前损失: 9次 dsv4p_nv 全部被拒绝 → 损失远大于最坏情况
- 健康检查 ✅ (nv_gw: healthy)

---

## 3. 执行

### 3.1 配置变更
```bash
# /opt/cc-infra/docker-compose.yml (HM1 only)
NVU_BIG_INPUT_FAIL_N=2 → NVU_BIG_INPUT_FAIL_N=3
```

### 3.2 重启 nv_gw
```bash
docker compose -f /opt/cc-infra/docker-compose.yml down nv_gw
docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw
```
结果: Container nv_gw Stopped → Removed → Created → Started ✅

### 3.3 验证
- `docker exec nv_gw env | grep NVU_BIG_INPUT_FAIL_N` → `NVU_BIG_INPUT_FAIL_N=3` ✅
- `docker compose config --quiet` → PASS ✅
- 健康检查: `running` ✅

---

## 4. 总结

| 项目 | 值 |
|------|-----|
| 变更参数 | NVU_BIG_INPUT_FAIL_N: 2→3 |
| 变更原因 | dsv4p_nv 0% SR (9/9 ATE); FAIL_N=2 被 zombie+ATE 噪声误触发 |
| 预期效果 | dsv4p_nv 恢复可用 (SR → glm5_2_nv big_input 水平, ~64%) |
| 副作用 | 需要 3 次连续失败才触发 breaker (vs 2次)，最坏情况多损失 1 次 dsv4p_nv 请求 |
| 铁律合规 | ✅ 单参数，只改 HM1 |

## ⏳ 轮到 HM1 优化 HM2