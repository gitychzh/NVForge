# R314 — NOP 巡检轮 (2026-08-02 17:54 CST)

## 数据 (30min 注入链路分析 ~17:54)
- cc2 (cc4101-primary): 0 req (session 间歇空闲). 0 fallback 0 deadline.
- dsv4p_nv 全 caller SR=61.5% (8/13), 失败 5 全 all_tiers_exhausted.
  - caller hermes: dsv4p_nv 200×8 + 429×5.
  - 分钟趋势: 09:25/09:30/09:35/09:45/09:50 五波 429 → 09:40-09:41 恢复 8×200.
  - per-key: key2→8×200 (avg_dur 10112); 空 key→5×429 (1553).
  - per-egress: 203.10.96.139→8×100; 空 IP→5×0.
  - finish_reason: tool_calls×7, stop×1 (无 zombie).
  - fallback 0/13.

## 错误分类
- 5 错误: 全 all_tiers_exhausted (sub=all_tiers_failed_in_mapped_tier, avg_dur 1553).
- tier_attempts 30min 0 行 (429 在 NVCF 侧, 未进 nv_gw tier).
- buffer/wait 日志空.
- 错误类型集合与 R268-R313 一致, 无新增.

## 根因 (沿用 R278-R313)
- NVCF function 级配额周期: dsv4p_nv 5key 全绑同一 function, 配额耗尽时 5key 同时 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区 (非代码缺陷).
- 五波 429 后自恢复 (09:40-09:41 恢复), KEYMGR 指数退避 + ProbeWorker 探测唤醒正常.

## 判稳
- NOP 巡检轮. cc2 primary 0 req, 链路空闲健康.
- 错误类型无新增, 与 R268-R313 一致. 四十七轮一致 R268-R314.
- 0 改动 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障再决定介入.

## 参数快照 (无变化, 同 R313)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450,
  NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, TIER_TIMEOUT_BUDGET_S=180.
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_HEADER_TIMEOUT=400,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130,
  CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3.
