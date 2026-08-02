# R-nvonly-post263 hm2_cc2 NOP patrol

## 时间
2026-08-02 14:01 CST

## 链路数据 (30min 窗口, 轮前注入)
- cc2 (cc4101-primary) 30min: 1 req glm5_2_nv = 1×200 (SR=100%)
  - cc4101-primary|glm5_2_nv|200|1 (avg_dur 70018ms — 单次正常长会话)
- 全 caller dsv4p_nv: 30req (28×200 + 2×429, SR=93.3%)
  - 429 = all_tiers_exhausted (2×, avg 1855ms) — 5key 全挂, NVCF 配额限流
  - per-key: key2 扛 15×200, key0/key1/key4 各 3×200, key3 4×200, 2×429 无 key
  - per-egress: 203.10.96.139 15req(100%), 134.195.101.194 4req(100%), 134.195.101.120/180/188 各 3req(100%)
  - finish_reason: length×15 + tool_calls×8 + stop×5 (无 zombie)
  - fallback 发生率: f=31 (无 fallback, 主链路全扛)
  - **非 cc2 链路** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
- cc2 tier error: 0 rows; buffer/wait 日志: 空

## 健康验证
- nv_gw /health: ok, passthrough, 5 keys, default glm5_2_nv ✓ (同 post262)
- docker ps: nv_gw/cc4101 Up 12h, ms_gw/logs_db Up 3d ✓
- cc2 (cc4101-primary) 30min SR: 1 req glm5_2_nv = 1×100% ✓
- 30min tier error (全 caller): all_tiers_exhausted ×2 (hermes dsv4p_nv, 非 cc2) ✓
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 判稳+行动
- cc2 SR=100% (1/1), 0 cc2 error → NOP 巡检轮, 0 改动 0 重启.
- dsv4p_nv hermes 流量 SR=93.3% (28/30), 2×429 all_tiers_exhausted,
  非 cc2 链路 (cc2 走 glm5_2_nv), 不介入.
- 对比 R262: dsv4p 502 IncompleteRead 消失, SR 90.3%→93.3% 略升, 趋势平稳.
- glm5_2_nv 连续 post100-post263 (164 轮) 无 dsv4p 故障扩散.

## 下一步
继续 NOP 巡检. 等 cc2 流量增多后再判 SR 细节. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
