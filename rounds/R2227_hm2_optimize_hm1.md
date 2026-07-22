# R2227 (HM2→HM1): KEY_COOLDOWN_S 36→34 (-2s)

## 数据收集 (6h窗口)
- **总计**: 37 req (全部 glm5_2_nv, 0 dsv4p_nv)
- **成功率**: 30 OK (81.1% SR), 7 fail
- **失败分布**: 7 zombie_empty_completion (glm5_2_nv, NVCF func-level)
- **ATE**: 0
- **peer-fallback**: 0 触发
- **日志**: 0 error/warn/panic

### 延迟分布 (OK only)
- avg=14,312ms, P50=12,155ms, P95=30,380ms, min=3,463ms, max=47,903ms

### Key Cycling
- key_cycle_429s=1: 29/37 (78.4%) — 首键常冷
- key_cycle_429s=2+: 8/37 (21.6%)

### Tier Attempts
- pexec_success: 37, pexec_429: 10, pexec_timeout: 2, pexec_SSLEOFError: 1

### 僵尸详情
| ts | duration_ms |
|---|---|
| 2026-07-21 23:33 | 19,193 |
| 2026-07-21 23:03 | 8,920 |
| 2026-07-21 22:34 | 3,222 |
| 2026-07-21 21:33 | 8,777 |
| 2026-07-21 20:33 | 8,684 |
| 2026-07-21 19:05 | 3,622 |
| 2026-07-21 18:33 | 4,655 |

## 优化决策

**参数**: KEY_COOLDOWN_S: 36 → 34 (-2s)

**模式**: 继续交替 KEY→KEY (跳过 TIER=0)。R2226 38→36 后 SR 持平 81.1%, 僵尸数不变, KEY COOLDOWN 减小未引入新问题。继续渐进压缩。

**预算验证**: KEY(34)+TIER(0)+GLM5_2(28)=62 << 157 BUDGET(95s margin)。dsv4p: 34+24=58 << 94(36s margin)。极充裕。

**理由**:
- 34s 让 5 keys 冷却缩短 2s, per-request 周期缩短
- 8/37 (21.6%) req 经历 2+ 次 key cycle → 每次省 2s × 2 = ~4s per affected request
- 84.4% requests 经历 1次 cycle → 首键更快冷却, 减少 cycle 1→0 概率
- 预算余量 95s 远大于任何风险阈值
- 低流量 (6.2 req/h) → key 池充分, 无 exhaustion risk

## 执行

```bash
# 编辑 compose (行500)
sed -i '500s/KEY_COOLDOWN_S: "36"/KEY_COOLDOWN_S: "34"/' /opt/cc-infra/docker-compose.yml

# 重启容器 (docker compose up -d, 非 restart)
cd /opt/cc-infra && docker compose up -d nv_gw
```

## 验证
- `docker exec nv_gw env | grep KEY_COOLDOWN_S`: KEY_COOLDOWN_S=34 ✓
- `curl /health`: 200 ✓
- 容器 env 与 compose 一致, 无漂移

## 预算余量
- glm5_2: KEY(34)+TIER(0)+GLM5_2(28)=62 << 157 BUDGET (95s)
- dsv4p: KEY(34)+UPSTREAM(24)=58 << 94 BUDGET (36s)
- PEER_FALLBACK_TIMEOUT(122) ≥ HM2_BUDGET+2 ✓ (constraint satisfied)

## 铁律
单参数, 只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2