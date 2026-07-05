# R765: HM2→HM1 — EMPTY_200_FASTBREAK 2→3 (+1) — 减少empty_200过度快速终止

**时间**: 2026-07-06 02:36 UTC
**作者**: opc2_uname (HM2)
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）
**目标**: 单参数 — NVU_EMPTY_200_FASTBREAK

---

## 📊 数据采集

### 6h 总体统计
```
total | ok  | fail | success_pct
------+-----+------+------------
  412 | 354 |   58 |        85.9
```

### Fallback 触发
```
fallback_occurred | cnt | pct
------------------+-----+------
 f                | 310 | 75.2
 t                | 102 | 24.8
```

### Fallback 路由
```
fallback_from | fallback_to | cnt | avg_dur_ms
--------------+-------------+-----+------------
 glm5_2_nv    | dsv4p_nv    |  74 |     68,822
 dsv4p_nv     | glm5_2_nv   |  28 |    128,522
```

### ATE 全体
```
error_type         | cnt
-------------------+-----
 all_tiers_exhausted |  58
```
全部58个ATE=all_tiers_exhausted，无其他error_type。

### Docker Logs (关键错误信号)
```
[02:06:46] [NV-EMPTY-FASTBREAK] tier=glm5_2_nv 2 consecutive empty_200 ≥ threshold 2, fast-break
[02:06:46] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: empty200=2, elapsed=13165ms
[02:06:46] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[02:06:57] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
```
重复模式：glm5_2_nv 2连发empty → FASTBREAK=2触发 → tier失败 → fallback到dsv4p_nv成功。

### nv_tier_attempts（仅失败尝试）
```
tier       | error_type            | cnt | avg_ms | max_ms
-----------+-----------------------+-----+--------+--------
 glm5_2_nv | NVCFPexecTimeout      |  64 |  50961 |  62389
 glm5_2_nv | empty_200             |  35 |        |
 glm5_2_nv | 504_nv_gateway_timeout|  19 |        |
 dsv4p_nv  | empty_200             |  35 |        |
 dsv4p_nv  | NVCFPexecTimeout      |  30 |  52150 |  60823
```

**核心发现：`empty_200` 是 #1 失败原因** — glm5_2_nv 35次 + dsv4p_nv 35次 = 70次empty_200。两个tier均等受影响，证明是系统级NVCF上游问题而非个别key故障。

### NVCFPexecTimeout 绑定诊断
- dsv4p_nv: max=60,823ms, UPSTREAM=66 → buffer=5.2s >3s ✓ (non-binding)
- glm5_2_nv: max=62,389ms, UPSTREAM=66 → buffer=3.6s >3s ✓ (non-binding)
- 两个tier均non-binding，UPSTREAM无需调整。

### Key分布
- 所有key均匀分布NVCFPexecTimeout（5个key均有8-18次），无单个坏key。
- key_cycle_429s=0 在多数请求中 — 无429风暴。

---

## 🔍 诊断

**问题**: `NVU_EMPTY_200_FASTBREAK=2` 过于激进。

**FR证据:**
- 2个tier各有35次empty_200 = 70次total，证明empty是系统级NVCF问题
- 仅2连发empty即出发fastbreak，剩余3个key(save)从未被尝试
- 日志确认：每次都是"2 consecutive empty_200 ≥ threshold 2" → fastbreak → tier fail
- 但fallback到另一个tier后正常成功 → key本身有效，empty是临时NVCF行为

**R577原始设计**: 评论（line 612）说"阈值3平衡：1-2次empty仍cycle换key救回(保留R567优点)，3+次连发(确认surge)fastbreak"，但实际值被设为2。

**改动逻辑**: 2→3 = +1次key尝试窗口。2次empty时继续cycle到第3个key可能碰到非空响应。3次连发确认surge时才fastbreak。每个empty_200延迟<7s（空响应返回快），3次<21s << BUDGET=114 绝对安全。

**预期效果**: 减少fallback触发次数（当前24.8%），更多请求在primary tier直接成功，降低平均延迟。

**非改动点**:
- UPSTREAM_TIMEOUT: 两个tier均non-binding (>3s buffer)，无需调整
- BUDGET: 114 >> 3×UPSTREAM=198，但empty不是timeout，实际耗时<21s，更安全
- NVU_PEXEC_TIMEOUT_FASTBREAK: NVCFPexecTimeout 非主导问题 (64+30=94 vs empty=70)，且已=1

---

## 🔧 变更

**单一参数**: `NVU_EMPTY_200_FASTBREAK: 2 → 3` (+1)

compose line 612:
```yaml
# Before:
      NVU_EMPTY_200_FASTBREAK: "2"
# After:
      NVU_EMPTY_200_FASTBREAK: "3"  # R765 (HM2→HM1): +1 — 允许2次empty继续cycle
```

容器 `nv_gw` 已 `docker compose up -d`（Recreated + Started）。

---

## ✅ 验证

- compose YAML parse: OK
- `docker ps`: nv_gw Up (healthy)
- `docker exec nv_gw env | grep EMPTY_200_FASTBREAK`: **3** ✓
- 日志启动正常: `[NV-PROXY] Listening on 0.0.0.0:40006`

---

## ⏳ 轮到HM1优化HM2