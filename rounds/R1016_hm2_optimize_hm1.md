# R1016: HM2→HM1 — TIER_COOLDOWN_S 25→15 (-10s)

## 数据 (改前必有数据)

### 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 244 |
| 成功 | 220 |
| 失败 (ATE) | 24 |
| 成功率 | 90.16% |
| avg延迟 | 37,022ms |
| P50 | 22,639ms |
| P95 | 129,209ms |

### 6h 按模型
| 模型 | 总数 | 成功 | 失败 | SR% | P50 |
|------|------|------|------|-----|-----|
| glm5_2_nv | 130 | 124 | 6 | 95.38% | 20,773ms |
| dsv4p_nv | 71 | 59 | 12 | 83.10% | 36,608ms |
| kimi_nv | 24 | 24 | 0 | 100.00% | 7,414ms |
| minimax_m3_nv | 19 | 13 | 6 | 68.42% | 8,443ms |

### 2h 窗口
- 115 total, 102 OK, 13 ATE → 88.7% SR
- 所有错误: all_tiers_exhausted (14次, avg 113,053ms)
- 容器日志: empty_200 触发 GLOBAL-COOLDOWN 25s → 后续请求全部 2ms ATE

### nv_tier_attempts 6h
- dsv4p_nv IntegrateTimeout: 14次, 各key均匀分布 (k0:2, k1:5, k2:4, k3:2, k4:1)
- 1次 NVCFPexecRemoteDisconnected (k0, 9134ms)
- 1次 kimi_nv empty_200

### 根因分析
Empty_200 事件隔离 (37min间隔), 不集群。每次 empty_200 触发 `NV-GLOBAL-COOLDOWN` 25s, 期间所有请求立即 ATE (2ms, TIER-SKIP)。25s cooldown = 每个 empty_200 的事件后额外浪费 25s 窗口。FASTBREAK=1 已保护退化期间不浪费 keys, 长 cooldown 成为唯一瓶颈。

## 方案
- **参数**: TIER_COOLDOWN_S 25→15 (-10s)
- **理由**: empty_200 隔离事件, 15s cooldown 恢复更快, 减少 blast radius。KEY_COOLDOWN_S=25 ≥ TIER_COOLDOWN_S=15 保持不变量
- **风险**: 零 — 无 429 场景, empty_200 期间 FASTBREAK=1 阻止 key 浪费, cooldown 仅影响恢复速度

## 执行
```bash
sed -i '497s/"25"/"15"/' /opt/cc-infra/docker-compose.yml
cd /opt/cc-infra && docker compose up -d nv_gw
```
- 容器重启 ✓, health ok ✓
- docker exec nv_gw env: TIER_COOLDOWN_S=15 ✓

## 评判
- 更少报错: 每次 empty_200 后 cooldown 窗口 25→15s, 预计减少 40% 的 cooldown 期间 ATE
- 更快请求: ATE 从 2ms cooldown-reject 更快恢复 → 有效请求占比提升
- 更低延迟: 不直接影响延迟, 但减少 cooldown 期间 ATE 避免 agent fallback 到 ms_gw
- 稳定优先: KEY=25 ≥ TIER=15 保持不变量, FASTBREAK=1 不变

## 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2