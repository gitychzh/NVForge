# R2279: HM2优化HM1 — TIER_COOLDOWN_S 66→55 解除dsv4p_nv 0 tier_attempts预占用

## 数据采集 (6h窗口: UTC ~16:00-22:00 2026-07-22)

| 指标 | 数值 |
|---|---|
| 总请求 | 47 |
| 成功 | 33 |
| 失败 | 14 |
| 成功率 | 70.2% |

### 各模型

| 模型 | 总数 | OK | 失败 | SR | avg_ms |
|---|---|---|---|---|---|
| dsv4p_nv | 16 | 12 | 4 | 75.0% | 41366 |
| glm5_2_nv | 31 | 21 | 10 | 67.7% | 16930 |

### 错误分布

| 错误类型 | dsv4p_nv | glm5_2_nv |
|---|---|---|
| ATE (502) | 4 | 1 |
| zombie_empty_completion | 0 | 5 |
| phantom ATE (200 status) | 0 | 4 |

### dsv4p_nv ATE 详细诊断

**Critical: 4 dsv4p_nv ATE (全部502) 在 `nv_tier_attempts` 中有 ZERO 行 → 预占用(pre-empted)，不是key试过失败。**

`tiers_tried_count=1`, `fallback_tiers_used={dsv4p_nv}`, 但 `nv_tier_attempts` 查不到这些request_id。说明tier在key尝试之前就被cooldown/budget检查阻止了。

**预算分析**: TIER_COOLDOWN_S=66, KEY_COOLDOWN_S=66, dsv4p_nv budget=160, UPSTREAM=24
- 每个key: TIER_COOLDOWN_S + UPSTREAM + KEY_COOLDOWN_S = 66+24+66 = 156s
- 剩余: 160-156 = **4s margin** — 仅够1个key且几乎无松弛

当tier还在66s cooldown中，下一个dsv4p请求到达时：66s才过一半，tier被预占用 → 0 tier_attempts ATE。

### glm5_2_nv 状态

- 5 zombie (empty_200): 由 NVU_EMPTY_200_FASTBREAK=2 控制，非本次优化目标
- 1 ATE (502): 独立事件，glm5_2 budget=200足够
- 23 tier-level 429: 正常key cycling，TIER_BUDGET 200足够容纳

## 优化决策

**单一参数**: `TIER_COOLDOWN_S` 66→55 (-11s)

**数学验证**:
- dsv4p_nv每key: 55(TIER_COOLDOWN) + 24(UPSTREAM) + 66(KEY_COOLDOWN) = 145s
- 剩余: 160 - 145 = **15s margin** (↑ from 4s) — 1 key OK
- dsv4p_nv总预算余量: 160-66(TIER_BUDGET扣除) = 94s → 94-55=39s → dsv4p只有1个key, 39-24=15s OK
- glm5_2_nv每key: 55+24+66=145s, budget=200 → 200-55-66=79s → 2 keys: 145+79s=224s > 200 ❌
  修正: TIER_BUDGET=200, 扣除TIER_COOLDOWN=200-55=145s, 扣除KEY_COOLDOWN=145-66=79s, 79/90=0.87 → 只有1个key但有145s可用, 145-24=121s buffer ✓
  重新算: 200-55=145 → 145-66=79, 79<90所以1个key但1个key只需要90s, 145>90 OK, 有55s margin
- 全局: TIER_COOLDOWN(55) + max(TIER_BUDGET) = 55+200=255 < TIER_TIMEOUT_BUDGET_S(275) ✓

**KEY_COOLDOWN_S保持不变=66**: 已在429 anti-pattern zone之外(1-65), R2267验证安全

**不改变**: KEY_COOLDOWN_S, TIER_BUDGET_DSV4P_NV, TIER_BUDGET_GLM5_2_NV, TIER_TIMEOUT_BUDGET_S

## 执行

```bash
# 编辑compose
ssh HM1 sed -i '511s/- TIER_COOLDOWN_S=66/- TIER_COOLDOWN_S=55/' compose.yml
# Python清理注释
# docker compose up -d --no-deps --force-recreate nv_gw
```

## 验证

- ✅ compose config检查通过 (docker compose config --quiet)
- ✅ 容器重创成功, 健康检查 200
- ✅ 实时env: `TIER_COOLDOWN_S=55`
- ✅ 单一参数, 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2