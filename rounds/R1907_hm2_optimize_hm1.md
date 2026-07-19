# R1907 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 168→166 (-2s)

## 数据采集 (HM1, 2026-07-19 ~08:21 UTC)

### 6h DB 摘要 (R1906 后, UPSTREAM=30, BUDGET=168)
- 总请求: 46
- 成功: 30 (65.2% SR) 持平 R1906
- 失败: 16 (14 zombie_empty_completion, 2 ATE dsv4p)
- OK avg: 7637ms (glm5_2: 7205ms, dsv4p: 9057ms)
- OK max: 19559ms (dsv4p_nv)

### 分模型 (6h)
| 模型 | 总量 | OK | 失败 | OK avg | OK max |
|---|---|---|---|---|---|
| glm5_2_nv | 35 | 23 | 12 zombie | 7205ms | 16462ms |
| dsv4p_nv | 11 | 7 | 2 ATE+2 zombie | 9057ms | 19559ms |

### 僵尸详情 (14 zombie, 6h)
- 全部 glm5_2_nv/dsv4p_nv, input 119K-129K chars
- 全部 NVCF empty200, 不可配置修复
- BIG_INPUT breaker (threshold=115000) 未触发 → 0 peer-fallback

### ATE 详情 (2 ATE, 6h)
- dsv4p_nv: 2 ATE, 502, 2-3ms, tiers_tried=1 (tier cooldown cascade)
- 上次 dsv4p thinking timeout 级联触发 tier cooldown 阻断

### Tier 错误 (6h)
| Tier | Error | Count |
|---|---|---|
| glm5_2_nv | pexec_success | 23 |
| glm5_2_nv | pexec_429 | 2 |
| glm5_2_nv | pexec_SSLEOFError | 1 |
| glm5_2_nv | pexec_timeout | 1 |

### 容器状态
- `nv_gw` health: OK, 3 tiers
- `UPSTREAM_TIMEOUT=30`, `TIER_TIMEOUT_BUDGET_S=168`
- `PEER_FALLBACK_TIMEOUT=122`, `PEER_FB_SKIP_MODELS=kimi_nv`
- Peer-fallback URL: `http://100.109.57.26:40006` → 200 OK

## 优化决策

**TIER_TIMEOUT_BUDGET_S: 168→166 (-2s)**

理由:
- SR 持平 R1906 (65.2%), 无退化
- OK max=19.6s(dsv4p) < 30s UPSTREAM, 安全余量 10.4s
- 预算: UPSTREAM=30 + PEER=122 = 152 < 166 (14s 余量)
- 延续 R1906→R1907 BUDGET 交替递减轨迹 (168→166)
- 14 zombie 全部 NVCF empty200, 不可配置修复; BIG_INPUT breaker 未触发
- 单参数; 铁律: 只改 HM1 不改 HM2

## 执行

```bash
# HM1 compose edit
sed -i 's|      TIER_TIMEOUT_BUDGET_S: "168".*|      TIER_TIMEOUT_BUDGET_S: "166"  # R1907 (HM2->HM1): ...|' /opt/cc-infra/docker-compose.yml
docker compose up -d nv_gw
```

## 验证

- `/health` → `200` OK
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → `166` ✓
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → `30` ✓
- 容器重启后 11min healthy
## ⏳ 轮到HM1优化HM2
