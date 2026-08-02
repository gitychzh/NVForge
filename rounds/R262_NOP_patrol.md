# R-nvonly-post262 hm2_cc2 NOP patrol

## 时间
2026-08-02 13:58 CST

## 链路数据 (30min 窗口, 轮前注入)
- cc2 (cc4101-primary) 30min: 1 req glm5_2_nv = 1×200 (SR=100%)
  - cc4101-primary|glm5_2_nv|200|1 (avg_dur 70018ms — 单次正常长会话)
- 全 caller dsv4p_nv: 31req (28×200 + 2×429 + 1×502, SR=90.3%)
  - 429 = all_tiers_exhausted (2×, avg 1855ms), 502 = NVStream_IncompleteRead (1×, avg 34130ms)
  - per-key: key2 扛 15×200+1×502, key0/key1 各 3×200, key3 4×200, key4 3×200, 2×429 无 key
  - per-egress: 203.10.96.139 16req(94%), 134.195.101.194 4req(100%), 134.195.101.120/180/188 各 3req(100%)
  - finish_reason: length×15 + tool_calls×9 + stop×4 (无 zombie)
  - fallback 发生率: f=32 (无 fallback, 主链路全扛)
  - **非 cc2 链路** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
- cc2 tier error: 0 rows; buffer/wait 日志: 空

## 健康验证
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv ✓ (同 post261)
- docker ps: nv_gw/cc4101 Up 12h, ms_gw/logs_db Up 3d ✓
- cc2 (cc4101-primary) 30min SR: 1 req glm5_2_nv = 1×100% ✓
- 30min tier error (全 caller): all_tiers_exhausted ×2 + NVStream_IncompleteRead ×1 (hermes dsv4p_nv, 非 cc2) ✓
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 判稳+行动
- cc2 SR=100% (1/1), 0 cc2 error → NOP 巡检轮, 0 改动 0 重启.
- dsv4p_nv hermes 流量 SR=90.3% (28/31), 2×429 all_tiers_exhausted + 1×502 IncompleteRead,
  非 cc2 链路 (cc2 走 glm5_2_nv), 不介入.
- glm5_2_nv 连续 post100-post262 (163 轮) 无 dsv4p 故障扩散.

## 下一步
继续 NOP 巡检. 等 cc2 流量增多后再判 SR 细节. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
