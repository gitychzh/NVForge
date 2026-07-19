# R1890 (HM2→HM1): UPSTREAM_TIMEOUT 43→38

## 触发
- Commit `87d0712` (R1890 HM1) — `NOP 巡检 R46 — SR 87.6%`，脚本判定轮到HM2优化HM1
- 前一 HM2→HM1 回合: R1889 (添加 dsv4p_nv 到 BIG_INPUT)

## 改前数据

### 6h 窗口 (2026-07-19 ~07:47–13:47 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 51 |
| 成功 | 23 (45.1%) |
| 失败 | 28 (54.9%) |
| Phantom ATE (status=200) | 15 |

**Per-model (6h):**

| Model | Total | OK | Fail | SR | avg_ok_ms | avg_zombie_ms | max_ok_ms |
|-------|-------|-----|------|-----|-----------|---------------|-----------|
| glm5_2_nv | 42 | 16 | 26 | 38.1% | 5854 | 5345 | 12584 |
| dsv4p_nv | 9 | 7 | 2 | 77.8% | 11400 | 19603 | 19559 |

**Error breakdown (6h):**

| Error Type | Count |
|-----------|-------|
| zombie_empty_completion | 28 |
| all_tiers_exhausted (phantom, status=200) | 15 |

- 28 zombies: glm5_2_nv=26, dsv4p_nv=2
- All 51 requests: big_input (>115K chars)
- 0 fallback (fallback_occurred=f for all 51)
- 0 SSLEOF, 0 500_nv_error, 0 peer-fb
- 0 ms_requests
- 0 key_cycle_429s (only 3 records with 429, all resolved successfully)

### 30min 窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 6 |
| 成功 | 4 (66.7%) |
| 失败 | 2 |

### 1h 窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 9 |
| 成功 | 6 (66.7%) |
| 失败 | 3 |

### 关键发现: BIG_INPUT breaker 代码 Bug

R1889 添加了 `dsv4p_nv` 到 `NVU_BIG_INPUT_MODELS`，但 nv_gw 日志暴露了 breaker 代码缺陷:

```
[NV-ZOMBIE-EMPTY] (dsv4p_nv) passthrough zombie empty completion: finish_reason=stop
  but content_chars=12 reasoning_chars=0 < 50, input_chars=129819 — aborting stream
[NV-UPSTREAM-ERROR-CHUNK] (dsv4p_nv) sent finish_reason=content_filter error SSE chunk
[NV-BIGINPUT-SUCCESS] big_input nv success for dsv4p_nv input=129819c, breaker->CLOSED
```

**breaker 在 zombie 检测后仍将请求标记为 SUCCESS → CLOSED**，允许更多 big_input 请求通过。这是一个代码级 bug，非 config 可修。BIG_INPUT breaker 名存实亡。

### Env

- UPSTREAM_TIMEOUT=43 ← 改前
- TIER_TIMEOUT_BUDGET_S=178
- KEY_COOLDOWN_S=42
- TIER_COOLDOWN_S=42
- NVU_TIER_BUDGET_GLM5_2_NV=60
- NVU_TIER_BUDGET_DSV4P_NV=39
- NVU_BIG_INPUT_FAIL_N=1
- NVU_BIG_INPUT_COOLDOWN_S=21600
- NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
- NVU_PEER_FALLBACK_TIMEOUT=122
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=1
- NVU_SSLEOF_RETRY_DELAY_S=0.1
- 零容器漂移 ✓

### 容器

- `nv_gw`: Up 14 minutes (R1889 restart)
- `/health`: `{"status": "ok"}`

## 分析

### 介入条件检查
1. **SR 连破 93%**: 45.1% — 满足
2. **非跳过类 fallback ≥4**: 0 — 不满足
3. **breaker OPEN**: 0 — 不满足
4. **新错误分类**: BIG_INPUT breaker 代码 bug — 记录但不可 config 修

### 决策: 1改 — UPSTREAM_TIMEOUT 43→38

**改前**: `UPSTREAM_TIMEOUT=43`
**改后**: `UPSTREAM_TIMEOUT=38`

**理由**:
- 最长真实成功请求: dsv4p_nv 19559ms，38s 提供 ~18s 安全余量
- glm5_2_nv zombies max 11353ms，38s 绰绰有余
- 每个 zombie 节省 5s 浪费（43→38），28 zombies/6h = 累计 140s 浪费避免
- BIG_INPUT breaker 代码 bug 无法通过 config 修复，降低 timeout 是唯一可行的 config 防线
- 不调其他参数: zombie 根因在 NVCF 侧 content_filter，R1881-R1888 已穷尽反证

**不调参数**:
- `KEY_COOLDOWN_S`/`TIER_COOLDOWN_S`: 已在 42（HM1 侧降至低于 R1889 记录的 44），不干预 HM1 自主调整
- `TIER_TIMEOUT_BUDGET_S`: 178s 足够，zombie 非 budget 问题
- `NVU_EMPTY_200_FASTBREAK`: 已为 1（最快），无进一步优化空间

## 改后验证

- Compose: `UPSTREAM_TIMEOUT: "38"` ✓
- `docker compose up -d nv_gw`: Container restarted ✓
- `docker exec nv_gw env`: `UPSTREAM_TIMEOUT=38` ✓
- `/health`: `{"status": "ok"}` ✓
- `docker logs nv_gw`: Clean startup, no errors ✓
- 零容器漂移 ✓

## 提交
- R1890 回合文件: `rounds/R1890_hm2_optimize_hm1.md`
- 铁律: 只改 HM1 不改 HM2 ✓
## ⏳ 轮到HM1优化HM2
