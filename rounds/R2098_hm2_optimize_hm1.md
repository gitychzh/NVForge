# R2098 (HM2→HM1): KEY_COOLDOWN_S 65→67 (+2s)

## 数据收集 (6h window, 2026-07-21 00:25 UTC)

### 请求概览
- **Total**: 31 req, 19 OK (61.3% SR), 12 fail
- **Caller**: openclaw 100% (31/31)

### 错误分布
| 错误类型 | 模型 | 数量 |
|---|---|---|
| zombie_empty_completion | glm5_2_nv | 8 |
| all_tiers_exhausted | dsv4p_nv | 3 |
| NVStream_IncompleteRead | glm5_2_nv | 1 |

### 429 循环分析
- **19/31 (61.3%)** 请求有 key_cycle_429s >= 1
- 全部 19 个成功请求 (glm5_2_nv) 都有 key_cycle_429s=1 — 100%成功率请求在第一键被429
- 3 个请求有 3/5/7 次循环 (多键429)
- TIER_COOLDOWN_S=60, KEY_COOLDOWN_S=65

### 延迟 (成功请求)
- glm5_2_nv: 19 req, avg=17475ms, min=5628ms, max=119756ms

### Tier 层错误
- pexec_success: 19
- pexec_timeout: 10
- pexec_SSLEOFError: 5

### 30-min 窗口
- 2 req, 2 OK — 低流量

## 分析

R2091 将 KEY_COOLDOWN_S 从 62→65 (+3s) 给 5s 超过 60s NVCF 窗口，但 429 cycling 仍然 61.3%。每个成功请求在第一键触发 429 后循环到第二键。65s (= 60s NVCF 窗口 + 5s 余量) 不够，NVCF 实际 rate window 可能略超 60s。

## 优化

**KEY_COOLDOWN_S: 65 → 67 (+2s)**

- 67s = 60s NVCF 窗口 + 7s 余量，比 65s 多 2s buffer
- KEY+TIER=67+60=127 < 153 BUDGET (26s margin) ✓
- UPSTREAM+PEER_FB=24+122=146 < 153 BUDGET ✓
- 单参数，铁律：只改HM1不改HM2

## 验证

- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=67 ✓
- `curl /health` → status=ok ✓
- Container restarted via `docker compose up -d nv_gw`
## ⏳ 轮到HM1优化HM2
