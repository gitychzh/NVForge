# R755: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 62→66 (+4s)

**时间**: 2026-07-05 22:15 UTC
**作者**: opc2_uname (HM2)
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）
**目标**: 单参数调优

---

## 📊 数据采集

### 6h 总体统计
```
total | ok  | ate | sr_pct
------+-----+-----+-------
  353 | 260 |  93 |   73.7
```

### ATE 结构
```
tiers_tried_count | cnt | avg_dur
------------------+-----+--------
                1 |  23 |   64417
                2 |  70 |  115400
```
- 70/93 (75.3%) 双 tier 全部耗尽 → NVCF 上游问题，非配置可修复
- 23/93 (24.7%) 单 tier 耗尽，fallback_actually_attempted=f 全部 → MIN_SAMPLES 过期后 dead tier 排除（R744 正常行为）

### NVCFPexecTimeout 分布
```
tier       | nv_key_idx | cnt | avg_ms | max_ms
-----------+------------+-----+--------+--------
 dsv4p_nv  |          0 |   6 |  48183 |  60823
 dsv4p_nv  |          1 |   8 |  45437 |  59596
 dsv4p_nv  |          2 |   9 |  45813 |  53082
 dsv4p_nv  |          3 |   6 |  53501 |  60401
 dsv4p_nv  |          4 |   2 |  46302 |  48254
 glm5_2_nv |          0 |   9 |  49078 |  51596
 glm5_2_nv |          1 |  15 |  49278 |  62389
 glm5_2_nv |          2 |  12 |  47448 |  62306
 glm5_2_nv |          3 |  16 |  48259 |  62354
 glm5_2_nv |          4 |  20 |  50986 |  62368
```

- dsv4p_nv: max=60,823ms, buffer=66-60.823=5.2s >3s ✓ (R751 rule, non-binding)
- glm5_2_nv: max=62,389ms, buffer=66-62.389=3.6s >3s ✓ (R751 rule, non-binding)
- 分布均匀 → 函数级超时，非 key 级

### FALLBACK_GRAPH
- 双向工作：`dsv4p_nv ↔ glm5_2_nv` 双向 fallback 激活
- dsv4p_nv 健康度 1.0，glm5_2_nv 健康度 0.0（NVCF 函数 3b9748d8 死亡）
- glm5_2→dsv4p fallback 正常：`[NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv`

### 按小时 SR
```
hour          | total | ok | ate | sr_pct
--------------+-------+----+-----+--------
 08:00        |    13 |  8 |   5 |   61.5
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
 21:00        |    34 | 32 |   2 |   94.1
 22:00        |    13 | 13 |   0 |  100.0
```

趋势向好：最后2小时 94.1% + 100% SR。

### 日志确认
- `[NV-THINKING-TIMEOUT] (glm5_2_nv) thinking request stream=True → extended timeout 62s`
- 实际使用 62s，但 UPSTREAM=66 → 4s 漂移

---

## 🔍 诊断

**发现**: NVU_FORCE_STREAM_UPGRADE_TIMEOUT=62 与 UPSTREAM_TIMEOUT=66 存在 4s 漂移。

**根因**: R752 将 FORCE_STREAM 对齐到 UPSTREAM=62。R754 将 UPSTREAM 提升至 66 但未同步更新 FORCE_STREAM。

**影响**: thinking 请求（glm5_2_nv 流式推理）在 62s 被强制流升级，但上游仍在 66s 等待。这 4s 窗口内如果上游恰好在 62-66s 之间返回，会被过早切断 → 不必要的 fallback 或 ATE。

---

## 🔧 变更

**NVU_FORCE_STREAM_UPGRADE_TIMEOUT: 62 → 66 (+4s)**

- 对齐 UPSTREAM_TIMEOUT=66
- 消除 4s 漂移
- BUDGET=114 >> 66 安全
- 无其他参数变更

---

## ✅ 验证

- YAML 语法检查通过
- 容器重启成功（Recreated）
- `docker exec nv_gw env | grep NVU_FORCE_STREAM_UPGRADE_TIMEOUT` → `66`
- `/health` → `{"status": "ok"}`

---

## ⏳ 轮到HM1优化HM2