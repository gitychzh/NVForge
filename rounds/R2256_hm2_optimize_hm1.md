# R2256: HM2→HM1 — NVU_TIER_BUDGET_GLM5_2_NV 56→72 (+16s)

**触发**: HM2 自提交 R2255 (symlink fix), false trigger, 脚本正确识别"不触发"但 cron 仍派遣。

## 6h 数据 (UTC 15:31-21:31)

| 指标 | 值 |
|------|-----|
| 总请求 | 59 |
| 成功 | 45 (76.27%) |
| 失败 | 14 |
| glm5_2_nv SR | 28/33 (84.85%) |
| dsv4p_nv SR | 17/26 (65.38%) |
| peer-fallback | 0 |

## 错误分布

| 模型 | 错误类型 | 数量 |
|------|---------|------|
| dsv4p_nv | ATE (all_tiers_exhausted) | 8 |
| glm5_2_nv | ATE (all_tiers_exhausted) | 4 |
| dsv4p_nv | zombie_empty_completion | 1 |
| glm5_2_nv | zombie_empty_completion | 1 |

## ATE 详情

全部 ATE 请求 `tiers_tried_count=1`，单次尝试即耗尽预算。
- dsv4p_nv: 持续时间 61-120s, BUDGET=120 刚好 5 键×24s=120s 零余量
- glm5_2_nv: 持续时间 137-163s, BUDGET=56 仅 2.3 键尝试

## 日志

glm5_2_nv 严重 429 键轮转 (所有 5 键)，KEY_COOLDOWN_S=0 允许即时重试致所有键同时冷却。

## 优化

**修改**: `NVU_TIER_BUDGET_GLM5_2_NV` 56→72 (+16s)

**依据**: BUDGET=56=UPSTREAM(24)+32，仅 2.3 键尝试。72=24+48 支持 3 键尝试 (48/24=2 额外键)。5 键全 429 时无法穿透，但给非全 429 场景多 1 键余量。

**约束**: KEY(0)+TIER(0)+GLM5_2(72)=72≪157(85s margin)。dsv4p_nv 保持 BUDGET=120 不变。

## 验证

- `docker exec nv_gw printenv NVU_TIER_BUDGET_GLM5_2_NV` → `72` ✓
- `KEY_COOLDOWN_S=0` ✓
- `curl localhost:40006/health` → `{"status":"ok"}` ✓

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**
## ⏳ 轮到HM1优化HM2
