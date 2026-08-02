# R325 — NOP 巡检轮 (2026-08-02 18:33 CST)

## 链路状态
- cc2 (cc4101-primary) 30min **0 req** (session 间歇空闲, 同 R275-R324).
- dsv4p_nv 30min 全 caller **SR=83.3% (20/24)**, 失败 4.
- 0 fallback / 0 deadline / 0 restart / 0 改动.

## 失败明细 (4)
| error_type | sub | count | avg_dur |
|---|---|---|---|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 3 | 3439 |
| NVStream_IncompleteRead | (空) | 1 | 33960 |

## per-key / per-egress
- key2 → 20×200 (avg_dur 10310) + 1×502 (33960); 空 key → 3×429 (3439).
- 203.10.96.139 → 21×95; 空 IP → 3×0 (429).
- 200 finish_reason: tool_calls×18, stop×2 (无 zombie).
- 200 延迟: avg_dur 10310, max 22797, min 3038, avg_ttfb 10010.

## 分钟趋势
- 10:05-10:20 恢复 20×200 (配额周期自恢复).
- 10:21-10:30 一波 429×3 → all_tiers_exhausted (NVCF function 配额周期, 5key 同 function 同时挂).
- 10:06 1×502 NVStream_IncompleteRead (mid-stream 软挂单发, 历史偶发).

## 健康检查 (18:33 实测)
- /health 200: nv_num_keys=5, default glm5_2_nv, pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv].
- 容器全 Up: nv_gw/cc4101 Up 4h, nv_gw_stable Up 17h, ms_gw/logs_db Up 3d.

## 根因 (沿用 R278-R324)
- all_tiers_exhausted = dsv4p_nv 5key 全绑同一 NVCF function, function 配额耗尽时 5key 同时 429.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区 (非代码缺陷).
- NVStream_IncompleteRead 单发 mid-stream 软挂, nv_breaker 未累积到 OPEN, 历史偶发.
- cc2 流量极低, all_tiers_exhausted 罕见且自恢复, 不达介入阈值.

## 判稳
- NOP 巡检轮. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- 错误类型无新增, 与 R268-R324 一致. **五十八轮一致 R268-R325.**

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted/NVStream_IncompleteRead) 或 key/IP 级故障, 再决定介入.
