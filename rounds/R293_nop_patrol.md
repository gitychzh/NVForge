# R293 — NOP 巡检轮 (2026-08-02 16:37 CST)

## 判稳: NOP
- cc2 (cc4101-primary) 30min **0 req**, session 间歇空闲, 与 R275-R292 一致.
- 链路空闲健康: 0 fallback 0 deadline, buffer/wait/keymanager 日志空.
- 错误类型无新增, 全 `all_tiers_exhausted`, 与 R268-R292 一致.
- 0 改动 0 restart.

## 本轮关键数据 (30min 链路分析注入 ~16:37 CST)

### 1. cc2 (cc4101-primary) 30min 0 req
- 同 R275-R292, session 间歇空闲. 0 fallback 0 deadline.

### 2. dsv4p_nv 30min 全 caller SR=37.5% (3/8)
| status | count | 备注 |
|---|---|---|
| 200 | 3 | key2 egress 203.10.96.139 健康 |
| 429 | 5 | function 级配额边界 (08:10-08:30 连续) |

按分钟趋势 (自恢复铁证):
- 08:10/08:15/08:20/08:25/08:30 → 5×429 (NVCF function 配额耗尽窗口)
- 08:35 → 1×200, 08:36 → 2×200 (配额恢复, 自恢复)

per-key × status: key2 → 3×200 (avg_dur 16032) + 5×429
per-egress: 203.10.96.139 → 3×100 (hermes key2 egress 100% SR)

### 3. 错误分类
- 全 `all_tiers_exhausted` (5 条, avg_dur 2091ms), 无新错误类型.
- fallback 0/8.

### 4. 健康检查
- `curl /health` → ok, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv].
- docker ps: cc4101/nv_gw (Up 2h), nv_gw_stable (Up 15h), ms_gw/logs_db (Up 3 days) 全 Up.

## 根因 (沿用 R278-R292, 设计盲区非代码缺陷)
- dsv4p_nv 5key (k0-k4) 全绑同一 NVCF function.
- NVCF 429 配额是 function 级: function 配额耗尽时 5key 同时 429 → all_tiers_exhausted.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 是已知盲区.
- 08:10-08:30 连续 429 → 08:35-08:36 恢复 200, 证明是 NVCF function 配额周期自恢复, 非 nv_gw 代码缺陷.

## 下一步
- 继续 NOP 巡检. 关注: (1) cc2 流量恢复后 buffer_exhausted 是否复发高频;
  (2) dsv4p_nv function 级配额边界点; (3) 新错误类型.
- 二十六轮一致 R268-R293.

## 参数快照 (沿用 R292, 无变更)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180,
  NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_FORCE_STREAM_UPGRADE=0,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150,
  CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms
