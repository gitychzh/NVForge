# R1889 (HM2→HM1): Add dsv4p_nv to BIG_INPUT breaker

## 触发
- Commit `3baf0b0` (R1888 HM1) — `NOP 零新流量`，脚本判定轮到HM2优化HM1
- 前一 HM2→HM1 回合: R1888 (NOP)

## 改前数据

### 6h 窗口 (2026-07-19 ~07:06–13:06 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 48 |
| 成功 | 20 (41.7%) |
| 失败 | 28 (58.3%) |
| Phantom ATE (status=200 rescued) | 13 |

**Per-model (6h):**

| Model | Total | OK | Fail | SR | avg_ok_ms | max_ok_ms |
|-------|-------|-----|------|-----|-----------|-----------|
| glm5_2_nv | 42 | 15 | 27 | 35.7% | 6366 | 15650 |
| dsv4p_nv | 6 | 5 | 1 | 83.3% | 6528 | 9778 |

**Error breakdown (6h):**

| Error Type | Count |
|-----------|-------|
| zombie_empty_completion | 28 |
| all_tiers_exhausted (phantom, status=200) | 13 |

- 28 zombies: glm5_2_nv=27, dsv4p_nv=1 (33.7s wasted!)
- All 48 requests: big_input (>115K)
- 0 fallback (fallback_occurred=f for all 48)
- 0 SSLEOF, 0 500_nv_error, 0 breaker OPEN
- 0 peer-fb triggered
- 0 ms_requests

### 30min 窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 3 |
| 成功 | 2 (66.7%) |
| 失败 | 1 |

### 1h 窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 8 |
| 成功 | 7 (87.5%) |
| 失败 | 1 |

### 关键发现: dsv4p_nv zombie

- dsv4p_nv 不在 `NVU_BIG_INPUT_MODELS` 中（仅 `glm5_2_nv`）
- 6h 内 1 条 dsv4p_nv zombie: `04:05:43 UTC`, input=126050c, duration=33734ms
- 浪费 33.7s — 明显可修的漏网之鱼
- BIG_INPUT breaker 对 glm5_2_nv 有效（30min 窗 100% SR 来自 breaker 阻断）

### Env

- UPSTREAM_TIMEOUT=43
- TIER_TIMEOUT_BUDGET_S=178
- KEY_COOLDOWN_S=44
- TIER_COOLDOWN_S=44
- NVU_TIER_BUDGET_GLM5_2_NV=60
- NVU_TIER_BUDGET_DSV4P_NV=39
- NVU_BIG_INPUT_FAIL_N=1
- NVU_BIG_INPUT_COOLDOWN_S=21600
- NVU_BIG_INPUT_MODELS=glm5_2_nv ← **只覆盖 glm5_2_nv**
- NVU_PEER_FALLBACK_TIMEOUT=122
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=1
- NVU_SSLEOF_RETRY_DELAY_S=0.1
- 零容器漂移 ✓

### 容器

- `nv_gw`: Up 21 minutes → 重启后变 Up seconds
- `/health`: `{"status": "ok"}`

## 分析

### 介入条件检查
1. **SR 连破 93%**: 41.7% — 满足
2. **非跳过类 fallback ≥4**: 0 — 不满足
3. **breaker OPEN**: 0 — 不满足
4. **新错误分类**: dsv4p_nv zombie 可修 — 满足

### 决策: 1改 — 添加 dsv4p_nv 到 BIG_INPUT breaker

**改前**: `NVU_BIG_INPUT_MODELS=glm5_2_nv`
**改后**: `NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv`

**理由**:
- R1881-R1888 已穷尽调参旋钮，zombie 非 config 可修（NVCF 侧 content-filter）
- 但 dsv4p_nv 不在 BIG_INPUT breaker 覆盖范围 — 这是覆盖面漏洞，非参数调优
- BIG_INPUT breaker 对 glm5_2_nv 已证明有效：30min 窗 100% SR
- 添加 dsv4p_nv 可以消除 1 条 zombie/6h，节约 33.7s 浪费
- 最小改动：1 个参数 + 1 行

**不调其他参数**: zombie 根因在 NVCF 侧 content-filter，R1881-R1886 已穷尽反证。BIG_INPUT breaker 是唯一有效的防线。

## 改后验证

- Compose: `NVU_BIG_INPUT_MODELS: "glm5_2_nv,dsv4p_nv"` ✓
- `docker compose up -d nv_gw`: Container restarted ✓
- `docker exec nv_gw env`: `NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv` ✓
- `/health`: `{"status": "ok"}` ✓
- `docker logs nv_gw`: Clean startup, no errors ✓
- 零容器漂移 ✓

## 提交
- R1889 回合文件: `rounds/R1889_hm2_optimize_hm1.md`
- 铁律: 只改 HM1 不改 HM2 ✓
## ⏳ 轮到HM1优化HM2
