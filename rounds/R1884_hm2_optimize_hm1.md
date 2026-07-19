# R1884 (HM2→HM1): UPSTREAM_TIMEOUT 45→43 (-2s)

## 改前数据 (6h window, ~12:15 CST)

| Metric | Value |
|---|---|
| Total | 48 |
| OK | 13 (27.1% SR) |
| Fail | 35 zombie_empty_completion |
| All big_input | 48 (>115K chars) |
| glm5_2_nv | 45 req (11 OK + 34 zombie) |
| dsv4p_nv | 3 req (2 OK + 1 zombie) |
| ATE phantom | 6 (glm5_2_nv:4 + dsv4p_nv:2, status=200, peer-fb rescue) |
| Peer-fallback | 3 triggered (all OK, 7-10ms ttfb) |

### 30min window (~11:45-12:15 CST)

| Metric | Value |
|---|---|
| Total | 6 |
| OK | 4 (66.7% SR) |
| Fail | 2 zombie_empty_completion (1 dsv4p_nv + 1 glm5_2_nv) |
| OK avg duration | 7,490ms |
| OK max duration | 9,778ms |
| Peer-fallback | 2 triggered (both OK, 7-10ms) |

### Error breakdown (6h)

| Model | Error | Count |
|---|---|---|
| glm5_2_nv | zombie_empty_completion | 34 |
| dsv4p_nv | zombie_empty_completion | 1 |

### Log highlights

- BIG_INPUT breaker active: NV-BIGINPUT-FB-OPEN for dsv4p_nv 126050c → peer-fallback → 200 OK (10ms/7ms ttfb)
- NV-BIGINPUT-SUCCESS → breaker CLOSED on successful nv pass
- No NV-ANTH-BREAKER events, no SSLEOF errors
- 0 pexec_429 in 6h

### Container state

- nv_gw: Up 22h (R1881 restart), /health ok
- All other containers: Up 2+ days
- StartedAt: 2026-07-18T21:26:29Z

## 分析

- 全链路 NVCF-degraded, 48/48 big_input(>115K) zombie
- BIG_INPUT breaker + peer-fallback 有效兜底 (6 ATE phantom 200 OK via HM2 rescue)
- 30min OK max=9.78s, 当前 UPSTREAM=45s margin=35.22s >> 3s 安全
- UPSTREAM_TIMEOUT 45→43 省 2s: zombie 路径每请求快 2s fail
- Peer-fb 预算: 43+122=165 < 178 (13s margin) ✓
- Peer-fb 约束: PEER_FALLBACK_TIMEOUT=122 ≥ HM2_BUDGET+2=122 ✓
- 单参数, 少改多轮

## 改后验证

- sed 修改 compose UPSTREAM_TIMEOUT: "45" → "43"
- docker compose up -d nv_gw → Recreated, Started
- docker exec nv_gw env → UPSTREAM_TIMEOUT=43 ✓
- /health → status: ok ✓

## 评判

- 更少报错: zombie 路径每请求快 2s fail
- 更快请求: OK 路径不受影响 (max=9.78s << 43s)
- 稳定优先: 30min 窗口 66.7% SR, margin 33.22s 充足
- 铁律: 只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
