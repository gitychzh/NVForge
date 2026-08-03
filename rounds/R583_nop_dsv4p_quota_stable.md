# R583 — NOP 巡检轮 (2026-08-03 10:30 CST)

## 数据 (30min, 10:30 CST)
- cc2 (cc4101-primary): 0 req (session 间歇空闲, 铁律1 不满足)
- dsv4p_nv: 14 req, 10×200 + 4×429 (SR=71.4%)
- 唯一错误: `all_tiers_exhausted` ×4 (avg_dur=1515ms, NVCF 配额型)
- nv_tier_attempts: 0 行 (KeyManager 全局冷却在 tier 层前拦截)
- 429 全在空 key/空 IP = NVCF 侧拒绝 (配额波动)
- key2: 10×200 (命中可用 key 时 100% 200, avg_dur=10388ms, IP 203.10.96.139)
- finish_reason: tool_calls×8 + stop×2 (健康, 无 zombie)
- 无 buffer/wait 日志, 无 stream_total_deadline

## 6h 趋势 (dsv4p_nv, 按小时)
- 08-02 19:00 ~ 08-03 01:00: SR 20%-55% 波动, 命中 key2 时 100% 200
- 与 R575-R582 完全一致模式 = NVCF 配额型波动, 非 nv_gw tier 故障

## 判稳
- cc2 0 流量 → 铁律1 不满足 → 不动码 (NOP)
- dsv4p_nv SR 上扬 (58.3%→71.4%) = NVCF 配额波动区间内, 非修复信号
- 无新错误类型, 无参数漂移 → 无介入必要

## 本轮改动
- 无

## 验证
- curl /health: ok, nv_num_keys=5, models=[kimi_nv,dsv4p_nv,glm5_2_nv]
- docker ps: nv_gw Up 20h, cc4101 Up 10h, ms_gw Up 4 days, logs_db Up 4 days

## 对比 R582
- SR: 58.3% → 71.4% (上扬, 波动区间内)
- 错误类型: 不变 (all_tiers_exhausted NVCF 配额型)
- 配置: 不变, 无漂移

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径
- 关注新错误类型或 key/IP 级故障再决定介入
