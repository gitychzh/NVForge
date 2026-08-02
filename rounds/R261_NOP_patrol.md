# R-nvonly-post261 hm2_cc2 NOP patrol

## 时间
2026-08-02 13:55 CST

## 链路数据 (30min 窗口, 轮前注入)
- cc2 (cc4101-primary) 30min: 1 req glm5_2_nv = 1×200 (SR=100%)
  - cc4101-primary|glm5_2_nv|200|1 (avg_dur 70018ms — 单次正常长会话)
- 全 caller dsv4p_nv: 24req (20×200 + 3×429 + 1×502, SR=83.3%)
  - 429 = all_tiers_exhausted (3×, avg 1762ms), 502 = NVStream_IncompleteRead (1×, avg 34130ms)
  - per-key: key2 扛 11×200+1×502, key0/key1 各 2×200, key3 3×200, key4 2×200, 3×429 无 key
  - per-egress: 203.10.96.139 12req, 134.195.101.194 3req, 其余 IP 各 2req
  - finish_reason: length×10 + tool_calls×7 + stop×3 (无 zombie)
  - fallback 发生率: f=25 (无 fallback, 主链路全扛)
  - **非 cc2 链路** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
- cc2 tier error: 0 rows; buffer/wait 日志: 空

## 健康验证
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv ✓
- docker ps: nv_gw/cc4101/nv_gw_stable Up 12h, ms_gw/logs_db Up 3d ✓
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK=ms_gw:40007 ✓

## 本轮改动
0 改动, 0 重启. NOP 巡检轮.

## 依据
cc2 (cc4101-primary) 30min 1 req glm5_2_nv = 1×200 SR=100%, 链路健康无故障,
无 cc2 tier error/buffer/wait 日志.
dsv4p_nv (hermes caller) SR=83.3% 是 NVCF dsv4p 配额限流 (3×all_tiers_exhausted + 1×IncompleteRead),
非 cc2 链路, 不介入.
glm5_2_nv 连续 post100-post260 (161 轮) 无 dsv4p 故障扩散.

## 下一步
继续 NOP 巡检. 等 cc2 流量增多后再判 SR 细节. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
