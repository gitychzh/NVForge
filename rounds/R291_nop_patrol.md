# R291 — NOP 巡检轮 (2026-08-02 16:29 CST)

## 基线
- 接 R290. 主仓 main `2b11cc4` (R290 round), 本仓 master `ed3eed3` (post290 STATE).
- 注入数据 16:29 CST 30min 窗口, 系统稳态延续, 与 R268-R290 现象一致.

## 本轮数据 (30min 实时 DB ~16:29 CST)

### 1. cc2 (cc4101-primary) 30min 0 req
- session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- nv_tier_attempts 30min 0 条; cc_requests stream_total_deadline 6h 0 条.

### 2. dsv4p_nv 全 caller 30min
| status | count | 备注 |
|---|---|---|
| 200 | 5 | hermes(4) + other(1) |
| 502 | 21 | all_tiers_exhausted (cooling 窗口瞬拒) |
| 429 | 6 | 边界点配额 |

SR=15.6% (5/32), 失败 27 全 `all_tiers_exhausted`.

### 3. 错误分类
- 全 `all_tiers_exhausted` (20 + 7 all_tiers_failed_in_mapped_tier), 无新错误类型, 与 R268-R290 一致.

### 4. 健康检查
- `curl /health` → ok, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv].
- docker ps: cc4101/nv_gw (Up 2h), nv_gw_stable (Up 15h), ms_gw/logs_db (Up 3 days) 全 Up.
- buffer/wait/keymanager 日志 30min 空 (无 buffer 流量).

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 失败全在 hermes/other caller 打 NVCF function 级配额边界, 非 nv_gw 代码缺陷.
- 错误类型无新增, 全 all_tiers_exhausted, 与 R268-R290 一致.
- 0 改动 0 restart.
- 二十四轮一致 R268-R291.

## 根因 (沿用 R278-R290 分析, 设计盲区非代码缺陷)
- dsv4p_nv 5key (k0-k4) 全绑同一 NVCF function. NVCF 429 配额是 function 级.
- function 配额耗尽时 5key 同时 429 → all_tiers_exhausted.
- buffer 5key 轮转对 function 级 429 失效 (设计盲区, 非 nv_gw 代码缺陷).
- cc2 流量极低, 命中 function 配额边界概率远低于 hermes 高频探测, buffer_exhausted 罕见且自恢复.

## 下一步
- 继续 NOP 巡检. 关注: (1) cc2 流量恢复后 buffer_exhausted 是否复发; (2) dsv4p_nv function 级配额新边界点; (3) 新错误类型.
- 若 cc2 流量恢复且 buffer_exhausted 高频复发, 再考虑介入 (function 级配额检测/等待策略).

## 参数快照 (沿用 R290, 无变更)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_FORCE_STREAM_UPGRADE=0, MIN_OUTBOUND_INTERVAL_S=10
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_MODEL=glm5_2_ms
- settings.json: API_TIMEOUT_MS=600000, contextWindow=170000, autoCompactWindow=155000
