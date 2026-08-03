# R725 — cc2/HM2 NOP 巡检轮 (2026-08-03 20:35 CST)

## 改动: 不改码 (NOP)

## 依据 (30min + 2h/6h 窗口交叉验证)

### cc2 (cc4101) 可见 SR — 本轮恢复有流量
- cc_requests 30min: 16 req, 15×primary 200 + 1×fallback 200 = **可见 SR 100.0%** (16/16)
- fallback 触发率: 1/16 = **6.25%** (目标 < 10%, 达标)
- 唯一 fallback: req=7c201729 primary glm5_2_nv 502 after 34s → fallback dsv4p_nv 200 after 2s (cc4101 层兜底有效)
- cc4101 日志: 17 REQ model=glm5_2_nv→glm5_2_nv passthrough, 1 PRIMARY-FAIL server_5xx 502, 1 FALLBACK-OK
- **注**: cc2 流量恢复 (R716-R724 连续 9 轮零流量后本轮 16 req) — 零流量 streak 终结

### nv_gw 全量 30min (caller=mapped_model × status)
- dsv4p_nv: 63×200 = **SR 100.0%** (63/63) — 持续健康 (R724=100.0% 持平)
- glm5_2_nv: **0 req** (30min 窗口无 glm5_2_nv 最终态请求 — tier attempts=0)
  - 原因: cc4101 primary 请求经 nv_gw glm5_2_nv tier 链路, pexec 全 5 key RemoteDisconnected 后走 integrate, integrate 成功的 req 被 NV-STREAM-ABS-CAP (150s) 截断或 IncompleteRead → 502 → cc4101 fallback dsv4p
  - 但 cc4101 层仍 15/16 primary 200 — 说明多数 glm5_2_nv 请求最终成功 (经 nv_gw buffer/integrate 链路)

### 6h SR 趋势 (更大小本)
- **glm5_2_nv**: 29×200 / 19×502 = **SR 60.4%** (48 req, 低流量) — avg 200=52.1s, avg 502=153.0s
  - 502 错误: all_tiers_exhausted×6 (全 key 挂), NVStream_IncompleteRead×11, stream_absolute_cap×3, NVAnthCollect_IncompleteRead×1
  - tier 失败: pexec_conn_RemoteDisconnected×19 (k3 重灾区), IntegrateRemoteDisconnected×15, integrate_conn_RemoteDisconnected×7, pexec_SSLEOFError×4, 429_nv_rate_limit×9, pexec_500×1
  - per-key: k3 fid=3b9748d8 pexec_conn_RD×18 (最差), k1/k3 integrate IntegrateRD 集中
- **dsv4p_nv**: 389×200 / 18×429 / 18×502 = **SR 91.5%** (425 req, 高流量) — dsv4p 持续承载主力

### 错误分类 (6h, 无新错误类型)
- nv_requests: all_tiers_exhausted×38, NVStream_IncompleteRead×13, stream_absolute_cap×3, NVAnthCollect_IncompleteRead×1 — 全 NVCF 上游连接/配额副作用
- nv_tier_attempts: pexec_conn_RD×19, pexec_success×17, IntegrateRD×15, 429×9, integrate_success×7, integrate_conn_RD×7, NVCFPexecRD×6, pexec_SSLEOFError×4, pexec_500×1 — 全已知类型

### per-key × fid × mode (6h, glm5_2_nv tier)
- k0: pexec b1b22d03 success×6 — 健康
- k1: integrate IntegrateRD×4 + integrate_conn_RD×3 + integrate_success×1 — integrate 不稳
- k2: pexec 3b9748d8 pexec_conn_RD×18 (重灾区!) + pexec_500×1 + pexec_SSLEOFError×1; pexec b1b22d03 SSLEOF×2; integrate IntegrateRD×3 — k2 pexec 3b9748d8 最差
- k3: integrate IntegrateRD×2 + integrate_conn_RD×4 + integrate_success×6 — integrate 不稳但可成
- k4: pexec b1b22d03/b6029a96 success×6 (健康) + integrate IntegrateRD×3

### dsv4p 延迟 (30min 200)
- avg 7183ms, max 32224ms, min 1430ms, ttfb 6772ms, avg_in 2 tok, avg_out 9 tok
- finish_reason: tool_calls×49, stop×18, length×7 (无 zombie)

### buffer/wait/keymanager 日志
- docker logs nv_gw --since 30m: **0 行** (无新日志 — 最后日志 19:56 CST, ~40min 前)
- 最后日志: [NV-STREAM-ABS-CAP] glm5_2_nv 150s cap exceeded (elapsed=187s) + Broken pipe — 已知长请求截断

## 验证: NOP 无需 restart
- `curl /health`: nv_gw ok (5keys, glm5_2_nv/dsv4p_nv/kimi_nv) + cc4101 ok (primary=glm5_2_nv) + dsv4p_nv40066 ok (5keys) — 全 ok
- `docker ps`: nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 5h, nv_gw_stable Up 43h, logs_db Up 4d — 全 Up
- 配置零漂移 (R661 baseline):
  - nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120
  - cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, PRIMARY_SKIP_S=30, FAIL_THRESHOLD=3
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr

## 根因分析
- glm5_2_nv 6h SR 60.4% (低流量 48 req): 主要失败是 NVCF 上游连接断开
  - k2 pexec fid=3b9748d8 连续 RemoteDisconnected×18 — 该 fid+IP 组合可能有问题
  - k1/k3 integrate 路径 IntegrateRemoteDisconnected 集中 — integrate API 不稳
- 但 cc4101 层可见 SR 100% (fallback 6.25%): cc4101→nv_gw glm5_2_nv 失败后 fallback dsv4p_nv 40066 兜底, 用户不可见
- dsv4p_nv 6h SR 91.5% (高流量 425 req): 429×18 + 502×18, 主力稳定

## 下一步
- 持续监控 cc2 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- glm5_2_nv k2 pexec fid=3b9748d8 连续 RemoteDisconnected 重灾区 — 若持续恶化可考虑:
  - 把 k2 从 pexec 3b9748d8 切到 b1b22d03 (k0/k4 用 b1b22d03 success×10 健康)
  - 但需更多数据 (当前 6h 仅 48 req glm5_2_nv, 样本小)
- 若 cc2 流量持续恢复后 fallback 率 >10% 再深入查 glm5_2_nv tier
- R661 post-restart ~43h+ 仍无新错误类型, 配置稳定

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
