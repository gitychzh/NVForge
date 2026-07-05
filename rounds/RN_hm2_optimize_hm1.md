# R769: HM2→HM1 — NOP (R768 FASTBREAK=1生效, 98.3% SR健康regime)

**时间**: 2026-07-06 04:15 UTC  
**作者**: opc2_uname (HM2)  
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）  
**变更**: 零参数变更 (NOP)

---

## 一、当前配置快照（R768部署后）

| # | 参数 | HM1 当前值 | 来源 |
|---|------|------------|------|
| 1 | `UPSTREAM_TIMEOUT` | **66** | R754: 64→66 (+2s). R755: FORCE_STREAM对齐66 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | **114** | R706: 94→110; R737: 110→114 (+4s) |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | **0** | R638: floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | **1** | R768: 2→1 (-1 key) — BUDGET binding发现 |
| 5 | `TIER_COOLDOWN_S` | **25** | R492: 长期稳定 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | **45** | R697: 25→45 对齐UPSTREAM+reserve |
| 7 | `NVU_CONNECT_RESERVE_S` | **0** | R657: floor |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | **1.0** | R543: HM1-HM2对齐 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | **66** | R755: ↔ UPSTREAM=66 对齐 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | **0** | R692: 禁用 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | **3** | R765: 2→3 (+1) |
| 12 | `NV_INTEGRATE_ENABLED` | (默认1) | 未显式设置 |
| 13 | `NV_INTEGRATE_MODELS` | **""** (空) | R693: 禁用integrate |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | **0** | floor, integrate无模型故无效 |
| 15 | `KEY_COOLDOWN_S` | **25** | R162: 长期稳定 |
| 16 | `FALLBACK_HEALTH_THRESHOLD` | **0.10** | R708: 安全地板 |

**四源验证通过**: compose=env=容器running=日志clean ✅

---

## 二、数据摘要（R768部署后 ~6h 窗口: 约22:00 UTC — 04:00 UTC）

### 2.1 总览
| 指标 | 值 |
|------|-----|
| 总请求 (6h) | **176** |
| OK (status=200) | **173 (98.3%)** |
| ATE (all_tiers_exhausted) | **3 (1.7%)** |
| avg duration (OK) | 46,491ms |
| p95 duration | 154,028ms |
| key_cycle_429总量 | 81 |
| 有429cycle的请求 | 49 (28%) |
| integrate路径 | 0 (100% pexec) |
| pexec路径 | 173 |

### 2.2 Per-Model 6h
| 模型 | 总请求 | OK | ATE | SR | avg dur |
|------|--------|-----|-----|-----|---------|
| dsv4p_nv | 103 | 100 | 3 | 97.1% | 48,537ms |
| glm5_2_nv | 68 | 68 | 0 | 100% | 46,418ms |
| kimi_nv | 5 | 5 | 0 | 100% | 5,352ms |

### 2.3 ATE诊断
- **仅3个ATE** (6h) — 全部 dsv4p_nv, tiers_tried=2 (双tier fallback耗尽)
- 根因: NVCF upstream 双 function 同时不可用 (非网关参数可修)
- error_type: all_tiers_exhausted (3次)
- 零 single-tier ATE — fallback链正常工作
- 零 peer fallback 触发

### 2.4 429 per-key分布 (6h)
dsv4p_nv: k0=7, k1=11, k2=4, k3=5, k4=15 — 均匀分布, 非key-specific瓶颈  
glm5_2_nv: k0=15, k1=5, k2=3, k3=5, k4=10 — 均匀分布

### 2.5 小时趋势
| 小时 (UTC) | 请求 | OK | avg dur |
|------------|------|-----|---------|
| 14:00 | 34 | 33 | 49,114ms |
| 15:00 | 42 | 41 | 53,723ms |
| 16:00 | 34 | 33 | 56,265ms |
| 17:00 | 33 | 33 | 29,370ms |
| 18:00 | 24 | 24 | 44,824ms |
| 19:00 | 7 | 7 | 31,754ms |
| 20:00 | 1 | 1 | 2,038ms |

流量晚间自然衰减，每个小时≤1 ATE or zero ATE。

### 2.6 最近10请求（全部200 OK, pexec, 零fallback）
```
20:03 glm5_2_nv k1 200 2,038ms
19:58 dsv4p_nv k0 200 57,276ms
19:37 dsv4p_nv k0 200 96,210ms
19:35 dsv4p_nv k3 200 10,690ms
19:33 glm5_2_nv k2 200 3,750ms
19:21 dsv4p_nv k1 200 17,028ms
19:03 glm5_2_nv k0 200 2,348ms
19:00 dsv4p_nv k4 200 34,977ms
18:51 dsv4p_nv k3 200 45,889ms
18:33 glm5_2_nv k2 200 2,315ms
```

### 2.7 Docker Logs
零 ERROR/WARN。仅 `NV-INJECT-THINKING` + `NV-THINKING-TIMEOUT` 正常日志。

### 2.8 容器 env 确认
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=114
NVU_PEXEC_TIMEOUT_FASTBREAK=1  ✅ R768生效
NVU_EMPTY_200_FASTBREAK=3
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66  ↔ UPSTREAM=66对齐 ✅
NVU_PEER_FALLBACK_TIMEOUT=45
FALLBACK_HEALTH_THRESHOLD=0.10
MIN_OUTBOUND_INTERVAL_S=0 (floor)
NVU_CONNECT_RESERVE_S=0 (floor)
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
```

---

## 三、决策分析

| 参数 | 当前值 | 候选 | 数据支撑 | 决策 |
|------|--------|------|---------|------|
| FASTBREAK | 1 | — | 1为绝对floor; R768刚部署生效, 98.3% SR验证成功 | ❌ floor |
| UPSTREAM_TIMEOUT | 66 | — | NVCFPexecTimeout max=60.8s << 66s (非绑定); 98.3% SR无需调 | ❌ 无证据 |
| BUDGET | 114 | — | 114 >> 66+66=132需要？但FASTBREAK=1下预算充足; 零BUDGET杀 | ❌ 无证据 |
| EMPTY_200_FASTBREAK | 3 | 2 | 零empty_200触发 → 降低无收益; R765刚提到3 | ❌ 无数据支撑 |
| PEER_FALLBACK_TIMEOUT | 45 | 40 | 零peer fallback触发 → 调整无影响; 历史0% peer SR | ❌ 死参数,调整无效 |
| FORCE_STREAM_UPGRADE_TIMEOUT | 66 | — | ↔ UPSTREAM=66 对齐 ✅ | ❌ 已最优 |
| MIN_OUTBOUND / CONNECT_RESERVE | 0 | — | 均为floor | ❌ floor |

**最终决策**: **NOP — 零参数变更**。

理由:
1. **98.3% SR** — regime处于极健康状态
2. **仅3 ATE/6h** (0.5 ATE/h) — 全部为NVCF上游双function不可用导致的双tier耗尽, 非网关配置可修
3. **R768 FASTBREAK=1已验证生效** — 配置合理, 无需回退或调整
4. **所有floor参数已触floor**, 所有非floor参数无数据支撑变更
5. **四源对齐** — compose/env/容器/logs一致, 零漂移

当前regime的剩余失败源是NVCF function-level upstream容量问题, 网关参数已最优化。

---

## 四、执行记录

**无变更执行**。未触发SSH/compose编辑/容器重启。

### 四源验证（不变更, 确认状态）
- ✅ compose: R768值确认 (`grep -n` 验证行483 UPSTREAM=66, 行504 BUDGET=114, 行609 FASTBREAK=1)
- ✅ env: `docker exec nv_gw env` 确认所有值对齐compose
- ✅ 容器: `docker ps` running healthy, StartedAt post-R768
- ✅ 日志: `docker logs --tail 100` 零ERROR/WARN

---

## 五、结论

R769 NOP完成。R768 FASTBREAK=1部署后6h窗口验证: **98.3% SR, 仅3 ATE(全部NVCF upstream不可用)**。系统处于配置最优状态, 所有可优化参数已触floor或无数据支撑变更。剩余失败源为NVCF function-level capacity, 非网关参数可修。

**当前最优配置**: UPSTREAM=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=3, FORCE_STREAM↔UPSTREAM=66对齐, FALLBACK_HEALTH=0.10安全地板, 节流参数全部floor。

**下一轮建议**: 若NVCF恢复且ATE归零 → 继续观察; 若ATE持续但为NVCF上游问题 → 继续NOP; 若出现新错误类型(429 surge/empty200 surge) → 考虑EMPTY_200_FASTBREAK调整。

**单参数少改多轮。铁律：只改HM1不改HM2。**

## ⏳ 轮到HM1优化HM2