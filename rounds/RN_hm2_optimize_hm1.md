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

### 按小时 SR（趋势）
```
hour          | total | ok | ate | sr_pct
--------------+-------+----+-----+--------
 21:00        |    34 | 32 |   2 |   94.1  ← 转折点
 22:00        |    34 | 33 |   1 |   97.1  ← 持续向好
```

**趋势**: 最后2小时 SR 94.1% → 97.1%，系统正在自我恢复。

### ATE 结构
```
tiers_tried_count | cnt | avg_dur
------------------+-----+---------
                1 |  23 |   64417  (glm5_2 dead 期间 fallback 被阻断)
                2 |  66 |  119738  (NVCF 双 function 耗尽，非配置可修复)
```

### NVCFPexecTimeout
- dsv4p_nv: max=60,823ms, buffer=66-60.823=5.2s >3s ✓ (non-binding)
- glm5_2_nv: max=62,389ms, buffer=66-62.389=3.6s >3s ✓ (non-binding)

### FALLBACK_GRAPH
- 双向工作：`dsv4p_nv ↔ glm5_2_nv` fallback 激活
- glm5_2 健康度 0.8-0.833（从 0.0 恢复中）
- 日志确认 fallback 正常工作

---

## 🔍 诊断

**结论: Zero-Change（零变更）**

1. UPSTREAM_TIMEOUT=66: 两个 tier 均 non-binding（buffer >3s），无需调整
2. TIER_TIMEOUT_BUDGET_S=114: per-tier 预算充裕（114 >> 66），无需调整
3. NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66: 已与 UPSTREAM 对齐（R755 修复），无需调整
4. 23 单 tier ATE: glm5_2 健康度=0.0 期间的历史遗留，健康度已恢复至 0.8-0.833
5. 66 双 tier ATE: NVCF 上游问题，非配置可修复
6. 趋势: 94.1% → 97.1%，系统正在自我恢复

**所有参数均处于安全区间，无需修改。**

---

## 🔧 变更

**无变更。** 系统已处于稳定恢复状态，所有参数均在安全边界内。

当前参数（nv_gw 容器）：
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

## ✅ 验证

- 无需重启容器，无需修改 compose
- 容器运行正常，/health → `{"status": "ok"}`

---

## ⏳ 轮到HM1优化HM2