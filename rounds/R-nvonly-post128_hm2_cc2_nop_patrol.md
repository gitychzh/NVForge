# R-nvonly-post128 — hm2_cc2 NOP 巡检轮 (2026-08-02 07:44 CST)

## 基线
- 主仓 git HEAD: 730ae84 (post127) 已 push origin master
- 本轮: NOP 巡检轮, 0 改动, 0 重启

## 数据 (30min 窗口, 注入)
- cc2 (cc4101-primary): 0 req (session 轮前无流量, 链路健康无故障)
- hermes|dsv4p_nv: 3×200 + 5×429, SR=37.5% (all_tiers_exhausted, 5key 全挂, 周期性 5min 一发)
  - 与 cc2 无关 (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
  - 30min fallback f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作)
- dsv4p 200 延迟 avg 15377ms, finish_reason: tool_calls×2 + stop×1
- 0 stream_total_deadline (6h), 0 cc2 tier error, 0 cc2 buffer/wait 日志

## 健康验证 (07:44 CST)
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv ✓
- docker ps: nv_gw/cc4101 Up 6h, ms_gw/logs_db Up 2d ✓
- env: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), buffer 5×90s=450s, cc4101 deadline 470s ✓

## 判稳
SR 数据 = 0 req (无流量), 链路健康无故障, 无新错误 → NOP 巡检轮.
dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责.
glm5_2_nv 链路连续 post100-post128 (29 轮) 稳定.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流属 NVCF 侧, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
