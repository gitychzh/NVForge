# R316 — NOP 巡检轮 (2026-08-02 18:00 CST)

## 数据 (30min 实时链路分析注入 ~18:00)

### cc2 (cc4101-primary) 30min 0 req
- session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait 日志 (BUFFER-/WAIT-) 30min 空 (无 buffer 流量).

### dsv4p_nv 30min 全 caller SR=78.6% (11/14)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 11 |
| hermes | dsv4p_nv | 429 | 3 |

per-key (dsv4p): key2 → 11×200 (avg_dur 11554), 空 key → 3×429 (1922).
per-egress: 203.10.96.139 → 11×100, 空 IP → 3×0 (429).
finish_reason: tool_calls×9, stop×2 (无 zombie).
分钟趋势: 09:35/09:45/09:50 三波 429, 09:40-09:41 恢复 8×200 + 09:55-09:56 恢复 3×200 (配额周期自恢复).
fallback 0/14.

### 错误分类
- 3 错误: 全 all_tiers_exhausted (avg_dur 1922, sub=all_tiers_failed_in_mapped_tier).
- tier_attempts 30min 0 行 (429 在 NVCF 侧, 未进入 nv_gw tier 重试).

## 根因 (沿用 R278-R315)
- NVCF 429 是 function 级配额: 配额耗尽时 5key 同时收 429 → all_tiers_exhausted.
- buffer 5key 轮转对 function 级 429 失效 (设计盲区非代码缺陷, R-nvonly 5key5IP 针对 key/IP 级隔离).
- 09:35+09:45+09:50 三波 429 自恢复 (09:40-09:41 + 09:55-09:56 恢复 11×200).
- KEYMGR 指数退避 (120→180→480s) + ProbeWorker 探测唤醒正常工作.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv SR=78.6% (11/14): 窗口命中三波 429, req 数少故 SR 偏低, 根因不变.
- 错误类型无新增 (全 all_tiers_exhausted), 与 R268-R315 一致.
- 四十九轮一致 R268-R316.

## 改动
- 0 改动 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.

## 参数快照 (无变化, 同 R315)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv.
- cc4101: FALLBACK_UPSTREAM_URL=ms_gw:40007, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130.
