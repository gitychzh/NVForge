# R697: HM1-only — PEER_FALLBACK_TIMEOUT 25→45 (对齐 R696 UPGRADE_TIMEOUT=40)

**Date**: 2026-07-05 00:30 UTC (HM1 local, +08:00 = 2026-07-05 08:30)
**Host**: HM1 only (100.109.153.83)
**Iron rule**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw / 所有修改写入仓库

## 背景

R696 (对称两机) 将 `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 从 25→40, 容纳 dsv4p_nv 长尾 TTFB (实测 max 37.2s). R696 的"已知限制"明确标注:

> peer fallback 用 PEER_FALLBACK_TIMEOUT (25s) 而非 40s, peer 路径仍可能 25s 砍. 后续轮次可调.

本轮修复该已知限制.

## 改前数据

### 容器日志证据 (R696 部署后, HM1)

```
[23:02:28.4] [NV-PEER-FB] local all_tiers_exhausted (model=dsv4p_nv), attempting peer fallback to http://100.109.57.26:40006
[23:02:53.4] [NV-PEER-FB] peer connect/request failed after 25027ms: TimeoutError: timed out
[23:02:53.4] [NV-PEER-FB] peer fallback FAILED for model=dsv4p_nv, returning local 502
```

peer fallback 在 25027ms (≈25s) timeout. peer 自身 upstream 用 `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40s` (R696 改后), 所以 peer 在 25s 内根本无法完成 thinking/stream-upgrade 请求的 TTFB.

### DB 证据 (R696 前 6h window)

- HM1 dsv4p_nv 502: `fallback_actually_attempted=f` (DB 记录), `tiers_tried_count=1`.
- DB 的 `fallback_actually_attempted` 列在 `_build_request_row()` 中定义为 `len(key_cycle_details) > 1`, 不是 peer fallback 标志 — 容器日志才是 peer fallback 的 ground truth.
- peer fallback 确实被触发 (容器日志 [NV-PEER-FB] 确认), 但 25s timeout 导致 peer 请求被杀, 最终返回本地 502.

### 根因链

1. openclaw 发 dsv4p_nv 请求 (带 reasoning_effort=xhigh, 被 nv_gw strip).
2. nv_gw 本地 5 key 全部尝试, 单 key 40s timeout (R696), TIER_TIMEOUT_BUDGET_S=72s 内最多尝试 ~1.5 个 key.
3. 本地 all_tiers_exhausted → 触发 peer fallback 到 HM2 (100.109.57.26:40006).
4. peer fallback socket timeout = 25s (NVU_PEER_FALLBACK_TIMEOUT).
5. HM2 nv_gw 收到 peer 请求, 走同样的 40s upstream timeout (R696 对称改).
6. 25s < 40s: peer 请求还没等到 NVCF 首字节就被 HM1 的 fallback timeout 杀掉.
7. HM1 返回 502 给客户端.

## 修改

| 文件 | 修改 |
|---|---|
| `/opt/cc-infra/docker-compose.yml` | `NVU_PEER_FALLBACK_TIMEOUT: "25"` → `"45"` |

备份: `docker-compose.yml.bak.R697`.

### 参数选择理由

- `45s = 40s (peer NVU_FORCE_STREAM_UPGRADE_TIMEOUT) + 5s (connect/relay reserve)`.
- R696 实测 dsv4p_nv TTFB 长尾 max 37.2s (HM2), 40s upstream timeout 已覆盖. peer fallback 45s 给 peer 完整的 40s upstream window + 5s 连接/中继余量.
- Worst case total: 72s (local TIER_TIMEOUT_BUDGET_S) + 45s (peer) = 117s < PROXY_TIMEOUT 300s. 安全.
- 不改 HM2: HM2 的 `NVU_PEER_FALLBACK_TIMEOUT` 仍是 25s, 但 HM2 peer fallback URL 指向 HM1 (100.109.153.83:40006), HM1 同样有 40s upstream. HM2 的 peer fallback 25s 问题对称存在, 但本轮范围是 HM1-only. HM2 可在后续对称轮次修复.

## 验证

### 改后即时验证

```
$ docker exec nv_gw env | grep NVU_PEER_FALLBACK_TIMEOUT
NVU_PEER_FALLBACK_TIMEOUT=45

$ curl -s -o /dev/null -w "health=%{http_code} %{time_total}s" http://127.0.0.1:40006/health
health=200 0.001262s
```

### HM2 peer endpoint 可达性

```
$ curl -s -o /dev/null -w "%{http_code} %{time_total}s" --connect-timeout 5 http://100.109.57.26:40006/health
200 0.002690s
```

HM2 nv_gw peer endpoint 健康, peer fallback 路径可达.

### 改后预期 (待流量验证)

- dsv4p_nv peer fallback 成功率: 25s timeout 时 0% (peer 从未在 25s 内完成) → 45s timeout 预期 >80% (peer 40s upstream 覆盖 37.2s max TTFB).
- 本地 502 → peer 200 的 rescue 路径恢复.
- 502 率从 R696 后的 ~10-15% (peer fallback 全部失败的残留) 降到 <5%.

## 参数表 (改后, HM1)

| Param | Value | Note |
|---|---|---|
| NVU_PEER_FALLBACK_TIMEOUT | 45 | R697: 25→45, 对齐 R696 UPGRADE_TIMEOUT=40 + 5s reserve |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 40 | R696, 不变 |
| UPSTREAM_TIMEOUT | 25 | non-thinking path, 不变 |
| TIER_TIMEOUT_BUDGET_S | 72 | 不变 |
| NV_INTEGRATE_MODELS | "" | R696, 不变 |
| dsv4p_nv inject | {} | R696, 不变 |
| dsv4p_nv strip_params | [reasoning_effort, stream_options, thinking] | R696, 不变 |

## 已知限制

- HM2 的 `NVU_PEER_FALLBACK_TIMEOUT` 仍是 25s, HM2→HM1 peer fallback 同样存在 25s 不足问题. 后续对称轮次可修.
- HM2 SSH 不可达 (port 22/2222 connection refused), 无法对称修改. 但 HM2 nv_gw HTTP endpoint (40006) 健康, peer fallback 路径可用.
- 45s peer timeout 意味着失败路径总时长最长 117s (72s local + 45s peer), 客户端需容忍. 但 PROXY_TIMEOUT=300s 有足够余量.

## Verification Checklist

- [x] docker-compose.yml 备份 .bak.R697
- [x] NVU_PEER_FALLBACK_TIMEOUT=45 (env 确认)
- [x] nv_gw /health 200
- [x] HM2 peer endpoint (100.109.57.26:40006) 可达, /health 200
- [x] 容器 recreate 成功 (docker compose up -d nv_gw)
- [ ] 24h 窗口 peer fallback 成功率 >80% (待流量验证)
- [ ] 24h 窗口 dsv4p_nv 502 率 <5% (待流量验证)
