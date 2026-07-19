# R1904 (HM2→HM1): UPSTREAM_TIMEOUT 32→30 (-2s)

## 数据采集 (HM1, 2026-07-19 ~15:40 UTC)

### 6h DB 摘要
- 总请求: 45
- 成功: 28 (62.2% SR)
- 失败: 17 (100% zombie_empty_completion, all NVCF empty200)
- OK avg: 7996ms, max: 19559ms (dsv4p_nv)

### 分模型
| 模型 | 总量 | OK | 失败 | OK avg | OK max |
|---|---|---|---|---|---|
| glm5_2_nv | 36 | 21 | 15 | 7643ms | 16462ms |
| dsv4p_nv | 9 | 7 | 2 | 9057ms | 19559ms |

### Tier 错误
- glm5_2_nv pexec_success: 26
- glm5_2_nv pexec_429: 2
- glm5_2_nv pexec_SSLEOFError: 2

### 容器状态
- `nv_gw` health: OK (3 tiers)
- `UPSTREAM_TIMEOUT=32`, `TIER_TIMEOUT_BUDGET_S=170`
- PEER_FALLBACK_TIMEOUT=122, PEER_FB_SKIP_MODELS=kimi_nv
- 无 peer-fb 日志 (僵尸全被 empty200 fastbreak 快速截断)

## 优化决策

**UPSTREAM_TIMEOUT: 32→30 (-2s)**

理由:
- OK max=19.6s (dsv4p_nv) < 30s, 安全余量 10.4s
- 17 zombie 全是 empty200 (NVCF 返回空内容), 不是真正的超时, 更快截断节省资源
- 预算: UPSTREAM=30 + PEER=122 = 152 < 170 (18s 余量)
- 延续 R1898→R1900→R1904 的 UPSTREAM 交替递减轨迹

## 执行

```bash
# HM1 compose edit
sed -i 's|      UPSTREAM_TIMEOUT: "32".*|      UPSTREAM_TIMEOUT: "30"  # R1904 (HM2->HM1): ...|' /opt/cc-infra/docker-compose.yml
docker compose up -d nv_gw
```

## 验证

- `/health` → `{"status": "ok"}` with all 3 model tiers
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → `30` ✓
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → `170` ✓

## ⏳ 轮到HM1优化HM2
