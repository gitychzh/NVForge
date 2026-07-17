# R1731 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 145→155 (+10s)

> **轮次**: R1731 | **日期**: 2026-07-18 06:25 UTC | **操作者**: HM2 (opc2_uname)
> **决策**: BUDGET 145→155, dsv4p peer-fb gap 增量修复第一步
> **铁律**: 只改HM1不改HM2

## 数据收集 (6h窗口, 2026-07-18 ~00:00–06:00 UTC)

### 成功率

| 指标 | 值 |
|------|-----|
| 总请求 | 53 |
| 成功 (200) | 45 |
| 失败 (502) | 8 |
| **成功率** | **84.9%** |
| 0 fallback | 53/53 |

### 错误分布

| 错误类型 | 模型 | 数量 | 平均延迟 | 备注 |
|---------|------|------|---------|------|
| zombie_empty_completion | glm5_2_nv | 6 | 8,149ms | 全 >250K chars, BIG_INPUT breaker, tiers_tried=1 |
| all_tiers_exhausted | dsv4p_nv | 2 | 69,524ms | 502, 无救援 (peer-fb skipped), 无 fallback |
| phantom ATE | dsv4p_nv | 3 | — | error_type=ATE 但 status=200, 不计入失败 |

### 延迟 (OK路径)

| 指标 | 值 |
|------|-----|
| avg | 10,743ms |
| p50 | 8,899ms |
| p95 | 19,271ms |
| max | 46,061ms |

### 容器状态
- nv_gw: 零漂移, compose=container 全一致 ✓
- key_cycle_429s: 正常 (87.3% single-key, IP级无429)
- 0 fallback, 0 peer-fb usage

## 问题: dsv4p peer-fb budget-cap gap

R1730 identified: dsv4p ATE实测70s + PEER_FALLBACK_TIMEOUT=125s = 195s > BUDGET=145 → peer-fb被cap跳过.
2 dsv4p ATE 均无救援 (peer-fb skipped + ms_gw relay broken R1609), 100% 失败.

```
当前: 145 - 70(ATE) = 75s remaining < 125s(PEER_FALLBACK_TIMEOUT) → skip
目标: 195 - 70(ATE) = 125s remaining ≥ 125s → enable
路径: 145→155→165→175→185→195 (5轮, 每轮+10s)
```

## 修改

```
TIER_TIMEOUT_BUDGET_S: 145 → 155 (+10s)
```

- 增量第一步, 少改多轮
- dsv4p peer-fb: 155−70=85s < 125s → 仍被跳过, 但向195目标前进
- glm5_2 BIG_INPUT: ~0s(快拒) + 125s = 125s < 155 ✓ (但BIG_INPUT触发zombie非ATE, 目前不触发peer-fb)
- OK路径: p50=8.9s, p95=19.3s << 155 ✓ 零影响
- 单参数, 铁律: 只改HM1不改HM2

## 验证

- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S`: 155 ✓
- `curl /health`: status=ok ✓
- 无容器漂移: compose=container 全一致 ✓
- 所有调优参数 compose=container 匹配 ✓

## 评判

- 更少报错: → (BUDGET增加不增加新报错, 为dsv4p peer-fb铺路)
- 更快请求: → (OK路径不受影响, p50=8.9s << 155)
- 超低延迟: → (zombie路径不受影响, BIG_INPUT_COOLDOWN=5400继续生效)
- 稳定优先: √ (增量渐进, 单参数+10s, 多轮积累)
## ⏳ 轮到HM1优化HM2
