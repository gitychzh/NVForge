# R730 — cc2 nv_gw NOP 巡检 (2026-08-04 07:22 CST)

> 上轮: R729 (NOP, glm5_2_nv 流量恢复 42×200 SR100%)
> 容器: nv_gw Up 5h, cc4101 Up 10h, dsv4p_nv40066 Up 5h, nv_gw_stable Up 2days

## 改动: 不改码 (NOP)

## 依据 (真实 30min UTC 窗口, nv_requests 表)

### 链路总览 (nv_gw 视角, caller=cc4101-primary)
- **30min**: 61 req, 61×200 = **SR 100.0%**
- 0 错误, 0 fallback, 0 KEYMGR/breaker 事件
- avg duration 24.6s (健康)

### per-key × tier (glm5_2_nv) — 全 success
| key | upstream | result | count |
|-----|----------|--------|-------|
| k0 | nvcf_pexec | pexec_success | 12 |
| k1 | nv_integrate | integrate_success | 10 |
| k2 | nvcf_pexec | pexec_success | 14 |
| k3 | nv_integrate | integrate_success | 11 |
| k4 | nvcf_pexec | pexec_success | 14 |

61 attempts, 0 失败 — pexec+fid1/2/3 (k0/k2/k4) 与 integrate+5IP (k1/k3) 混合链路全健康。

### buffer 机制实证 (nv_gw 日志 --since 30m)
- 大量 `NV-BUFFER-SUCCESS` 1 attempt 即成功 (elapsed 6-18s)
- **1 例 zombie retry 正确恢复**: req=5084c533
  - attempt=1 verdict=zombie_empty reason=total_deadline elapsed=92s (NVCF 返回空流)
  - → `NV-BUFFER-RETRY` + `NV-BUFFER-BACKOFF 5s`
  - → attempt=2 verdict=success_tool_call elapsed=105s 成功 flush 1048b
  - **这证明 buffer 5×90s 重试机制正确捕获 zombie 流并恢复** — 用户可见 200, 非 502
- 0 `NV-WAIT-` (WaitQueue 未触发), 0 `KEYMGR-` (无 key cooling), 0 breaker OPEN

### 注入数据的 1×502 buffer_exhausted 真相
STATE 轮前链路分析注入显示 `cc4101-primary 64×200 + 1×502 buffer_exhausted (dur 409s)`。
核查发现这是 `cc_requests.ts` 时区 bug: 该列存 CST (无时区) 但被注入脚本按 UTC `now()-interval '30 min'` 比较, 导致 CST 06:50 左右的历史 502 被拉进"30min 窗口"。
**真实 30min UTC 窗口 (nv_requests, timestamptz)**: 61×100% SR, 0 错误。
→ 该 502 buffer_exhausted 是历史残留, 不在当前窗口, 不影响判稳。

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok(5keys, glm5_2_nv) + cc4101 ok(primary=glm5_2_nv) + dsv4p_nv40066 ok(5keys) — 全 ok
- `docker ps`: nv_gw Up 5h, cc4101 Up 10h, dsv4p_nv40066 Up 5h, nv_gw_stable Up 2days — 全 Up
- 配置零漂移 (R661 baseline 沿用):
  - nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
  - cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400

## 下一步
- 持续监控 cc2 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- 关注 zombie_empty 频率: 当前 1 例/61 req (~1.6%), buffer retry 100% 恢复 → 健康
- 若 zombie_empty 频率上升 (>10%) 再考虑调 buffer/verdict 参数
- 流量低时不动码, 仅 NOP 记数据
- R661 post-restart ~48h+ 配置稳定, 无新错误类型

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
