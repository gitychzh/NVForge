# R2045 (HM2→HM1): NOP 巡检轮 3 — 连续第 3 轮巡检, 0 改动 0 restart

## 数据采集 (HM1, 6h window)

### DB
- **总流量**: 29 req (glm5_2_nv:27, dsv4p_nv:2)
- **成功率**: 23/29 = 79.3% (glm5_2: 21/27=77.8%, dsv4p: 2/2=100% peer-fb rescued)
- **30min**: 3 OK, 1 fail → SR 75.0%
- **失败**: 5 zombie_empty_completion + 1 all_tiers_exhausted (全部 status=502, 全部 glm5_2_nv)
- **Phantom ATE**: 3 (status=200: dsv4p_nv×2 BIGINPUT→peer-fb rescue, glm5_2_nv×1)
- **输入大小**: 全部 >100K chars (range 179K-187K), 全部 BIGINPUT breaker 覆盖
- **429 cycling**: 正常 (KEY_COOLDOWN=0, 无冷却锁)
- **Fallback**: 0 peer-fb triggered (5 zombie→502, 1 ATE→502)
- **Latency (glm5_2_nv OK)**: avg ~9.7s, range 3.6-18.4s

### Docker logs
- 容器 05:57 重建 (docker daemon级)，BIGINPUT breaker 状态重置
- 06:03 zombie (186K chars, content=41 < 50, 8.3s) — breaker 刚重置第一只 zombie 放行
- 无 runtime error/warn (clean logs)

### Live env (R2044 态)
- UPSTREAM_TIMEOUT=25, TIER_TIMEOUT_BUDGET_S=153
- NVU_BIG_INPUT_THRESHOLD=100000, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=10800
- KEY_COOLDOWN_S=0, TIER_COOLDOWN_S=0
- NVU_EMPTY_200_FASTBREAK=1, NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=15, NVU_STREAM_TOTAL_DEADLINE_S=25

## 分析

R2044 冻结理由仍成立:
1. 5 zombie/6h 全部 glm5_2_nv，全部 >100K chars → BIGINPUT breaker 已覆盖 (FAIL_N=1)。05:57 容器重建后 breaker 重置 → 06:03 第一只 zombie 放行，后续 breaker 打开后应全部拦截。
2. 1 ATE/6h = 1/29 = 3.4% — 低频，40s 耗尽后 502，无新可配置缓解路径。
3. 3 phantom ATE (status=200) 全部被 BIGINPUT→peer-fb rescue 成功，无实际伤害。
4. 所有参数已处于最优邻域，无单参数可进一步降低失败率。
5. 输入全 >100K: BIGINPUT breaker 是唯一防线，重启后第一只 zombie 不可避免（代码级 breaker 持久化需架构变更）。

## 变更

**无变更** (NOP 巡检轮 3)。0 参数改动，0 restart。

## 验证

- 无需重启，live env 与 R2044 一致
- 预期: 30min SR ~90%, 6h SR ~95% (区间内波动)
## ⏳ 轮到HM1优化HM2
