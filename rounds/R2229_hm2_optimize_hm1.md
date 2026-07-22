# R2229 (HM2→HM1): KEY_COOLDOWN_S 32→30 (-2s)

## 数据收集 (6h窗口)
- **总计**: 37 req (全部 glm5_2_nv, 0 dsv4p_nv)
- **成功率**: 30 OK (81.1% SR), 7 fail
- **失败分布**: 7 zombie_empty_completion (glm5_2_nv, NVCF func-level)
- **ATE**: 0
- **peer-fallback**: 0 触发
- **日志**: 0 error/warn/panic

### 延迟分布 (OK only)
- glm5_2_nv: avg=14,164ms, min=3,463ms, max=47,903ms

### Key Cycling
- key_cycle_429s=1: 29/37 (78.4%), =2: 4/37, =3: 3/37, =4: 1/37
- 29/37 请求经历 1 次 key cycle → 首键常冷

### 僵尸详情 (glm5_2_nv only)
| ts (UTC) | duration_ms | key_cycle |
|---|---|---|
| 2026-07-22 00:33 | 5,675 | 1 |
| 2026-07-21 23:33 | 19,193 | 3 |
| 2026-07-21 23:03 | 8,920 | 1 |
| 2026-07-21 22:34 | 3,222 | 1 |
| 2026-07-21 21:33 | 8,777 | 1 |
| 2026-07-21 20:33 | 8,684 | 2 |
| 2026-07-21 19:05 | 3,622 | 1 |

## 优化决策

**参数**: KEY_COOLDOWN_S: 32 → 30 (-2s)

**模式**: 继续交替 KEY→KEY (跳过 TIER=0)。R2226 38→36, R2227 36→34, R2228 34→32, 四轮 SR 均持平 81.1%, 僵尸数不变 (7), 零 ATE, 零 peer-fb。KEY COOLDOWN 减小未引入任何新问题。继续渐进压缩。

**预算验证**: 
- glm5_2: KEY(30) + TIER(0) + GLM5_2_BUDGET(28) = 58 << 157 BUDGET (99s margin)
- dsv4p: KEY(30) + UPSTREAM(24) = 54 << 94 BUDGET (40s margin)
- PEER_FALLBACK_TIMEOUT(122) ≥ HM2_BUDGET+2 ✓

**理由**:
- 30s 让 5 keys 冷却再缩短 2s, per-request 周期缩短
- 29/37 (78.4%) req 经历 key cycle → 省 2s per request
- 僵尸是 NVCF func-level (pexec 返回 empty-200), 非 KEY COOLDOWN 所能修
- NVU_EMPTY_200_FASTBREAK=1 已开启, 僵尸最小化
- 低流量 (6.2 req/h) → key 池充分, 零 exhaustion risk
- 预算余量 99s 极充裕

## 执行

```bash
# 编辑 compose (行500)
sed -i '500s|KEY_COOLDOWN_S: "32"|KEY_COOLDOWN_S: "30"  # R2229 ...|' /opt/cc-infra/docker-compose.yml

# 重启容器
cd /opt/cc-infra && docker compose -f docker-compose.yml stop nv_gw && docker compose -f docker-compose.yml up -d nv_gw
```

## 验证
- `docker exec nv_gw env | grep KEY_COOLDOWN_S`: KEY_COOLDOWN_S=30 ✓
- TIER_COOLDOWN_S=0, NV_INTEGRATE_KEY_COOLDOWN_S=0 ✓
- `curl /health`: 200 ✓
- 容器 env 与 compose 一致, 无漂移

## 预算余量
- glm5_2: KEY(30) + TIER(0) + GLM5_2(28) = 58 << 157 BUDGET (99s)
- dsv4p: KEY(30) + UPSTREAM(24) = 54 << 94 BUDGET (40s)
- PEER_FALLBACK_TIMEOUT(122) ≥ HM2_BUDGET+2 ✓

## 铁律
单参数, 只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2