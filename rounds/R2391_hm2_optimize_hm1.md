# R2391: HM2 → HM1 — dsv4p_nv PEXEC_TIMEOUT_FASTBREAK 优化

## 本轮数据

| 指标 | 2h | 6h | 24h |
|------|----|----|-----|
| **总请求** | 21 | 73 | 268 |
| **成功率** | 81.0% (17/21) | 67.1% (49/73) | 62.0% (166/268) |
| **kimi_nv SR** | 100% (10/10) | 74.3% (26/35) | 76.6% (108/141) |
| **dsv4p_nv SR** | 33.3% (1/3) | 10.0% (1/10) | 47.4% (9/19) |
| **glm5_2_nv SR** | 75.0% (6/8) | 78.6% (22/28) | 67.6% (73/108) |
| **kimi_nv 错误** | 0 (null) | 6 ATE, 2 zombie, 1 no_content | 23 ATE, 5 empty_200, etc |
| **dsv4p_nv 错误** | 2 ATE | 9 ATE, 1 zombie | 10 ATE, 1 zombie, etc |
| **key_cycle_429s** | 0 | 0 | 0 |
| **空完成体** | 1 (dsv4p) | 0 | 1 (dsv4p) |

## 根因分析

- **dsv4p_nv 处于低成功状态**：24h 内仅 47.4% 的成功率，远低于 kimi_nv 和 glm5_2_nv。
- **原因分析**：`tiers_tried_count` 为 1 且所有请求均为 ATE，这表明所有 5 个键都在初始预算检查期间内被耗尽。
- **NV_INTEGRATE_MODELS=空**：dsv4p_nv 完全使用直接 pexec，需要更高的容错能力。
- **PEXEC_TIMEOUT_FASTBREAK=5**：当前值 5 在 `tiers_tried_count` 受限时仍然启用，导致预算被消耗。
- **没有观察到 PEXEC_FASTBREAK 或 INTEGRATE_FASTBREAK**：在 50000 行日志中完全不存在，说明当前设置没有生成任何 Fastbreak。

## 优化计划

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 5 | 6 | dsv4p_nv 24h 中 9 个 ATE 均只尝试了 1 个键，PEXEC_TIMEOUT_FASTBREAK 为 5（等于键数），导致所有键尝试后未给 Fastbreak 留下空间。增加到 6 允许在 5 个键全 pexec 超时后仍触发 Fastbreak，为后续键保留预算。极小改动，不会负面影响其他模型。|

## 铁律声明
- **只改HM1 配置，绝不动HM2 本地。**
- **单参数微调，多轮积累，观察稳定后再扩。**

## 实施
1. 编辑 `/opt/cc-infra/docker-compose.yml` 的 `nv_gw` 环境变量 `NVU_PEXEC_TIMEOUT_FASTBREAK` 为 6。
2. `docker compose up -d nv_gw` 重启生效。

## ⏳ 轮到HM1优化HM2
