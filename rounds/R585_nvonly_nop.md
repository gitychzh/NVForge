# R585 (2026-08-03 10:40 CST) — NOP 巡检轮

## 数据 (30min, 10:40 CST)
- cc2 (cc4101-primary): 0 req (session 间歇空闲, 无 cc2 评估样本)
- dsv4p_nv: 8 req, 3×200 + 5×429 (SR=37.5%)
  - vs R584: 71.4% → 37.5% (下滑, 仍在 6h 波动区间 20-55% 内)
  - per-key: key2 3×200 (命中可用 key 100% 200, avg_dur=11798ms, IP 203.10.96.139), 空 key 5×429 (全挂)
  - 唯一错误: all_tiers_exhausted ×5 (avg_dur=1512ms, NVCF 配额型, 非 nv_gw tier 故障)
  - finish_reason: tool_calls×2 + stop×1 (健康, 无 zombie)
- 无 buffer/wait 日志 (30min 无 buffer 触发), 无 stream_total_deadline, 无 zombie
- fallback 发生率 f×8 (cc4101 层 ms_gw 兜底, 预期)

## 判稳
- SR=37.5% < 99%, 但 cc2 0 流量 → 铁律1 (改前有数据) 不满足, 不动码
- dsv4p_nv 8 req 全 NVCF 配额波动型 (命中 key2 时 100% 200, 全挂时空 key 429)
- 6h 趋势: SR 波动 20-55%, 与 R545-R584 同一 NVCF 配额波动模式
- KeyManager 行为正确: 全挂时 all_tiers_exhausted = NVCF 侧拒绝, 非 nv_gw tier 故障
- 无新错误类型, 无参数漂移 → NOP

## 本轮改动
- 无 (NOP). cc2 0 流量, 铁律1 不满足.

## 验证
- 0 restart → 无需 py_compile / curl 复测
- curl /health: status=ok, nv_num_keys=5, models=[kimi_nv,dsv4p_nv,glm5_2_nv]
- docker ps: nv_gw Up 20h, nv_gw_stable Up 33h, cc4101 Up 10h, ms_gw Up 4 days, logs_db Up 4 days

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为
- dsv4p_nv 小时级 SR <60% + cc2 流量恢复 → 评估 TIER_COOLDOWN_S 180s 是否过激
- all_tiers_exhausted 中段不恢复再评估 (当前全 NVCF 配额型)
- 502 (peer-fb-skip) >=6/h + cc2 流量恢复 → 评估 dsv4p_nv fallback 策略
