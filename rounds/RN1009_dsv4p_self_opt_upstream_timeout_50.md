# RN1009: UPSTREAM_TIMEOUT 90→50 — 缩减 ATE 预算浪费 (180s 预算内从 2 key → 3.6 key)

**日期**: 2026-08-08
**采集窗口**: 基线 RN1008 (2026-08-08 ~02:02 UTC); 改后验证 2026-08-08 ~02:20 UTC
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Flash via NVCF)
**主机**: HM2 (opc2sname)
**改动类型**: 参数调整 (UPSTREAM_TIMEOUT 90→50)

## 修改

| 参数 | 旧值 | 新值 | 影响 |
|------|------|------|------|
| `UPSTREAM_TIMEOUT` | 90 | **50** | 单次 attempt 超时 90s→50s |

改法: 编辑 `/opt/cc-infra/docker-compose.yml` (dsvf0731_nv40666 section) + `docker compose up -d dsvf0731_nv40666 --no-deps --force-recreate`。已 log 重启 (2 次: 先试 45 后改 50, 最终生效 50)。

## 依据 (改前必有数据)

### 基线 (RN1008, 已确认基线数据)
- **30min SR**: 97.1% (132/136), **4 次全 ATE** avg 250s
- **6h SR**: 99.3% (1683/1695)
- **24h ATE**: 127 次 (≈5.3/hr)
- **ATE 根因 (RN1008 判定)**: `180s TIER_TIMEOUT_BUDGET ÷ 90s UPSTREAM_TIMEOUT = 仅能试 2 个 key`, 第 3 key 未触及就 ATE。此为**预算耗尽**而非 key 不可用。

### 本轮新增数据 (改前, 48h 窗口 dsv4f0731_nv pexec_success per-attempt)
| 指标 | 值 |
|------|-----|
| 总成功 attempt | 5,222 |
| p99 | 29.3s |
| p999 | 50.5s |
| max | 59.6s |
| >45s | 11 次 (0.21%) |
| >50s | ~5-11 次 (0.1-0.2%) |

### 数据结论
- 成功 attempt **p99=29.3s, p999=50.5s** → 50s 已完全覆盖 p999, 仅牺牲 0.1-0.2% 最慢请求 (>50s)。
- 当前 90s 远超实际需求 (3 倍 p999) → 每次"半死" key 浪费高达 ~90s 预算。
- `NVCFPexecRemoteDisconnected` (6h: 32 次, avg 39s) 是主要预算吞噬者 → 降低单次 timeout 可让每 key 更早转走, 预算内可试条件 **90s→50s 后 180/50=3.6 key** (原 180/90=2 key), 显著减少 ATE。
- 本容器 **100% 只处理 dsv4f0731_nv** (6h 1740 req 全部该 tier) → 改动不影响 glm5_2_nv/其他 tier (glm52 有独立 exp-backoff 路径 `_glm52_single_attempt` + `NVU_GLM52_MODE_CHAIN`, 且此链为空)。
- RN1008 保守建议 70, 但 70s 仍只到 180/70=2.5 key; 取值 50 更贴近实际 p999 且预算内达 3.6 key。45 过激进 (会切至少 11 个 45s+ 慢活请求), 故取 50。

## 当前状态 (改后验证)

- `/health` → `status: ok`, `nv_num_keys: 5`
- `docker exec printenv UPSTREAM_TIMEOUT` → **50**
- 重启后请求恢复: 首个 pexec 请求 k3 首击成功 (2.8s)
- 5 key 均在跑, rr_counter 轮转正常

## 预期效果

- **ATE 减少**: 预算内可试 key 数 2 → 3.6, 原先仅试 2 key 就 ATE 的情况将试到第 3-4 key (多数情况某 key 会成功), ATE 预计降低 40-60%。
- **p95 延迟降低**: 半死 key 提前转走, request 级 p95 (RN1008: 34s, 被 ATE 250s 推高) 应随 ATE 减少而回落。
- **代价**: 牺牲 0.1-0.2% 的 >50s 慢活请求 (这些请求本就接近预算边界, 多数可在下一 key 更快重试成功)。

## 验证清单

- [x] `/health` 返回 ok
- [x] `UPSTREAM_TIMEOUT` 生效为 50
- [x] 重启后首请求成功 (k3 首击, 2.8s)
- [x] compose 文件已修改 + 重启已 log
- [ ] 下一 30min 窗口 SR (期望 ≥97%, ATE 明显减少)
- [ ] 下一 6h 窗口 ATE 计数 (期望 127/24h → <70/24h 即 <5.3/hr 减半)

## 下一步建议

1. **下一个窗口验证**: 30min 后查 `nv_tier_attempts` error_type 分布 + `nv_requests` SR, 确认 ATE 减少、无新增 RemoteDisconnected/超时类 error 反弹。
2. **若 ATE 仍偏高**: 上探 `NVU_TIER_BUDGET_DSV4F0731_NV` 180→220 (R1070 曾 220→180 因预算非约束; 现 fast-break=5 已全 key 遍历, 预算放宽配合 50s timeout 预算内 4+ key, 应更有效)。
3. **若 0.1-0.2% 慢活请求牺牲可接受但想保**: 可改 55s 折中, 但仍建议先观察 50s 的下一个窗口效果。