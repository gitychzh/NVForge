# R727 (cc2/HM2): NOP 巡检轮

> 2026-08-03 20:50 CST | 容器: nv_gw Up 5h, cc4101 Up 5h, dsv4p_nv40066 Up 5h

## 改动: 不改码 (NOP)

## 依据 (30min 窗口)
- **cc2 (cc4101-primary) 30min**: 零流量 (连续零流量streak终结于R725后又归零)
- **nv_gw 全量 30min**: dsv4p_nv 61×200 = SR **100.0%** (hermes caller, 非 cc2)
  - glm5_2_nv 0 req
- **错误分类 30min**: 0 错误 (无新错误类型)
- **tier attempts 30min**: 0 行 (glm5_2_nv 无 tier 流量)
- **buffer/wait 日志**: 0 行 (无触发)
- **per-key (dsv4p)**: k0=14, k1=11, k2=14, k3=12, k4=10 — 均衡, 全 200
- **per-egress-IP**: 5 US IPv4 全 100% (134.195.101.180/203.10.96.139/134.195.101.194/134.195.101.188/134.195.101.120)
- **dsv4p 延迟**: avg 6.8s, max 35.6s, ttfb 6.5s — 正常
- **finish_reason**: tool_calls×27, stop×26, length×8 — 无 zombie

## 根因分析
- cc2 本轮零流量 = 用户无请求, 非链路故障 (R725 流量16req→R726 16req→R727 0req 波动正常)
- dsv4p_nv 100% SR (主力稳定 tier), glm5_2_nv 零请求 — 无数据可判
- fallback 全 61×f (非 cc2, hermes caller) — cc2 无 fallback 事件

## 验证: NOP 无需 restart
- `/health`: nv_gw ok(5keys) + cc4101 ok(primary=glm5_2_nv) + dsv4p_nv40066 ok(5keys) — 全 ok
- `docker ps`: nv_gw Up 5h, cc4101 Up 5h, dsv4p_nv40066 Up 5h, nv_gw_stable Up 43h, logs_db Up 4d — 全 Up
- 配置零漂移 (R661 baseline 沿用)

## 下一步
- 持续监控 cc2 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- glm5_2_nv 流量恢复后深入查 6h SR 60.4% 根因 (k2 pexec conn_RD 持续重灾)
- R661 post-restart ~43h+ 配置稳定, 无新错误类型

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
