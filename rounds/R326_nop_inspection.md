# R326 — NOP 巡检轮 (2026-08-02 18:38 CST)

## 链路状态
- cc2 (cc4101-primary) 30min **0 req** (session 间歇空闲, 同 R275-R325).
- dsv4p_nv 30min 全 caller **SR=78.9% (15/19)**, 失败 4.
- 0 fallback / 0 deadline / 0 restart / 0 改动.

## 失败明细 (4)
| error_type | sub | count | avg_dur |
|---|---|---|---|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 4 | 2907 |

## per-key / per-egress
- key2 → 15×200 (avg_dur 10688); 空 key → 4×429 (2907).
- 203.10.96.139 → 15×100; 空 IP → 4×0 (429).
- 200 finish_reason: tool_calls×13, stop×2 (无 zombie).
- 200 延迟: avg_dur 10688, max 22797, min 3038, avg_ttfb 10339.

## 分钟趋势
- 10:10-10:20 恢复 15×200 (配额周期自恢复).
- 10:21-10:35 一波 429×4 → all_tiers_exhausted (NVCF function 配额周期, 5key 同 function 同时挂).
- 本轮无 NVStream_IncompleteRead (R325 有 1, 本轮 0).

## 健康检查 (18:33 上轮实测, 本轮容器时间未变 18:37)
- /health 200: nv_num_keys=5, default glm5_2_nv, pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv].
- 容器全 Up: nv_gw 17h, cc4101 4h, nv_gw_stable/ms_gw/logs_db 持续.

## 根因 (沿用 R278-R325)
- all_tiers_exhausted = dsv4p_nv 5key 全绑同一 NVCF function, function 配额耗尽时 5key 同时 429.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区 (非代码缺陷).
- 本轮 10:21-10:35 一波 429×4 证明是 NVCF function 配额周期自恢复, 非 nv_gw 代码缺陷.
- KEYMGR 指数退避 (120→180→480s) 正常工作, 429 后 key 进入冷却, 配额恢复后 ProbeWorker 探测唤醒.
- cc2 流量极低 (0 req), all_tiers_exhausted 罕见且自恢复, 不达介入阈值.

## 判稳
- NOP 巡检轮. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 本轮 SR=78.9% (15/19) 偏低因窗口命中 1 波 429×4 且总 req 少 (19), 根因不变.
- 错误类型无新增, 与 R268-R325 一致. **五十九轮一致 R268-R326.**

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted/NVStream_IncompleteRead) 或 key/IP 级故障, 再决定介入.
