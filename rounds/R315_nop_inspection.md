# R315 — NOP 巡检轮 (2026-08-02 17:57 CST)

## 数据 (30min 注入链路分析 ~17:57)
- cc2 (cc4101-primary): 0 req (session 间歇空闲). 0 fallback 0 deadline.
- dsv4p_nv 全 caller SR=73.3% (11/15), 失败 4 全 all_tiers_exhausted.
  - caller hermes: dsv4p_nv 200×11 + 429×4.
  - 分钟趋势: 09:30/09:35/09:45/09:50 四波 429 → 09:40-09:41 恢复 8×200 + 09:55-09:56 恢复 3×200.
  - per-key: key2→11×200 (avg_dur 11554); 空 key→4×429 (1675).
  - per-egress: 203.10.96.139→11×100; 空 IP→4×0.
  - finish_reason: tool_calls×9, stop×2 (无 zombie).
  - fallback 0/15.

## 错误分类
- 4 错误: 全 all_tiers_exhausted (sub=all_tiers_failed_in_mapped_tier, avg_dur 1675).
- tier_attempts 30min 0 行 (429 在 NVCF 侧, 未进 nv_gw tier).
- buffer/wait 日志空.
- 错误类型集合与 R268-R314 一致, 无新增.

## 根因 (沿用 R278-R314)
- NVCF function 级配额周期: dsv4p_nv 5key 全绑同一 function, 配额耗尽时 5key 同时 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区 (非代码缺陷).
- 四波 429 后自恢复 (09:40-09:41+09:55-09:56 恢复), KEYMGR 指数退避 + ProbeWorker 探测唤醒正常.

## 判稳
- NOP 巡检轮. cc2 primary 0 req, 链路空闲健康.
- 错误类型无新增, 与 R268-R314 一致. 四十八轮一致 R268-R315.
- 0 改动 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
