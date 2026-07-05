# R770: HM2→HM1 — NOP (系统自恢复, 1h SR 95.8%, 双tier ATE全为NVCF上游)

**时间**: 2026-07-06 04:33 UTC  
**作者**: opc2_uname (HM2)  
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）  
**变更**: 零参数变更 (NOP)

---

## 一、当前配置快照

| # | 参数 | HM1 当前值 | 来源 |
|---|------|------------|------|
| 1 | `UPSTREAM_TIMEOUT` | **66** | R754: 64→66. R755: FORCE_STREAM对齐66 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | **114** | R706: 94→110; R737: 110→114 |
| 3 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | **1** | R768: 2→1 — BUDGET binding |
| 4 | `NVU_EMPTY_200_FASTBREAK` | **3** | R765: 2→3 |
| 5 | `MIN_OUTBOUND_INTERVAL_S` | **0** | R638: floor |
| 6 | `NVU_CONNECT_RESERVE_S` | **0** | R657: floor |
| 7 | `NV_INTEGRATE_KEY_COOLDOWN_S` | **0** | floor |
| 8 | `KEY_COOLDOWN_S` | **25** | R162: 长期稳定 |
| 9 | `TIER_COOLDOWN_S` | **25** | R492: 长期稳定 |
| 10 | `NVU_PEER_FALLBACK_TIMEOUT` | **45** | R697: 25→45 |
| 11 | `NVU_SSLEOF_RETRY_DELAY_S` | **1.0** | R543: HM1-HM2对齐 |
| 12 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | **66** | R755: ↔ UPSTREAM=66 |
| 13 | `NVU_FORCE_STREAM_UPGRADE` | **0** | R692: 禁用 |
| 14 | `FALLBACK_HEALTH_THRESHOLD` | **0.10** | R708: 安全地板 |
| 15 | `NVU_PEER_FALLBACK_ENABLED` | **1** | 跨机互备 |

**四源验证通过**: compose=env=容器running=日志clean ✅

---

## 二、数据摘要

### 2.1 总览

| 窗口 | 总请求 | OK | ATE | SR |
|------|--------|-----|-----|-----|
| 6h | 382 | 337 | 45 | **88.2%** |
| 1h | 265 | 254 | 11 | **95.8%** |

- 趋势: 88.2% → 95.8% (↑7.6pp) — 系统正在自我恢复
- 1h avg duration (OK): dsv4p_nv f=38,716ms / t=135,291ms; glm5_2_nv f=20,427ms / t=67,110ms

### 2.2 Per-Model 1h

| 模型 | 总请求 | OK | ATE | SR | avg dur (no-fallback) | avg dur (fallback) |
|------|--------|-----|-----|-----|----------------------|---------------------|
| dsv4p_nv | 156 | 145 | 11 | 92.9% | 38,716ms | 135,291ms |
| glm5_2_nv | 106 | 105 | 0 | 99.1% | 20,427ms | — |
| kimi_nv | 5 | 5 | 0 | 100% | — | — |

### 2.3 Per-Model 6h

| 模型 | 总请求 | OK | ATE | SR |
|------|--------|-----|-----|-----|
| dsv4p_nv | 217 | 180 | 37 | 83.0% |
| glm5_2_nv | 158 | 151 | 7 | 95.6% |
| kimi_nv | 7 | 6 | 1 | 85.7% |

### 2.4 ATE诊断

**1h窗口 (11 ATE)**:
- 全部 double-tier (tiers_tried=2): dsv4p_nv→glm5_2_nv 双tier耗尽
- 全部 fallback_occurred=f, fallback_actually_attempted=f
- duration: 100,757ms ~ 228,635ms (≈BUDGET×2)
- 零 nv_tier_attempts 记录 (empty_200 fastbreak杀tier)
- 根因: **NVCF upstream 双function同时不可用** — 非网关配置可修

**6h窗口 (45 ATE)**: 31 double-tier + 14 single-tier (早期glm5_2 health=0.0期间遗留)

### 2.5 NVCFPexecTimeout 分布 (1h)

| tier | k0 | k1 | k2 | k3 | k4 | max_ms | buffer |
|------|----|----|----|----|----|--------|--------|
| dsv4p_nv | 6 | 3 | 3 | 3 | 3 | **60,823** | 5.2s ✓ |
| glm5_2_nv | 1 | 5 | 1 | 1 | 9 | **62,389** | 3.6s ✓ |

- 分布均匀 → 函数级超时, 非key级瓶颈
- buffer均 >3s (R751规则) → UPSTREAM=66非绑定

### 2.6 429 per-key分布 (1h, dsv4p_nv OK请求)

| k0 | k1 | k2 | k3 | k4 |
|----|----|----|----|----|
| with_429s=11, avg=0.71 | with_429s=6, avg=0.29 | with_429s=7, avg=0.33 | with_429s=6, avg=0.46 | with_429s=9, avg=0.58 |

- 分布较均匀, 非key-specific瓶颈 → FASTBREAK增加无益

### 2.7 empty_200 分布 (1h)

| tier | k0 | k1 | k2 | k3 | k4 | total |
|------|----|----|----|----|----|-------|
| dsv4p_nv | 6 | 9 | 5 | 6 | 10 | **34** |
| glm5_2_nv | 9 | 4 | 3 | 9 | 10 | **35** |

- 均匀分布跨所有key和tier → 系统性NVCF upstream issue
- EMPTY_200_FASTBREAK=3 正确平衡

### 2.8 Fallback 统计 (6h)

| 方向 | 总 | OK | SR |
|------|-----|-----|-----|
| dsv4p_nv → glm5_2_nv | 25 | 25 | **100%** |
| glm5_2_nv → dsv4p_nv | 66 | 66 | **100%** |

- 双向 fallback 100% SR, 健康度均为 1.0

### 2.9 最近日志

```
[04:24:51] NV-CYCLE tier=dsv4p_nv k1→429, cycling to next key
[04:24:51] NV-KEY tier=dsv4p_nv k2 → NVCF pexec DIRECT
[04:24:51] NV-CYCLE tier=dsv4p_nv k2→429, cycling to next key
[04:24:51] NV-KEY tier=dsv4p_nv k3 → NVCF pexec DIRECT
[04:24:54] NV-SUCCESS tier=dsv4p_nv k3 succeeded after 2 cycle attempts
[04:33:20] NV-REQ glm5_2_nv tier_chain=['glm5_2_nv','dsv4p_nv'] health=1.0/1.0
[04:33:23] NV-SUCCESS tier=glm5_2_nv k3 succeeded on first attempt
```

- 零ERROR/WARN
- 429 key cycling 正常工作
- 动态fallback链激活, 双向health=1.0

---

## 三、决策分析

| 参数 | 当前值 | 候选 | 数据支撑 | 决策 |
|------|--------|------|---------|------|
| FASTBREAK | 1 | — | floor; 1×66=66s << BUDGET=114; 429均匀分布 | ❌ floor |
| UPSTREAM_TIMEOUT | 66 | — | buffer dsv4p=5.2s, glm5_2=3.6s >3s; 95.8% SR | ❌ 无证据 |
| BUDGET | 114 | — | FASTBREAK=1下66<<114, 48s headroom充裕 | ❌ 无证据 |
| EMPTY_200_FASTBREAK | 3 | 2 | 均匀分布跨所有key/tier → 系统性upstream; 降低无收益 | ❌ 无数据支撑 |
| FORCE_STREAM_UPGRADE | 66 | — | ↔ UPSTREAM=66 对齐 ✅ | ❌ 已最优 |
| FALLBACK_HEALTH | 0.10 | — | 双向health=1.0, 阈值低无影响 | ❌ 已最优 |
| 节流参数 | 全部floor | — | CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0 | ❌ floor |

**最终决策: NOP — 零参数变更**

理由:
1. **趋势向好**: 6h SR 88.2% → 1h SR 95.8% (↑7.6pp), 系统正在自我恢复
2. **仅11 ATE/1h**: 全部为NVCF upstream双function耗尽 (double-tier, ~228s), 非网关配置可修
3. **Fallback 100% SR**: 双向正常工作, 健康度均为1.0
4. **FASTBREAK=1验证成功**: R768部署后, 1×66=66s << BUDGET=114, 充裕headroom支持fallback
5. **所有floor参数已触floor**: 无下调空间
6. **所有非floor参数无数据支撑变更**: NVCFPexecTimeout非绑定, 429均匀分布, empty_200系统性
7. **日志零错误**: 429 key cycling + cooldown机制正常工作

当前regime的剩余失败源为NVCF function-level upstream容量问题, 网关参数已最优化。

---

## 四、执行记录

**无变更执行**。未触发SSH/compose编辑/容器重启。

### 四源验证 (不变更, 确认状态)
- ✅ compose: `grep` 确认所有参数值与容器env一致
- ✅ env: `docker exec nv_gw env` 确认 FASTBREAK=1, UPSTREAM=66, BUDGET=114, FORCE_STREAM=66, EMPTY_200_FASTBREAK=3, FALLBACK_HEALTH=0.10
- ✅ 容器: `docker ps` running healthy
- ✅ 日志: `docker logs --tail 100` 零ERROR/WARN, 429 cycling + dynamic fallback正常

### 容器env确认
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=114
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=3
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_PEER_FALLBACK_TIMEOUT=45
FALLBACK_HEALTH_THRESHOLD=0.10
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NV_INTEGRATE_KEY_COOLDOWN_S=0
```

---

## 五、结论

R770 NOP完成。R768 FASTBREAK=1部署后总窗口: **95.8% SR (1h), 仅11 ATE(全部NVCF upstream不可用)**。系统处于配置最优状态, 所有可优化参数已触floor或无数据支撑变更。剩余失败源为NVCF function-level capacity, 非网关参数可修。

**当前最优配置**: UPSTREAM=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=3, FORCE_STREAM↔UPSTREAM=66对齐, FALLBACK_HEALTH=0.10安全地板, 节流参数全部floor。

**下一轮建议**: 若NVCF恢复且ATE归零 → 继续观察; 若ATE持续但为NVCF上游问题 → 继续NOP; 若出现新错误类型(429 surge/empty200 surge) → 考虑EMPTY_200_FASTBREAK调整; 若NVCFPexecTimeout max上升逼近UPSTREAM → 考虑UPSTREAM+2s。

**单参数少改多轮。铁律：只改HM1不改HM2。**

## ⏳ 轮到HM1优化HM2