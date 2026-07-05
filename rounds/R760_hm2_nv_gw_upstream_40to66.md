# R760: HM2 nv_gw UPSTREAM_TIMEOUT 40→66 — 修复误杀正常慢请求

> 仅改 HM2 nv_gw env。HM1 全未动。源码未动 (模块化铁律)。

## 改前数据 (铁律: 改前必有数据)

### 配置漂移
| 参数 | HM2 | HM1 (生产) |
|---|---|---|
| UPSTREAM_TIMEOUT | 40 | 66 |
| TIER_TIMEOUT_BUDGET_S | 110 | 114 |

R754-R757 git 记录 HM2 也是 66, 当前 40 是无轮次记录的漂移下调。

### 40s 误杀正常请求的量化 (3h)
| 模型 | 成功总数 | 耗时>40s 的成功 (被砍) | >60s 的成功 |
|---|---|---|---|
| dsv4p_nv | 118 | 15 (12.7%) | 5 |
| glm5_2_nv | 53 | 7 (13.2%) | 3 |

成功 p90/p99:
- dsv4p_nv: p90=46.3s, p99=87.6s, max=94.2s — **p90 已超 40s, 正常慢请求被当 timeout 砍**
- glm5_2_nv: p90=51.7s, p99=81.3s, max=85.4s — 同样误杀

### NVCF 真实 timeout (R755 git, HM1 UPSTREAM=66 时)
- dsv4p_nv: NVCFPexecTimeout max=60,823ms (buffer=5.2s)
- glm5_2_nv: max=62,389ms (buffer=3.6s)

NVCF 平台侧真实 timeout ~61s。UPSTREAM=40 远低于此, 把 NVCF 还在正常处理的请求 (p90=46~52s) 提前砍掉。

### 当前 NVCF timeout 触发耗时 (HM2, UPSTREAM=40)
- dsv4p_nv: 40.6~45.9s (40s socket 人工边界, 非 NVCF 真实 timeout)
- glm5_2_nv: 47.3~53.4s

## 根因

upstream.py:163-165:
```python
per_attempt_timeout = max(MIN_ATTEMPT_TIMEOUT,
                          min(UPSTREAM_TIMEOUT, remaining_budget - CONNECT_RESERVE_S))
```
UPSTREAM_TIMEOUT 是单 key read timeout 上限。=40 时单 key 读 40s 就 timeout 换 key, 但 NVCF 真实 timeout ~61s, 成功 p90=46~52s, 40s 把这些当 timeout 误杀。

## 改动 (单参数, 对齐 HM1)

`/opt/cc-infra/docker-compose.yml` nv_gw 块:
```
- UPSTREAM_TIMEOUT=40   →   UPSTREAM_TIMEOUT=66
```
仅 HM2, 仅 nv_gw (ms_gw=300/cc4101=120 未动)。

### 为什么是 66
- R754: glm5_2_nv max=62,389ms, UPSTREAM=64 buffer=1.6s<3s → +2s 到 66, buffer=3.6s
- R755: dsv4p buffer=5.2s, glm5_2 buffer=3.6s, "BUDGET=114>>66 safe"
- R754-R757 多轮验证 66 覆盖 NVCF 真实 timeout(~61s)+最小 buffer(3s)
- HM1 生产用 66, 两机对齐

### 不改
- TIER_TIMEOUT_BUDGET=110 (>66, 安全; budget 兜底最坏耗时)
- NVU_PEER_FALLBACK_TIMEOUT=90 (R757 设, 覆盖 HM1 pexec 29~61s)
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=90 (独立, 下轮)
- 代码逻辑 / HM1 / 源码 / adapter

### 与 R758/R759 互补
- R758: FASTBREAK 1→3 (1 次 timeout 不再放弃 5 key)
- R759: opclaw4103 150+300→90+120 (< openclaw 240s stuck)
- R760: UPSTREAM 40→66 (不再误杀 p90=46~52s 正常慢请求)

## 改后验证

### env 生效
- UPSTREAM_TIMEOUT=66, FASTBREAK=3 ✓
- health 200 ✓

### 实测
- dsv4p_nv 非流: 5s 成功 "Hello! How can I help you today?" ✓
- 改后 5min: dsv4p_nv 4/4 全成功 (avg 13.6s), glm5_2_nv 4/4 全成功 (avg 31s), 0 个 502, 0 次 timeout

## 预期 (待 30min+ 观察)
1. dsv4p_nv/glm5_2_nv 成功率上升 (救回 ~12-13% 被 40s 误杀的请求)
2. NVCF timeout 触发耗时从 40~46s 上移到 ~61s (NVCF 真实边界)
3. 单 key 最坏 66s, TIER_TIMEOUT_BUDGET=110 兜底, 最坏不超 110s + PEER-FB 90s = 200s

## 代价
- 单次 502 耗时 40s→66s (但减少误杀, 总成功率上升)
- budget 110s 兜底

## 风险
- 低: 对齐 HM1 生产值, R754-R757 长期验证
- 回滚: env 改回 40

## 遗留
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=90 vs HM1=66 (下轮)
- NVU_PEER_FALLBACK_TIMEOUT=90 vs HM1=45 (R757 设, 不动)
- HM1 同步待授权
