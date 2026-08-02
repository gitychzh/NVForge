# R298 — NOP 巡检轮 (2026-08-02 16:55 CST)

## 链路状态
- 容器: nv_gw Up 2h, cc4101 Up 3h, ms_gw/logs_db Up 3 days 全 Up.
- /health 200, nv_num_keys=5, default glm5_2_nv.

## 本轮数据 (30min 实时链路分析注入 ~16:55)
- cc2 (cc4101-primary) 30min 0 req (session 间歇空闲). 0 fallback 0 deadline.
- dsv4p_nv 30min 全 caller SR=75.0% (9/12), 失败 3 全 `all_tiers_exhausted`.
- per-key: key2 → 9×200 + 3×429. per-egress: 203.10.96.139 → 9×100.
- 分钟趋势: 08:25 429, 08:30 429 → 08:35-08:36 恢复 200 → 08:40 429 → 08:45-08:51 恢复 200.
- 典型 NVCF function 配额周期自恢复 (429 → cooling → decay → reset → 200).
- buffer/wait/keymanager 日志 30min 空 (无 buffer 流量).
- fallback 0/12.

## 判稳
- NOP 巡检轮. cc2 primary 0 req 不受影响.
- dsv4p_nv 低 SR 是 NVCF function 级配额周期, 自恢复, 非 nv_gw 代码缺陷.
- 错误类型无新增, 全 all_tiers_exhausted, 与 R268-R297 一致.

## 根因 (沿用 R278-R297 分析)
- dsv4p_nv 5key 全绑同一 NVCF function. function 配额耗尽时 5key 同时 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 未覆盖 function 级配额 (设计盲区非代码缺陷).
- 当前 cc2 流量极低, buffer_exhausted 罕见且自恢复, 不达介入阈值.

## 改动
- 0 改动 0 restart. 三十一轮一致 R268-R298.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
