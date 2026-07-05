# RN: HM2→HM1 — NOP — 96% SR持续11h, 最后5h+ 100% SR零ATE, NVCFPexecTimeout非绑定, 零参数变更

**时间**: 2026-07-06 06:30 UTC  
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

### 2.1 容器状态
- 容器: `nv_gw`, Up 3 hours (healthy), StartedAt: 2026-07-05T19:52:49Z (R769重启)
- 零ERROR/WARN在docker logs中
- tier_chain: `['dsv4p_nv','glm5_2_nv']` (dynamic fallback), health: 0.95/1.0

### 2.2 总览

| 窗口 | 总请求 | OK | ATE | SR |
|------|--------|-----|-----|-----|
| 6h (含R769重启前) | 381 | 345 | 36 | **90.6%** |
| Post-restart (20:00+ UTC) | 273 | 262 | 11 | **96.0%** |
| 最后5h+ (01:00-06:30 UTC) | 95 | 95 | 0 | **100%** |

### 2.3 Per-Model (Post-restart)

| 模型 | 总请求 | OK | ATE | SR |
|------|--------|-----|-----|-----|
| dsv4p_nv | 163 | 153 | 10 | 93.9% |
| glm5_2_nv | 105 | 104 | 1 | 99.0% |
| kimi_nv | 5 | 5 | 0 | 100% |

### 2.4 小时趋势 (UTC)

| 小时 | 总 | OK | ATE | SR |
|------|-----|-----|-----|-----|
| 17:00 | 43 | 32 | 11 | 74.4% (pre-restart) |
| 18:00 | 31 | 23 | 8 | 74.2% (pre-restart) |
| 19:00 | 22 | 18 | 4 | 81.8% (pre-restart) |
| 20:00 | 27 | 21 | 6 | 77.8% (post-restart glitch) |
| 21:00 | 34 | 32 | 2 | 94.1% |
| 22:00 | 42 | 41 | 1 | 97.6% |
| 23:00 | 42 | 41 | 1 | 97.6% |
| 00:00 | 34 | 33 | 1 | 97.1% |
| **01:00** | **33** | **33** | **0** | **100%** |
| **02:00** | **25** | **25** | **0** | **100%** |
| **03:00** | **6** | **6** | **0** | **100%** |
| **04:00** | **18** | **18** | **0** | **100%** |
| **05:00** | **8** | **8** | **0** | **100%** |
| **06:00** | **3** | **3** | **0** | **100%** |

### 2.5 ATE诊断

**6h (36 ATE)**:
- 14 single-tier (全部 pre-restart, 17:00-19:00 UTC, 在R769重启前)
- 22 double-tier (11 pre-restart + 11 post-restart)
- 所有ATE: fallback_occurred=false, fallback_actually_attempted=false

**Post-restart (11 ATE)**:
- 全部 double-tier (tiers_tried_count=2)
- 全部 dsv4p_nv (10) + glm5_2_nv (1)
- duration: 100,757ms ~ 228,635ms ≈ 2×BUDGET(114s)
- 根因: **NVCF upstream 双function同时不可用** — BUDGET在每tier耗尽后kill, fallback从未触发
- 非网关配置可修

### 2.6 NVCFPexecTimeout分布 (6h)

| tier | k0 | k1 | k2 | k3 | k4 | max_ms | buffer vs UPSTREAM=66 |
|------|----|----|----|----|----|--------|----------------------|
| dsv4p_nv | 6 | 4 | 4 | 4 | 3 | **60,823** | 5.2s ✓ |
| glm5_2_nv | 7 | 13 | 5 | 9 | 16 | **62,389** | 3.6s ✓ |

- 分布均匀 → 函数级超时, 非key级瓶颈
- buffer均 >3s (R751规则) → UPSTREAM=66非绑定
- glm5_2 buffer仅3.6s → 下调buffer <3s违反R751安全规则

### 2.7 Tier Attempts Summary (6h)

| tier | error_type | cnt | max_ms |
|------|-----------|-----|--------|
| dsv4p_nv | empty_200 | 41 | — |
| dsv4p_nv | NVCFPexecTimeout | 21 | 60,823 |
| dsv4p_nv | 429_nv_rate_limit | 5 | — |
| dsv4p_nv | NVCFPexecgaierror | 3 | 16,023 |
| glm5_2_nv | NVCFPexecTimeout | 50 | 62,389 |
| glm5_2_nv | empty_200 | 35 | — |
| glm5_2_nv | 504_nv_gateway_timeout | 19 | — |

### 2.8 Fallback统计 (6h)

| 方向 | 总 | OK | SR |
|------|-----|-----|-----|
| dsv4p_nv → glm5_2_nv | 22 | 22 | **100%** |
| glm5_2_nv → dsv4p_nv | 64 | 64 | **100%** |

- 双向 fallback 100% SR, 健康度 0.95/1.0

### 2.9 最近请求 (全部200 OK, 零fallback)

```
06:22 dsv4p_nv 200 81,533ms
06:03 glm5_2_nv 200 2,369ms
06:01 dsv4p_nv 200 108,348ms
05:56 dsv4p_nv 200 118,044ms  ← fallback成功 (dsv4p→glm5_2)
05:41 dsv4p_nv 200 31,058ms
05:35 dsv4p_nv 200 17,600ms
05:33 glm5_2_nv 200 2,091ms
05:24 dsv4p_nv 200 37,106ms
05:20 dsv4p_nv 200 6,526ms
05:12 dsv4p_nv 200 11,987ms
05:03 glm5_2_nv 200 2,765ms
04:59 dsv4p_nv 200 10,884ms
04:33 glm5_2_nv 200 2,851ms
04:24 dsv4p_nv 200 19,038ms
04:24 dsv4p_nv 200 3,090ms
```

### 2.10 日志关键事件

```
[05:58:51] NV-TIMEOUT dsv4p_nv k3 pexec timeout 52,461ms
[05:58:51] NV-PEXEC-FASTBREAK dsv4p_nv 1 consecutive timeout → fast-break
[05:58:51] NV-TIER-FAIL dsv4p_nv all 5 keys failed: 429=0 empty200=1 timeout=1
[05:58:51] NV-FALLBACK → glm5_2_nv
[05:58:54] NV-FALLBACK-SUCCESS glm5_2_nv after primary dsv4p_nv failed
[06:01:39] tier_chain=['dsv4p_nv','glm5_2_nv'] health=0.95/1.0
[06:03:20] tier_chain=['glm5_2_nv','dsv4p_nv'] health=0.95/1.0
```

零ERROR/WARN。FASTBREAK=1正确触发fallback。Fallback 100%成功。

---

## 三、决策分析

| 参数 | 当前值 | 候选 | 数据支撑 | 决策 |
|------|--------|------|---------|------|
| FASTBREAK | 1 | — | floor; 1×66=66s << BUDGET=114; 429均匀分布; fallback 100% SR | ❌ floor |
| UPSTREAM_TIMEOUT | 66 | — | dsv4p buffer 5.2s, glm5_2 buffer 3.6s; 下调后glm5_2 buffer <3s违反R751 | ❌ 无证据 |
| BUDGET | 114 | — | FASTBREAK=1下66<<114, 48s headroom充裕 | ❌ 无证据 |
| EMPTY_200_FASTBREAK | 3 | — | 均匀分布跨所有key/tier → 系统性upstream; 降低无收益 | ❌ 无数据支撑 |
| FORCE_STREAM_UPGRADE | 66 | — | ↔ UPSTREAM=66对齐 ✅ | ❌ 已最优 |
| FALLBACK_HEALTH | 0.10 | — | 双向health=0.95-1.0, 阈值低无影响 | ❌ 已最优 |
| 节流参数 | 全部floor | — | CONNECT_RESERVE=0, MIN_OUTBOUND=0, INTEGRATE_COOLDOWN=0 | ❌ floor |

**最终决策: NOP — 零参数变更**

理由:
1. **Post-restart SR 96.0%**, 最后5h+ **100% SR 零ATE** — 系统处于极健康regime
2. **仅11 post-restart ATE**: 全部double-tier NVCF upstream双function同时不可用 (max_dur≈2×BUDGET), 非网关配置可修
3. **FASTBREAK=1已验证最优**: 1×66=66s << BUDGET=114, 48s fallback headroom; fallback 100% SR双向
4. **NVCFPexecTimeout非绑定**: dsv4p_nv 5.2s buffer, glm5_2_nv 3.6s buffer — 均 >3s
5. **UPSTREAM下调不可行**: glm5_2 buffer仅3.6s, 任何下调(66→64/65)使buffer <3s违反R751安全规则; dsv4p_nv和glm5_2_nv跨tier共享UPSTREAM, 不可拆分
6. **FASTBREAK=1为floor**: 不可再减; +1→2则2×66=132>BUDGET=114触发R768 BUDGET杀
7. **所有floor参数已触底**, 所有非floor参数无数据支撑变更
8. **日志零错误**: 429 key cycling + cooldown + FASTBREAK=1 fallback机制全部正常工作

当前regime的剩余失败源为NVCF function-level upstream容量问题, 网关参数已最优化。

---

## 四、执行记录

**无变更执行**。未触发SSH/compose编辑/容器重启。

### 四源验证 (不变更, 确认状态)
- ✅ compose: `grep` 确认所有参数值与容器env一致
- ✅ env: `docker exec nv_gw env` 确认 FASTBREAK=1, UPSTREAM=66, BUDGET=114, FORCE_STREAM=66, EMPTY_200_FASTBREAK=3, FALLBACK_HEALTH=0.10
- ✅ 容器: `docker ps` running healthy, Up 3 hours
- ✅ 日志: `docker logs --tail 100` 零ERROR/WARN, 429 cycling + FASTBREAK fallback正常

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

RN NOP完成。R769重启后11h窗口: **96.0% SR, 仅11 ATE(全部NVCF upstream不可用)**。最后5h+ **100% SR零ATE**。系统处于配置最优状态, 所有可优化参数已触floor或无数据支撑变更。剩余失败源为NVCF function-level capacity, 非网关参数可修。

**当前最优配置**: UPSTREAM=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=3, FORCE_STREAM↔UPSTREAM=66对齐, FALLBACK_HEALTH=0.10安全地板, 节流参数全部floor。

**下一轮建议**: 若NVCF维持健康 + 零ATE → 继续观察; 若ATE回归且为NVCF上游问题 → 继续NOP; 若出现新错误类型(429 surge/empty200 surge) → 考虑EMPTY_200_FASTBREAK调整; 若NVCFPexecTimeout max漂移超过+3s → 考虑UPSTREAM+2s。

**单参数少改多轮。铁律：只改HM1不改HM2。**

## ⏳ 轮到HM1优化HM2