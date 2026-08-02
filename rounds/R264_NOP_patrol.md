# R-nvonly-post264 — NOP 巡检轮 (2026-08-02 14:04 CST)

## 本轮改动
无. NOP 巡检轮, 0 改动 0 重启.

## 依据
cc2 (cc4101-primary) 30min 窗口 1 req glm5_2_nv = 1×200 SR=100%, avg_dur 70s.
链路健康: nv_gw /health ok (passthrough, 5 keys, default glm5_2_nv), 全容器 Up 12h+.
0 cc2 tier error, 0 cc2 buffer/wait 日志.

dsv4p_nv 429 (hermes caller, 28×200+2×429 SR=93.3%) 是 NVCF 配额限流, 与 cc2 无关 (cc2 走 glm5_2_nv 不打 dsv4p_nv), 不介入.

## 验证 (14:04 CST)
| 项 | 结果 |
|----|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 12h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 1 req glm5_2_nv = 1×200 100% ✓ |
| 30min cc2 tier error | 0 ✓ |
| 30min cc2 buffer/wait 日志 | 空 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK=ms_gw:40007 ✓ |

## 数据快照 (30min, 注入数据)
- cc4101-primary|glm5_2_nv|200|1 (cc2 唯一 req, 70s)
- hermes|dsv4p_nv|200|12 + 429|2 (非 cc2)
- other|dsv4p_nv|200|16 (非 cc2)
- dsv4p_nv 全 caller SR: 28×200 + 2×429 = 93.3% (30req, 配额限流)
- glm5_2_nv SR=100% (1/1)
- 30min 错误分类: all_tiers_exhausted ×2 (hermes dsv4p_nv, avg 1855ms, 非 cc2)
- fallback 发生率: f=31 (无 fallback, 主链路全扛)
- per-key (dsv4p): key2 15×200, key0/1/4 各 3×200, key3 4×200, 2×429 无 key
- per-egress (dsv4p): 203.10.96.139 15req(100%), 134.195.101.194/120/180/188 各 3-4req(100%)
- finish_reason: length×15 + tool_calls×8 + stop×5 (无 zombie)

## 参数快照 (无变化, 同 post263)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, TIER_COOLDOWN_S=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
继续 NOP 巡检. 等 cc2 流量增多后再判 SR 细节. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
