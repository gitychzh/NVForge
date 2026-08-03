# R721 — cc2/HM2 NOP 巡检轮 (2026-08-03 20:11 CST)

## 结论: NOP 不改码

cc2 本窗口零流量 (连续第 6 轮), 无数据不动手。链路兜底健康。

## 30min 数据 (注入, ~19:41-20:11 CST)

### 模型成功率
- dsv4p_nv: 64×200 + 1×502 = **SR 98.5%** (64/65) — 兜底链路继续回升 (R718 91.3%→R719 93.1%→R720 97.7%→R721 98.5%)
- glm5_2_nv: 4×200 + 2×502 = **SR 66.7%** (4/6) — 持平 R720, 六轮趋势 0%→50%→57.1%→57.1%→66.7%→66.7% 恢复停滞

### caller 分布 (全非 cc2)
- hermes|dsv4p_nv: 49×200 + 1×502
- hermes|glm5_2_nv: 4×200 + 2×502
- other|dsv4p_nv: 15×200

### 错误分类 (无新类型)
- NVStream_IncompleteRead × 1 (avg_dur 78s) — mid-stream 断流
- all_tiers_exhausted|all_tiers_failed_in_mapped_tier × 1 (avg_dur 90s) — 5key 全挂
- stream_absolute_cap × 1 (avg_dur 187s) — 绝对时长封顶

### tier 错误 (全 NVCF 上游配额副作用)
- k1: IntegrateRemoteDisconnected × 1
- k2: pexec_500 × 1, pexec_conn_RemoteDisconnected × 4, pexec_success × 1
- k3: IntegrateRemoteDisconnected × 1
- k4: IntegrateRemoteDisconnected × 1

### per-key (dsv4p) 均衡
- k0 13×200, k1 13×200, k2 13×200, k3 13×200, k4 12×200

### per-egress-IP 全 100%
- 134.195.101.180/188/194/120 + 203.10.96.139 各 12-13×200

### dsv4p 200 延迟/token
- avg_dur 7377ms, max 27511ms, min 1430ms, ttfb 6885ms, avg_in 2 tok, avg_out 11 tok
- finish_reason: tool_calls×44, stop×13, length×7 (无 zombie)

### fallback
- f×71 (全非 cc2, hermes 流量)

### buffer/wait/keymanager 日志: 无 (无 buffer 触发)

## 健康验证 (NOP 无需 restart)
- nv_gw: ok (5keys, glm5_2_nv/dsv4p_nv/kimi_nv)
- cc4101: ok (primary=glm5_2_nv)
- dsv4p_nv40066: ok (5keys)
- docker ps: nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 5h, nv_gw_stable Up 42h, logs_db Up 4d

## 根因
glm5_2_nv NVCF 上游缓慢恢复中 (R720 66.7%→R721 66.7% 持平, 恢复停滞), cc4101 fallback → dsv4p 兜底, cc2 本窗口零流量。所有 tier 错误均为 NVCF 上游配额副作用, 非 nv_gw 可控。

## 下一步
- 持续监控 cc2 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- glm5_2_nv NVCF 上游恢复停滞于 66.7%, 继续观察是否突破稳态
- 若 cc2 流量恢复后 fallback 率 >10% 再深入查 glm5_2_nv tier
- R661 post-restart ~42h+ 仍无新错误类型, 配置稳定

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
