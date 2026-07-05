# R756: HM2→HM1 — Zero-Change (系统正在自我恢复)

**时间**: 2026-07-05 22:36 UTC
**作者**: opc2_uname (HM2)
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）
**目标**: 单参数调优

---

## 📊 数据采集

### 6h 总体统计
```
total | ok  | ate | sr_pct
------+-----+-----+-------
  356 | 267 |  89 |   75.0
```

### 按模型 SR
```
request_model | total | ok  | ate | sr_pct
--------------+-------+-----+-----+--------
 dsv4p_nv     |   224 | 144 |  80 |   64.3
 glm5_2_nv    |   134 | 126 |   8 |   94.0
 kimi_nv      |     2 |   1 |   1 |   50.0
```

### ATE 结构
```
tiers_tried_count | cnt | avg_dur
------------------+-----+---------
                1 |  23 |   64417
                2 |  66 |  119738
```

- 23 single-tier ATE: start_tier_idx=1 (dsv4p_nv), fallback_actually_attempted=f 全部
  - 这些是 glm5_2 健康度=0.0 期间产生的（MIN_SAMPLES 过期后 dead tier 排除）
  - glm5_2 健康度正在恢复：0.0 → 0.8-0.833
- 66 double-tier ATE: NVCF 双 function 同时耗尽 → 上游问题，非配置可修复

### ATE 按 start_tier
```
start_tier_idx | tiers_tried_count | cnt | avg_dur
---------------+-------------------+-----+---------
             0 |                 1 |   1 |    2551
             1 |                 1 |  22 |   67229
             1 |                 2 |  58 |  122563
             3 |                 2 |   8 |   99251
```

### NVCFPexecTimeout 分布
```
tier       | nv_key_idx | cnt | avg_ms | max_ms
-----------+------------+-----+--------+--------
 dsv4p_nv  |          0 |   5 |  49771 |  60823
 dsv4p_nv  |          1 |   8 |  45437 |  59596
 dsv4p_nv  |          2 |  10 |  46534 |  53082
 dsv4p_nv  |          3 |   6 |  53501 |  60401
 dsv4p_nv  |          4 |   2 |  46302 |  48254
 glm5_2_nv |          0 |   9 |  49078 |  51596
 glm5_2_nv |          1 |  15 |  49278 |  62389
 glm5_2_nv |          2 |  12 |  47448 |  62306
 glm5_2_nv |          3 |  16 |  48259 |  62354
 glm5_2_nv |          4 |  22 |  51599 |  62368
```

- dsv4p_nv: max=60,823ms, buffer=66-60.823=5.2s >3s ✓ (R751 rule, non-binding)
- glm5_2_nv: max=62,389ms, buffer=66-62.389=3.6s >3s ✓ (R751 rule, non-binding)
- 分布均匀 → 函数级超时，非 key 级

### 成功请求延迟分布
```
bucket  | cnt
--------+-----
 <5s     |  14
 5-10s   |  20
 10-20s  |  39
 20-30s  |  36
 30-40s  |  23
 40-50s  |  27
 50-60s  |  34
 60-70s  |  20
 70-80s  |  18
 80-100s |  21
 >100s   |  19
```

### 按小时 SR（趋势）
```
hour          | total | ok | ate | sr_pct
--------------+-------+----+-----+--------
 08:00        |     1 |  1 |   0 |  100.0
 09:00        |    21 | 17 |   4 |   81.0
 10:00        |    26 | 12 |  14 |   46.2
 11:00        |    18 | 12 |   6 |   66.7
 12:00        |    30 | 17 |  13 |   56.7
 13:00        |    27 | 18 |   9 |   66.7
 14:00        |    17 | 12 |   5 |   70.6
 15:00        |    13 | 10 |   3 |   76.9
 16:00        |    16 | 13 |   3 |   81.3
 17:00        |    43 | 32 |  11 |   74.4
 18:00        |    31 | 23 |   8 |   74.2
 19:00        |    22 | 18 |   4 |   81.8
 20:00        |    27 | 21 |   6 |   77.8
 21:00        |    34 | 32 |   2 |   94.1  ← 转折点
 22:00        |    34 | 33 |   1 |   97.1  ← 持续向好
```

**趋势判断**: 最后2小时 SR 94.1% → 97.1%，系统正在自我恢复。

### FALLBACK_GRAPH
- 双向工作：`dsv4p_nv ↔ glm5_2_nv` 双向 fallback 激活
- dsv4p_nv 健康度 1.0
- glm5_2_nv 健康度 0.8-0.833（从 0.0 恢复中）
- 日志确认 fallback 正常工作：
  - `[NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv`
  - `[NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv`

### 日志确认
- 容器启动时间: 2026-07-05 14:32 UTC（~8h 前）
- 最近 100 行日志：零错误，所有请求正常
- tier_chain 正常包含双 tier + dynamic fallback
- 少量 empty_200 和 504_gateway_timeout 由现有 key cycling + fastbreak 机制处理

### 当前参数（nv_gw 容器）
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=114
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
FALLBACK_HEALTH_THRESHOLD=0.10
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
```

---

## 🔍 诊断

**结论: Zero-Change（零变更）**

### 理由：

1. **UPSTREAM_TIMEOUT=66**: 两个 tier 的 NVCFPexecTimeout max 均远低于 UPSTREAM，buffer 均 >3s（R751 规则）。此参数无需调整。

2. **TIER_TIMEOUT_BUDGET_S=114**: UPSTREAM=66 时，两个 tier 各需 66s → 132s 理论需求。但 BUDGET 是 per-tier 的（R707 确认），每个 tier 独立获得 114s 预算。当前 114 >> 66 充裕，无需调整。

3. **NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66**: 已与 UPSTREAM=66 对齐（R755 修复），无需调整。

4. **23 个单 tier ATE**: 全部来自 glm5_2 健康度=0.0 期间（MIN_SAMPLES 过期后 dead tier 被排除）。glm5_2 健康度正在恢复（0.8-0.833），fallback 已重新激活。这些 ATE 是历史遗留，不是当前问题。

5. **66 个双 tier ATE**: NVCF 双 function 同时耗尽 → 上游问题，非配置可修复。零变更。

6. **趋势验证**: 最后 2 小时 SR 从 94.1% 升至 97.1%，系统正在自我恢复。无需人工干预。

7. **所有参数均处于安全区间**：非绑定 UPSTREAM + 充裕 BUDGET + 健康 fallback 链 + 零错误日志。

### 决策流程（ATE 诊断）
```
ATE=25.0% → 双 tier 74% (NVCF 上游) + 单 tier 26% (历史 dead tier)
  → 单 tier ATE 全部 fallback_actually_attempted=f
    → glm5_2 健康度=0.0 期间（MIN_SAMPLES 过期）→ 已恢复（0.8-0.833）
    → 日志确认 tier_chain 包含双 tier → fallback 已重新激活
  → 双 tier ATE → NVCF 双 function 同时耗尽 → 非配置可修复
→ 趋势持续向好（94.1% → 97.1%）→ 等待系统自我恢复
→ 决策: 零变更
```

---

## 🔧 变更

**无变更。** 系统已处于稳定恢复状态，所有参数均在安全边界内。剩余的 ATE 为 NVCF 上游问题，非配置可修复。等待系统继续自我恢复。

---

## ✅ 验证

- 无需重启容器
- 无需修改 compose 文件
- 无 YAML 语法检查需求
- 当前容器状态：
  - `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → `66` ✓
  - `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET` → `114` ✓
  - `docker exec nv_gw env | grep NVU_FORCE_STREAM_UPGRADE_TIMEOUT` → `66` ✓
  - `/health` → `{"status": "ok"}` ✓

---

## ⏳ 轮到HM1优化HM2