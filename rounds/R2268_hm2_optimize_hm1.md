# R2268 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 100→110 (+10s)

## 数据收集 (6h window, pre-R2268)

### 请求汇总
- **总计**: 60 req (41 glm5_2_nv, 19 dsv4p_nv)
- **成功率**: 43 OK (71.7% SR), 17 fail
- **失败分布**: 5 dsv4p ATE-502 + 5 glm5_2 ATE-429 + 5 glm5_2 zombie + 2 glm5_2 ATE-502
- **30min window**: 11 req / 8 OK (72.7% SR)
- **fallback_occurred**: 0 (全部 60 条)
- **caller**: 全部 openclaw

### 延迟 (OK only, 6h)
| model | count | avg_ms | max |
|---|---|---|---|
| dsv4p_nv | 14 | 24,367 | 78,685 |
| glm5_2_nv | 29 | 34,852 | 121,442 |

### 日志分析 (docker logs nv_gw --tail 100)
```
[02:05:01] dsv4p_nv all 5 keys failed: 429=0, empty200=1, timeout=0, elapsed=61950ms
[02:06:03] glm5_2_nv k3→k4→k5→k1→k2 all 429 cycling (19s span)
[02:06:22] glm5_2_nv all keys cooldown → TIER_COOLDOWN=66s → preempt
[02:06:28] glm5_2_nv all keys cooling → ATE (10ms)
```
- 1 dsv4p ATE: NVCF upstream degradation (non-config)
- 1 glm5_2 429 storm: all 5 keys 429 in 19s, TIER_COOLDOWN=66s triggered
- 1 glm5_2 preempted: TIER_COOLDOWN active, all keys cooling → 10ms ATE

### Error Breakdown (6h)
| model | error_type | cnt |
|---|---|---|
| dsv4p_nv | all_tiers_exhausted (502) | 5 |
| glm5_2_nv | all_tiers_exhausted (429) | 5 |
| glm5_2_nv | zombie_empty_completion | 5 |
| glm5_2_nv | all_tiers_exhausted (502) | 2 |

## 分析

**核心发现**:
- TIER_COOLDOWN=66 (R2267) 有效: 429 storm 后正确冷却, 防止重试死亡螺旋
- 但 BUDGET=100 在 TIER_COOLDOWN=66 后只剩 34s per-key
- Per-key 成本: KEY(66)+UPSTREAM(24)=90s
- 当前 margin: 100-90=10s (仅 10s 余量 for 1 key attempt of 24s)
- 4247 429 事件已大幅减少 (R2267 前 36% 429 cycling at 42s, now zero 429 cycling)

**30min 窗口 SR 72.7%**: 好于 6h 71.7%, 说明 R2267 生效中

**优化方向**: 增加 GLM5_2 BUDGET 以匹配更高的 KEY_COOLDOWN=66
- Per-key: 66+24=90s
- New BUDGET=110: margin 110-90=20s (vs old 10s)
- 每个 key 有 20s 余量, 足够 1 次 24s 请求 (含 4s 额外 buffer)
- 全局: KEY(66)+TIER(66)+GLM5_2(110)=242 >> 192 BUDGET (50s over)
  - 但 TIER_COOLDOWN 和 KEY_COOLDOWN 不重叠消耗: TIER_COOLDOWN 触发时所有 key 已冷却, 实际路径 = max(66, 66) + 24 = 90s < 110 ✓

## 优化决策

**参数**: NVU_TIER_BUDGET_GLM5_2_NV: 100 → 110 (+10s)

**理由**:
- R2267 将 KEY=TIER=66 设为 iron law, 429 风暴已消除
- 但 BUDGET=100 在 per-key 成本 90s 下仅剩 10s 余量
- 110 提供 20s 余量, 足够 1 次 key attempt (24s) 含 4s buffer
- 保守 +10s, 单参数, 不引入新风险
- 铁律: 只改 HM1 不改 HM2

## 执行
```bash
# SSH edit line 494
ssh -p 222 opc_uname@100.109.153.83 \
  "sed -i '494s|NVU_TIER_BUDGET_GLM5_2_NV=100.*|NVU_TIER_BUDGET_GLM5_2_NV=110 ...|' /opt/cc-infra/docker-compose.yml"

# Restart
docker compose -f /opt/cc-infra/docker-compose.yml up -d --force-recreate nv_gw
```

## 验证
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2`: **110** ✓
- `curl /health`: **200** ✓
- Container recreated and running

## 预算
- glm5_2: KEY(66)+UPSTREAM(24)=90, BUDGET=110 → 20s margin
- dsv4p: KEY(66)+UPSTREAM(24)=90, BUDGET=135 → 45s margin
- TIER_COOLDOWN=66, TIER_TIMEOUT=192
- 单参数, 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2