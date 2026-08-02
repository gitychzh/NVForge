# R300 — NOP 巡检轮 (2026-08-02 17:01 CST)

## 链路状态
- 容器: nv_gw Up 15h, cc4101 Up 3h, nv_gw_stable Up 15h, ms_gw/logs_db Up 3 days 全 Up.
- /health 200, nv_num_keys=5, default glm5_2_nv.

## 本轮数据 (30min 实时链路分析注入 ~17:01)
- cc2 (cc4101-primary) 30min 0 req (session 间歇空闲). 0 fallback 0 deadline.
- dsv4p_nv 30min 全 caller SR=95.0% (19/20), 失败 1 全 `all_tiers_exhausted` (avg_dur 1875).
- per-key: key2 → 19×200 + 1×429. per-egress: 203.10.96.139 → 19×100.
- 200 延迟: avg 11208 / max 30071 / min 4145; ttfb 10796; finish_reason: tool_calls×15, stop×4.
- 分钟趋势: 08:35 200×1, 08:36 200×2, 08:40 429×1, 08:45 200×2, 08:46 200×1,
  08:50 200×2, 08:51 200×1, 08:55 200×2, 08:56 200×3, 09:00 200×3, 09:01 200×2.
- 典型 NVCF function 配额周期自恢复 (08:40 一波 429 → 08:45-09:01 多波 200 恢复).
- buffer/wait/keymanager 日志 30min 空 (无 buffer 流量).
- fallback 0/20. tier_attempts 30min 0 行 (function 级 429 不产生 tier attempt).

## 判稳
- NOP 巡检轮. cc2 primary 0 req 不受影响.
- dsv4p_nv SR=95.0% 是 NVCF function 级配额周期, 自恢复, 非 nv_gw 代码缺陷.
- 错误类型无新增, 全 all_tiers_exhausted, 与 R268-R299 一致.

## 根因 (沿用 R278-R299 分析)
- dsv4p_nv 5key 全绑同一 NVCF function. function 配额耗尽时 5key 同时 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 未覆盖 function 级配额 (设计盲区非代码缺陷).
- 当前 cc2 流量极低, buffer_exhausted 罕见且自恢复, 不达介入阈值.

## 改动
- 0 改动 0 restart. 三十三轮一致 R268-R300.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
