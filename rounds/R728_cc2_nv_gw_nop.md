# R728 — cc2 nv_gw NOP 巡检 (2026-08-03 20:55 CST)

## 改动: 不改码 (NOP)

## 依据 (30min 窗口)
- **cc2 (cc4101-primary) 30min**: 零流量 (无请求, 非链路故障)
- **nv_gw 全量 30min**: 79×200, 全是 dsv4p_nv (hermes/other caller), SR **100.0%**
  - glm5_2_nv 0 req (30min 内无流量)
- **cc4101 cc_requests 30min**: 16 req, 16×200, SR **100.0%**, fallback 1/16=6.3%
- **错误分类 30min**: 0 错误
- **tier attempts 30min**: 0 行 (glm5_2_nv 无 tier 流量)
- **buffer/wait 日志**: 0 行
- **per-key (dsv4p)**: k0=15, k1=12, k2=14, k3=14, k4=12 — 均衡全 200
- **per-egress-IP**: 5 US IPv4 全 100%
- **dsv4p 延迟**: avg 6.4s, max 35.6s, ttfb 6.1s — 正常
- **finish_reason**: tool_calls×27, stop×30, length×9 — 无 zombie
- **根因**: cc2 零流量 = 用户无请求 (R725 16req→R726 16req→R727 0req→R728 0req 波动正常)

## 12h glm5_2_nv 历史分析 (有流量时段 07:00-11:00 UTC)
| 小时 (UTC) | 总 | 成功 | SR |
|---|---|---|---|
| 07:00 | 16 | 15 | 93.8% |
| 09:00 | 1 | 1 | 100% |
| 10:00 | 18 | 9 | 50.0% |
| 11:00 | 13 | 4 | 30.8% |

### 12h glm5_2_nv 错误分类 (19 errors)
- NVStream_IncompleteRead: 9 (全在 nv_integrate upstream)
- all_tiers_exhausted: 6 (5key 全败后)
- stream_absolute_cap: 3

### 12h per-key tier attempts 根因 (关键)
| key | fid | upstream | 成功 | 失败 | 失败率 |
|-----|-----|----------|------|------|--------|
| k0 | b1b22d03 | pexec | 6 | 0 | 0% ✅ |
| k1 | integrate | integrate | 1 | 7 | 87.5% ❌ |
| **k2** | **3b9748d8** | **pexec** | **4** | **20** | **83%** ❌❌ |
| k3 | integrate | integrate | 6 | 6 | 50% |
| k4 | b6029a96 | pexec | 5 | 2 | 29% |

**k2→fid2(3b9748d8) pexec 是主根因**: 18×RemoteDisconnected (avg 41s), 占总 tier 失败 38%
- 对比: fid1(b1b22d03) 在 k0 上 100% 成功 (6/6)
- fid2(3b9748d8) 在 k2 上 4 success / 20 fail — 这个 fid 可能有持续连接问题

## 验证: NOP 无需 restart
- `/health`: nv_gw ok(5keys) + cc4101 ok(primary=glm5_2_nv) + dsv4p_nv40066 ok(5keys) — 全 ok
- `docker ps`: nv_gw Up 5h, cc4101 Up 6h, dsv4p_nv40066 Up 5h — 全 Up
- 配置零漂移 (R661 baseline 沿用)

## 下一步
- **k2 fid 切换候选**: 把 k2 的 fid 从 index 1 (3b9748d8) 换到 index 0 (b1b22d03)
  - 当前: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 → k2 用 fid index 1 = 3b9748d8
  - 候选: NV_GLM52_KEY_FID_BIND=0:0;2:0;4:2 → k2 用 fid index 0 = b1b22d03 (k0 验证 100%)
  - **前提**: 需 glm5_2_nv 流量恢复后验证, 当前零流量无法验证 (铁律: 改后必验证)
- 持续监控 cc2 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- glm5_2_nv 流量恢复后, 先验证 k2 fid 切换效果

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
