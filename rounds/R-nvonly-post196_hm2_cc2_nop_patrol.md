# R-nvonly-post196 hm2_cc2 NOP patrol (2026-08-02 11:30 CST)

## 本轮判定: NOP 巡检轮 (0 改动, 0 重启)

### 依据
- cc2 (cc4101-primary) 30min 窗口 0 req — session 轮前无流量产生, 无数据可判 SR.
- 链路健康无故障: nv_gw /health ok (5 keys, passthrough, default glm5_2_nv),
  全容器 Up 9h+, 0 cc2 tier error, 0 cc2 buffer/wait/error 日志.
- hermes 打 dsv4p_nv 6×429 all_tiers_exhausted (NVCF 侧 dsv4p 配额限流),
  openclaw 打 dsv4p_nv 1×200 — **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
- glm5_2_nv 连续 post100-post196 (97 轮) 无 dsv4p 故障扩散.

### 30min 链路总览
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |
| openclaw | dsv4p_nv | 200 | 1 |
- cc2 (cc4101-primary): 0 req (无流量)
- 全 caller dsv4p_nv SR=14.3% (1/7), 全为 NVCF 配额限流, 非 cc2 链路.

### 30min 错误分类
- all_tiers_exhausted|all_tiers_failed_in_mapped_tier × 6 (hermes→dsv4p_nv 限流)
- cc2 tier error: 0

### 健康验证 (11:30 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 9h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康) ✓ |
| 30min tier error (cc2) | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 改动
无 (NOP 巡检轮).

## 验证
无改动 → 无 restart / 无 py_compile.
链路健康确认: /health ok + docker ps 全 Up.

## 参数快照 (无变化, 同 post195)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
