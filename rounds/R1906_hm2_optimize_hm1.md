# R1906 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 170→168 (-2s)

## 数据采集 (HM1, 2026-07-19 ~08:07 UTC)

### 6h DB 摘要 (R1904 后, UPSTREAM=30)
- 总请求: 46
- 成功: 30 (65.2% SR) ↑ +3pp vs R1905
- 失败: 16 (14 zombie_empty_completion, 2 ATE dsv4p)
- OK avg: 7637ms (glm5_2: 7205ms, dsv4p: 9057ms)
- OK max: 19559ms (dsv4p_nv)

### 24h DB 摘要
- 总请求: 158
- 成功: 109 (69.0% SR)
- 失败: 49 (42 zombie, 7 ATE_502, 27 phantom_ATE)

### 1h DB 摘要
- 总请求: 7
- 成功: 3 (42.9%)
- 失败: 4 (1 zombie glm5_2, 2 ATE dsv4p, 1 zombie glm5_2)

### 分模型 (6h)
| 模型 | 总量 | OK | 失败 | OK avg | OK max |
|---|---|---|---|---|---|
| glm5_2_nv | 35 | 23 | 12 zombie | 7205ms | 16462ms |
| dsv4p_nv | 11 | 7 | 2 ATE+2 zombie | 9057ms | 19559ms |

### 分模型 (1h)
| 模型 | 总量 | OK | 失败 |
|---|---|---|---|
| dsv4p_nv | 2 | 0 | 2 ATE (502, 2-3ms, tier cooldown cascade) |
| glm5_2_nv | 5 | 3 | 2 zombie/phantom |

### 新现象: dsv4p_nv ATE cascade
- 2 个 dsv4p ATE 来自同一级联: thinking request 66s timeout → peer-fb 70s fail → tier cooldown
- 日志: `[NV-THINKING-TIMEOUT] (dsv4p_nv)` → `[NV-PEER-FB] peer returned 502 after 70134ms` → `[NV-PEER-FB] peer fallback FAILED`
- 后续请求被 tier cooldown 阻隔 → 2-3ms ATE (all_tiers_failed_in_mapped_tier)
- 根因: dsv4p thinking 请求超时后 peer-fb 也失败, tier cooldown 60s 内所有 dsv4p 请求均被快速拒绝

### Tier 错误 (6h)
| Tier | Error | Count |
|---|---|---|
| glm5_2_nv | pexec_success | 23 |
| glm5_2_nv | pexec_429 | 2 |
| glm5_2_nv | pexec_SSLEOFError | 1 |
| glm5_2_nv | pexec_timeout | 1 |

### 容器状态
- `nv_gw` health: OK (3 tiers)
- `UPSTREAM_TIMEOUT=30`, `TIER_TIMEOUT_BUDGET_S=170`
- `PEER_FALLBACK_TIMEOUT=122`, `PEER_FB_SKIP_MODELS=kimi_nv`
- 所有参数 floor/optimal

## 优化决策

**TIER_TIMEOUT_BUDGET_S: 170→168 (-2s)**

理由:
- SR 从 62.2% (R1904/R1905) 提升至 65.2% (+3pp), 无明显退化
- dsv4p ATE cascade 是单次 thinking timeout 级联, 非参数问题
- OK max=19.6s < 30s UPSTREAM, 安全余量 10.4s
- 预算: UPSTREAM=30 + PEER=122 = 152 < 168 (16s 余量)
- 延续 R1899→R1901→R1903→R1906 的 BUDGET 交替递减轨迹 (176→174→172→170→168)
- 14 zombie 全部 NVCF empty200, 不可配置修复
- 铁律: 只改 HM1 不改 HM2

## 执行

```bash
# HM1 compose edit
sed -i 's|      TIER_TIMEOUT_BUDGET_S: "170".*|      TIER_TIMEOUT_BUDGET_S: "168"  # R1906 (HM2->HM1): ...|' /opt/cc-infra/docker-compose.yml
docker compose up -d nv_gw
```

## 验证

- `/health` → `{"status": "ok"}` with all 3 model tiers
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → `168` ✓
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → `30` ✓
## ⏳ 轮到HM1优化HM2
