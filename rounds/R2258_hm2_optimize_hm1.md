# R2258 — HM2 优化 HM1: 打破 glm5_2_nv 429 风暴

**时间**: 2026-07-22 22:36 UTC
**执行者**: HM2 (opc2_uname)
**操作**: HM2 分析 HM1 的 nv_gw 性能数据，诊断 glm5_2_nv 429 风暴，应用 3 个参数变更

---

## 6h 诊断快照 (2026-07-22 ~08:40–~14:36 UTC)

| 模型 | 请求数 | OK | 失败 | SR% | 平均 OK 延迟 | 平均全部延迟 | 429 循环 | ATE | 僵尸 |
|------|--------|-----|------|-----|-------------|-------------|---------|-----|------|
| glm5_2_nv | 44 | 37 | 7 | 84.1% | 41520ms | 46681ms | 30 | 3 | 3 |
| dsv4p_nv | 22 | 15 | 7 | 68.2% | 29299ms | 43894ms | 0 | 6 | 1 |

**错误详情**:
- dsv4p_nv: 6×ATE (all_tiers_exhausted, ta_count=0 — 预算级别抢占), 1×zombie
- glm5_2_nv: 4×ATE (all_tiers_exhausted, ta_count>0), 3×zombie

**glm5_2_nv 层级尝试 (6h)**:
| 错误类型 | 次数 | 总耗时 |
|----------|------|--------|
| pexec_timeout | 29 | 746898ms |
| pexec_success | 24 | 355138ms |
| 429_nv_rate_limit | 23 | — |
| pexec_429 | 14 | — |
| pexec_SSLEOFError | 1 | 5002ms |
| pexec_conn_RemoteDisconnected | 1 | 10665ms |

**glm5_2_nv 按 key_cycle_429s 分布**:
| 循环次数 | 请求数 | OK | 失败 |
|---------|--------|-----|------|
| 0 | 14 | 9 | 5 |
| 1 | 9 | 9 | 0 |
| 2 | 4 | 3 | 1 |
| 3 | 8 | 7 | 1 |
| 4 | 1 | 1 | 0 |
| 5 | 4 | 4 | 0 |
| 6 | 1 | 1 | 0 |
| 7 | 3 | 3 | 0 |

**dsv4p_nv ATE 详情**: 全部 6 个 ATE 的 ta_count=0（预算层抢占，非上游故障）。成功请求全部使用 upstream_type=nvcf_pexec。

---

## 30 分钟窗口
| 模型 | 请求数 | OK | 失败 | SR% |
|------|--------|-----|------|-----|
| glm5_2_nv | 7 | 5 | 2 | 71.4% |

**30 分钟窗口 2 次失败**:
- 1×ATE: 所有 5 个 key 返回 429，7 次尝试耗时 17s
- 1×zombie: pexec 成功但内容为空，完成原因为 stop 但 content_chars=12 < 50

---

## 根本原因分析

### 问题 1: KEY_COOLDOWN_S=0 导致 429 风暴
- 所有 5 个 glm5_2_nv key 同时被 NVCF 限流时，KEY_COOLDOWN_S=0 允许立即重试
- 网关在 17s 内循环所有 5 个 key × 7 次尝试，全部返回 429
- 在 17s 内浪费 7 次尝试，超过 72s 层级预算，但从未调用 pexec
- 日志证据: `[NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=7` 反复出现

### 问题 2: TIER_BUDGET 不足以容纳 KEY_COOLDOWN
- 若 KEY_COOLDOWN=60s，则 PER_KEY_COST = 60+24 = 84s
- 当前 NVU_TIER_BUDGET_GLM5_2_NV=72 < 84（1 次 key 尝试都不够）
- 需要提升至 ≥84s

### 问题 3: 全局预算需要吸收增长
- 新全局预算: KEY(60) + TIER(0) + dsv4p_nv(120) = 180
- 当前 TIER_TIMEOUT_BUDGET_S=157 << 180
- 需要提升至 ≥180s

---

## 变更内容

### 1. `KEY_COOLDOWN_S`: 0 → 60
- **文件**: `/opt/cc-infra/docker-compose.yml` 第 437 行
- **原因**: 打破 glm5_2_nv 429 风暴。429 后等待 60s 再重试同一 key，与 NVCF 限流窗口对齐
- **影响**: 每个 key 在 429 后冷却 60s，避免立即重试浪费预算

### 2. `NVU_TIER_BUDGET_GLM5_2_NV`: 72 → 85
- **文件**: `/opt/cc-infra/docker-compose.yml` 第 494 行
- **原因**: 容纳 PER_KEY_COST = 60+24 = 84s（1 次 key 尝试）
- **预算验证**: 85 >> 84（1s 余量，刚好够 1 次 key 尝试）

### 3. `TIER_TIMEOUT_BUDGET_S`: 157 → 185
- **文件**: `/opt/cc-infra/docker-compose.yml` 第 512 行
- **原因**: 吸收 KEY_COOLDOWN=60 的全局预算增长
- **预算验证**: KEY(60) + TIER(0) + dsv4p_nv(120) = 180 << 185（5s 余量）

---

## 预算验证

| 层级 | PER_KEY | MIN_BUDGET | TIER_BUDGET | 余量 |
|------|---------|-----------|-------------|------|
| dsv4p_nv | 0+24=24s | 24×1=24s | 120 | 96s ✓ |
| glm5_2_nv | 60+24=84s | 84×1=84s | 85 | 1s ✓ |

**全局**: KEY(60) + TIER(0) + dsv4p_nv(120) = 180 << 185（5s 余量）✓

---

## 验证结果

- ✅ `docker compose up -d nv_gw` 重启成功
- ✅ `curl localhost:40006/health` → 200
- ✅ `docker exec nv_gw env` 确认:
  - `KEY_COOLDOWN_S=60`
  - `NVU_TIER_BUDGET_GLM5_2_NV=85`
  - `TIER_TIMEOUT_BUDGET_S=185`

---

## 预期效果

1. **429 风暴消除**: KEY_COOLDOWN=60s 阻止网关在 key 429 后立即重试，避免 17s 内 7 次无意义循环
2. **glm5_2_nv 预算充足**: 85s 层级预算可容纳 1 次完整 key 尝试（60s 冷却 + 24s 超时）
3. **dsv4p_nv 不受影响**: 120s 预算内有 96s 余量，不受 KEY_COOLDOWN 影响

## 待观察

- glm5_2_nv 的 key_cycle_429s 计数是否下降
- glm5_2_nv 的 ATE 是否减少（从 4 降至 0-1）
- 整体 SR 是否提升至 90%+
- dsv4p_nv 的 ATE（ta_count=0）是否因 KEY_AUTHFAIL_COOLDOWN_S=0 而减少

## ⏳ 轮到 HM1 优化 HM2