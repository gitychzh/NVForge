# R2003 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 24→22 (-2s)

**时间**: 2026-07-20 07:45 UTC
**触发**: HM1 commit `ae6cd92` R2002 (HM2 cc2) — NOP 巡检 R107
**作者**: opc2_uname (HM2)

## 1. 改前数据 (2026-07-20 07:45 UTC)

### 1.1 概览

| 窗口 | 总 | OK | fail | SR |
|------|-----|-----|------|-----|
| 6h | 41 | 36 | 5 | 87.8% |
| 30m | 2 | 1 | 1 | 50.0% |

### 1.2 Per-model (6h)

| request_model | total | ok | fail | avg_ms | sr_pct |
|---------------|-------|-----|------|--------|--------|
| glm5_2_nv     |    31 | 26 |    5 |   5724 |   83.9 |
| dsv4p_nv      |    10 | 10 |    0 |  31599 |  100.0 |

### 1.3 错误分析

| 模型 | 数量 | 错误类型 | 可修性 |
|------|------|---------|--------|
| glm5_2_nv | 5 | zombie_empty_completion | 代码级(R1107), 不可配置修复 |
| glm5_2_nv | 27 | all_tiers_exhausted (status=200, phantom) | peer-fb rescue |

### 1.4 Genuine OK 耗时

| 模型 | 数量 | avg_ms | min_ms | max_ms |
|------|------|--------|--------|--------|
| glm5_2_nv | 5 | 7117 | 5065 | 9201 |
| dsv4p_nv | 4 | 18212 | 11102 | 24784 |

### 1.5 Zombie 输入

| ts | input_chars | duration_ms |
|----|-------------|-------------|
| 23:33 | 174882 | 4874 |
| 21:33 | 156334 | 3408 |
| 19:03 | 152998 | 4444 |
| 18:33 | 152302 | 3528 |
| 18:04 | 152349 | 4569 |

全部 zombie 输入 > 115K (BIG_INPUT_THRESHOLD), breaker 已生效。

## 2. 优化决策

**改**: `NVU_TIER_BUDGET_GLM5_2_NV` 24→22 (-2s)

### 2.1 理由

- 5 zombie 全部不可配置修复 (NVCF 函数级退化), 唯一优化方向是加速 fail path → 更快 peer-fallback rescue
- glm5_2 genuine OK max=9201ms << 22s (12.8s margin) — 安全, 不会误杀成功请求
- 22 + PEER_FALLBACK=122 = 144 < 151 BUDGET (7s margin) — 约束安全
- 延续 R2001/R1998 轨迹 (26→24→22, 累计 -4s)

### 2.2 Peer-fallback 约束

- PEER_FALLBACK_TIMEOUT=122 ≥ HM2_BUDGET+2=72 ✓
- 22+122=144 < 151 BUDGET ✓ (7s margin)

### 2.3 不改项

- `TIER_TIMEOUT_BUDGET_S=151`: 已接近 144+0=144 安全线, 不再压
- `NVU_TIER_BUDGET_DSV4P_NV=20`: dsv4p 100% SR 6h, 无改变需求
- `UPSTREAM_TIMEOUT=30`: dsv4p OK max=24784ms < 30s safe
- `KEY_COOLDOWN_S=60` / `TIER_COOLDOWN_S=60`: 零 key_cycle_429s, 稳定

## 3. 改后验证

- 确值: `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV` → 22 ✓
- 健康: `curl /health` → `{"status":"ok"}` ✓
- 日志: 无 error/warn ✓
- 约束: 22+122=144<151 ✓

## 4. 铁律

- 只改 HM1 不改 HM2 ✓
- 单参数每轮 ✓
- 改前有数据 ✓
- 改后有验证 ✓

## ⏳ 轮到HM1优化HM2
