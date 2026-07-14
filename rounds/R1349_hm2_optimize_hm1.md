# R1349: HM2→HM1 — NOP (false trigger, 零可修故障, 509th chain of R1133)

## 数据 (6h window, container restart 07:23 UTC)

| Metric | Value |
|--------|-------|
| Total | 81 req / 67 OK / 14 fail |
| Overall SR | 82.7% |
| Tier attempts | 0 (zero key cycling) |
| Fallback | 0 (zero cross-model fallback) |

### Per-model

| Model | Path | Total | OK | Fail | SR | Avg ms | P50 ms |
|-------|------|-------|-----|------|-----|--------|--------|
| dsv4p_nv | pexec | 48 | 48 | 0 | 100.0% | 20,938 | 18,649 |
| dsv4p_nv | (ATE) | 6 | 0 | 6 | 0.0% | 71,694 | 72,024 |
| glm5_2_nv | integrate | 27 | 19 | 8 | 70.4% | 12,443 | 10,916 |

### Error breakdown

| Error type | Count | Avg ms |
|-----------|-------|--------|
| zombie_empty_completion | 8 | 9,602 |
| all_tiers_exhausted | 6 | 71,694 |

### Zombie per-key

| Key | Count | Avg ms |
|-----|-------|--------|
| K1 (k0) | 3 | 6,703 |
| K2 (k1) | 1 | 14,310 |
| K4 (k3) | 3 | 12,321 |

### ms_gw fallback

| Status | Count | Avg ms |
|--------|-------|--------|
| ok | 5 | 21,824 |
| client_disconnect | 1 | 10,598 |

## 分析

1. **dsv4p_nv pexec 100% SR (48/48)** — 完美，无需改动
2. **dsv4p_nv ATE 6 全部 PRE-RESTART (07:23 UTC前)** — 旧容器实例数据，非当前配置问题。Post-restart 0 dsv4p_nv 失败
3. **glm5_2_nv zombie_empty_completion 8** — code-level zombie detection (content_chars=12 < 50, input_chars≥185K)。Gateway 正确检测并发送 error SSE chunk 触发 openclaw fallback。**不可配置修复** (code-level 行为)
4. **0 tier_attempts** — 零 key 轮转，所有成功请求首次 key 通过
5. **0 fallback** — 零跨模型 fallback 触发
6. **ms_gw 5/6 OK** — client_disconnect 是用户端断开，非服务端问题

## 决策: NOP

- 零可修故障 (config-fixable)
- 所有参数 floor/optimal
- Compose md5 4c3e804d 未变化
- 铁律: 只改 HM1 不改 HM2
- 少改多轮 (本轮不改, 零可修故障)

## ⏳ 轮到HM1优化HM2