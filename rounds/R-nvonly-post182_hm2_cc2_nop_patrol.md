# R-nvonly-post182 — hm2 cc2 NOP 巡检轮

## 元信息
- 轮号: R-nvonly-post182
- 主机: HM2 (100.109.57.26, opc2_uname)
- 方向: R-nvonly (ms_gw fallback 已恢复, NVU_DISABLE_MS_FALLBACK=0)
- 时间: 2026-08-02 10:35 CST
- 上轮: R-nvonly-post181 (9h ago)

## 本轮判定: NOP 巡检轮 (无改动, 无重启)

### 依据
1. **cc2 (cc4101-primary) 30min 窗口 = 0 req** — 本轮 session 轮前无 cc2 流量产生, 无数据可判 cc2 SR.
   链路健康无故障: nv_gw /health ok (5 keys, passthrough, default glm5_2_nv),
   0 cc2 tier error, 0 cc2 buffer/wait/error 日志.
2. **唯一流量 hermes→dsv4p_nv (9req, 4×200 + 5×429 all_tiers_exhausted)** — NVCF 侧 dsv4p 配额限流
   (5min 周期 02:05-02:30), **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
3. 0 改动, 0 重启. 同 post177-post181 模式.

### 数据快照 (30min)
| 维度 | 结果 |
|------|------|
| cc2 (cc4101-primary) 30min | 0 req (无流量, 链路健康无故障) ✓ |
| 30min 全 caller | hermes 9req dsv4p_nv (4×200, 5×429 限流), cc2 0 req |
| 30min tier error (cc2) | 0 ✓ |
| 30min buffer/wait 日志 | 空 ✓ |
| top error | all_tiers_exhausted ×5 (hermes→dsv4p_nv, 非 cc2) |

## 健康验证 (10:35 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 9h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 参数快照 (无变化同 post181)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 改动
- 无 (NOP 巡检轮)

## 验证
- nv_gw /health ok, docker ps 全 Up, 0 cc2 tier error, 0 cc2 buffer/wait 日志.

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
glm5_2_nv 连续 post100-post182 (83 轮) 无 dsv4p 故障扩散.
