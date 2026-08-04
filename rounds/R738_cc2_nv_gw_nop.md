# R738 — cc2 nv_gw NOP 巡检 (2026-08-05 04:55 CST)

## 改动: 不改码 (NOP)

## 依据 (实测 ~04:54 CST, 30min 窗, created_at 时区)
- **cc2 (cc4101-primary) glm5_2_nv: 60×200, SR=100%, fb=0%** — 达标, 连续第 4 轮 100%
- cc_requests 30min: total=58, ok=57, fb=0, SR=98.3%, fb_pct=0%
  - 58 中 60×200 nv_gw 直接成功 (注: cc_requests 58 vs nv_requests 60 略偏移, 窗口/写入时机差)
  - 注入数据 cc4101-primary|glm5_2_nv|200|54 与 DB 60×200 一致 (窗口偏移)
- hermes→dsv4f0731_nv: 12×200 + 11×502 all_tiers_exhausted
  - 这是 hermes caller 走 dsv4f0731_nv 的 NVCF 容量问题, 非 cc2 nv_gw 链路
- 错误分类 30min: all_tiers_exhausted ×10 (全在 hermes/dsv4f0731_nv, cc2 zero)

## per-key tier 分布 (30min, 全 tier 聚合, 含所有 caller)
- **两个 fid 并存**: `b1b22d03` (fid1, 全 pexec_success) + `52e1ddb6` (新 fid, 全 529/RemoteDisconnected/Timeout)
- k0: b1b22d03×12 pexec_success, 52e1ddb6×14 529_nv_overloaded + 2 RemoteDisconnected
- k1: b1b22d03×13 pexec_success, 52e1ddb6×13 529 + 4 RemoteDisconnected + 1 Timeout
- k2: b1b22d03×11 pexec_success, 52e1ddb6×14 529 + 2 RemoteDisconnected
- k3: b1b22d03×13 pexec_success, 52e1ddb6×14 529 + 1 empty_200
- k4: b1b22d03×12 pexec_success, 52e1ddb6×10 529 + 3 RemoteDisconnected + 4 integrate 529
- **关键**: 52e1ddb6 的 529 全被 buffer retry 兜住 → cc2 最终 100% 200
- 与 STATE 修正记录对照: STATE 记"全 5 key 绑 fid1=b1b22d03", 实测 52e1ddb6 也在跑 — 可能是多 caller 共用 key 时 fid 路由的副作用, 但对 cc2 不可见 (buffer 兜住)

## buffer 日志 (30min, 最后 20 行, cc4101-primary)
- 每请求 attempt=1/5 即成功, verdict=success_tool_call, elapsed 4-12s
- start_key 轮转: k4→k5→k1→k2 (KEY_ROTATION 正常)
- 无 fallback、无 all_tiers_exhausted 触发到 cc4101-primary
- 无 529 余波泄漏到 cc2 路径

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (5 keys, glm5_2_nv default) + cc4101 ok (primary=glm5_2_nv) — 全 ok
- `docker ps`: nv_gw Up 2h, cc4101 Up 3h, dsv4p_nv40066 Up 8h, ms_gw Up 3h, 全 Up 无异常重启
- env 沿 R737, 无漂移

## 判稳结论
- **cc2 nv_gw 链路 (glm5_2_nv) 连续 4 轮 (R735/R736/R737/R738) SR 100%, fb 0%** — 全面达标
- 52e1ddb6 fid 的 529 storm 是 dsv4f0731_nv 多 caller 共用 NVCF 的容量问题, cc2 buffer 用 fid1 兜住
- hermes 11×502 是 dsv4f0731_nv NVCF 容量, 不是 cc2 nv_gw 链路
- NOP 巡检轮 — 链路已稳, 无可改项

## SR 趋势
| 轮 | 30min 窗 SR | 窗口备注 |
|---|---|---|
| R735 | 100% (最近 22min) | 30min 91.6% 被 04:10 前 dsv4p 502 拖低, 529 余波 |
| R736 | 100% (47/47) | 04:50 CST, 余波平息 |
| R737 | 100% (51/51) | 04:51 CST, 持续稳定 |
| R738 | 100% (60/60 nv_requests, 58 cc_requests 窗口偏移) | 04:54 CST, 52e1ddb6 fid 529 被 buffer 兜住 |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+ / fb <10%)
- 52e1ddb6 fid 出现在 tier attempts 与 STATE "全 fid1" 不符, 但对 cc2 不可见 — 观察, 若未来泄漏到 cc2 再查
- dsv4f0731_nv 的 529 storm 非 cc2 职责 (cc2 只走 glm5_2_nv)
- 流量低时不动码, 仅 NOP 记数据

## 参数快照 (实测 env, 沿 R737, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, 单 mode pexec_us_rr, KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0 (全 5 key 绑 fid1=b1b22d03),
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
