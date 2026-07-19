# R1882 (HM2→HM1): UPSTREAM_TIMEOUT 47→45 (-2s)

## 改前数据 (6h window, ~11:50 CST)

| Metric | Value |
|---|---|
| Total | 44 |
| OK | 10 (22.7% SR) |
| Fail | 34 zombie_empty_completion |
| All big_input | 44 (>115K chars) |
| Model | glm5_2_nv (100%) |
| Peer-fallback | 0 triggered |
| ATE phantom | 2 (status=200, BIG_INPUT breaker 03:03→peer-fb OK) |

### 30min window (~11:20-11:50 CST)

| Metric | Value |
|---|---|
| Total | 6 |
| OK | 5 (83.3% SR) |
| Fail | 1 zombie_empty_completion |
| OK max duration | 15,650ms |
| OK avg duration | 8,429ms |
| Peer-fallback | 0 triggered |

### Tier attempts (6h)

| Tier | Error | Count |
|---|---|---|
| glm5_2_nv | pexec_success | 51 |
| glm5_2_nv | pexec_429 | 1 |
| glm5_2_nv | pexec_SSLEOFError | 1 |

### Container state
- nv_gw: Up 8min (R1881 restart), /health ok
- All other containers: Up 2 days
- No NV-ANTH-BREAKER events, no NV-PEER-FB in logs

## 分析

- 全链路 glm5_2_nv NVCF-degraded, 44/44 都是 big_input(>115K) zombie
- 30min 窗口仅 1 个 zombie, OK max=15.65s, margin 巨大
- UPSTREAM_TIMEOUT 当前 47s, 砍到 45s 省 2s
- OK max=15.65s, 45-15.65=29.35s >> 3s 安全余量
- Peer-fb 预算: 45+122=167 < 178 (11s margin) ✓
- Peer-fb 约束: PEER_FALLBACK_TIMEOUT=122 ≥ HM2 glm5_2 budget=120+2=122 ✓
- 单参数, 少改多轮

## 改后验证
- docker compose up -d nv_gw → Recreated, Started
- docker exec nv_gw env → UPSTREAM_TIMEOUT=45 ✓
- /health → status: ok ✓

## 评判
- 更少报错: zombie 路径每请求快 2s fail
- 更快请求: OK 路径不受影响 (max=15.65s << 45s)
- 稳定优先: 30min 窗口 83.3% SR, margin 29.35s 充足
- 铁律: ��改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
