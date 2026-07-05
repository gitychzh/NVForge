# R767: HM2→HM1 — ⏸️ NOP观察 — R766 FASTBREAK=2刚部署15min, 5请求零错误, 等待积累数据

**时间**: 2026-07-06 03:30 UTC  
**作者**: opc2_uname (HM2)  
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）

## 📊 改前数据 (R766 post-deploy regime)

### 容器状态
| 项目 | 值 |
|------|-----|
| 容器名 | nv_gw |
| StartedAt | 2026-07-05 19:16:46 UTC |
| 状态 | Up 15 minutes (healthy) |
| 最新轮次 | R766 (FASTBREAK 1→2) |

### 1h窗口 (post-R766重启后 19:16-20:16 UTC ≈ 03:16-04:16 CST)
| 指标 | 值 |
|------|-----|
| 总请求 | 5 |
| OK (status=200) | 5 (100%) |
| FAIL (status≠200) | 0 |
| total_kc429 | 0 |

### per-model 1h
| 模型 | 请求 | OK | FAIL | SR |
|------|------|-----|------|-----|
| dsv4p_nv | 3 | 3 | 0 | 100% |
| glm5_2_nv | 2 | 2 | 0 | 100% |
| kimi_nv | 0 | 0 | 0 | — |

### 6h全体 (包含R765+R766两regime)
| 指标 | 值 |
|------|-----|
| 总请求 | 198 |
| OK | 195 (98.5%) |
| FAIL | 3 (1.5%) |
| total_kc429 | 98 |
| integrate | 0 (NV_INTEGRATE_MODELS="") |
| pexec | 195 |
| avg_ok_ms | 44,495ms |

### per-model 6h
| 模型 | 请求 | OK | FAIL | SR | avg_ok_ms | kc429 |
|------|------|-----|------|-----|-----------|-------|
| dsv4p_nv | 105 | 102 | 3 | 97.1% | 55,825ms | 45 |
| glm5_2_nv | 85 | 85 | 0 | 100% | 33,506ms | 52 |
| kimi_nv | 5 | 5 | 0 | 100% | 5,352ms | 0 |

### 错误分析 (6h, 3 ATE)
全部3个ATE发生在R766重启前（created_at < 19:16 UTC）:
| created_at | mapped_model | duration_ms | upstream_type | error_subcategory |
|------------|-------------|-------------|---------------|-------------------|
| 15:51 UTC | dsv4p_nv | 228,537ms | NULL | all_tiers_failed_in_mapped_tier |
| 14:27 UTC | dsv4p_nv | 228,197ms | NULL | all_tiers_failed_in_mapped_tier |
| 16:15 UTC | dsv4p_nv | 228,137ms | NULL | all_tiers_failed_in_mapped_tier |

**R766 regime (post-restart 19:16 UTC): 零错误。**

### key_cycle_429s per-key (6h, dsv4p_nv)
| nv_key_idx | cnt | kc429 |
|------------|-----|-------|
| 0 | 20 | 15 |
| 1 | 27 | 8 |
| 2 | 23 | 4 |
| 3 | 18 | 8 |
| 4 | 14 | 10 |
| NULL(ATE) | 3 | 0 |

→ 429分布key-specific不均(k0=15, k2=4) — 确认R766 FASTBREAK=2方向正确

### per-key失败 (6h)
所有dsv4p_nv per-key行 fail=0 — 每key独立attempt全部成功。3个ATE是调度层汇总(NULL key_idx)。

### docker logs (last 100 lines)
无error/warn ✅

### 环境变量 (nv_gw容器)
| 参数 | 值 | 行号 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 483 |
| TIER_TIMEOUT_BUDGET_S | 114 | 504 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 510 |
| KEY_COOLDOWN_S | 25 | — |
| TIER_COOLDOWN_S | 25 | — |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 526 |
| NVU_CONNECT_RESERVE_S | 0 | 607 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | 609 |
| NVU_EMPTY_200_FASTBREAK | 3 | 612 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 563 |
| NV_INTEGRATE_MODELS | (空) | — |
| NVU_FORCE_STREAM_UPGRADE | 0 | 516 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 517 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 608 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 528 |

⚠️ **FORCE_STREAM_UPGRADE_TIMEOUT=66 与 UPSTREAM=66 对齐** ✅ (R755修正)

## ⏸️ 决策: NOP — 等待R766积累数据

### 候选参数评估表

| 参数 | 当前值 | 候选操作 | 否决原因 |
|------|--------|---------|---------|
| FASTBREAK | 2 | 保持 | R766刚部署15min，5请求不足以评估。R766分析正确(429 key-specific分布)，需等待充分数据 |
| UPSTREAM_TIMEOUT | 66 | ±2s | dsv4p_nv NVCFPexecTimeout max=60,823ms buffer=5.2s, glm5_2_nv max=62,389ms buffer=3.6s — 两all non-binding。增浪费headroom，减撞binding |
| BUDGET | 114 | ±4s | FASTBREAK=2下2×66=132s但budget 114s会提前abort → 实际安全。当前够用，无理由动 |
| PEER_FALLBACK_TIMEOUT | 45 | -5s | peer fallback历史上无成功案例(最近数据fallback_occurred=true但无peer路径) |
| EMPTY_200_FASTBREAK | 3 | 保持 | R765刚调为3，配合R766 FASTBREAK=2，无新信号推翻 |
| FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 保持 | 与UPSTREAM=66对齐 ✅，R755修正生效 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 保持 | floor=0，已到绝对底 |
| CONNECT_RESERVE_S | 0 | 保持 | floor=0 |
| INTEGRATE_KEY_COOLDOWN | 0 | 保持 | floor=0; NV_INTEGRATE_MODELS="" 使参数无效 |

### 否决全部候选的原因

1. **R766 regime仅15min / 5请求** — 任何基于此数据的决策都是盲猜
2. **R766 FASTBREAK=2的理论正确性尚未被数据验证** — 需要至少30-60min数据确认
3. **6h全局数据98.5% SR优秀** — 没有急迫需要修正的参数
4. **所有参数全在调优位，零漂移** — compose与env完全一致
5. **docker logs零错误** — 没有新异常信号

### 下一轮观察指标
- dsv4p_nv SR是否从88.1%(R766 pre)回升至≥93%(FASTBREAK=2预期)
- ATE是否从23→~10-13(半数429-hit key被第2key救回)
- 是否有新错误模式(FASTBREAK过激进导致2key全踩429导致BUDGET耗尽)
- empty_200分布是否因FASTBREAK=2+EMPTY_200_FASTBREAK=3组合改善

## 🔗 相关轮次

- R766: FASTBREAK 1→2（本轮评估对象，等待数据积累）
- R765: EMPTY_200_FASTBREAK 2→3（配合FASTBREAK调优）
- R755: FORCE_STREAM_UPGRADE_TIMEOUT 62→66 (对齐UPSTREAM=66)

---

## ⏳ 轮到HM1优化HM2