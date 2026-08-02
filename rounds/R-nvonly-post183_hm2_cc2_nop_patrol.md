# R-nvonly-post183 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 10:40 CST
**上轮**: R-nvonly-post182 (commit a45cad2)
**容器**: nv_gw Up 9h, cc4101 Up 9h, nv_gw_stable Up 9h, ms_gw/logs_db Up 3d

## 本轮结论
NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req (session 轮前无流量产生, 无数据可判 SR).
链路健康无故障: nv_gw /health ok, env 配置正确, 0 cc2 tier error, 0 cc2 buffer/wait 日志.
0 改动, 0 重启.

## 健康验证 (10:40 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 9h, ms_gw/logs_db Up 3d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 轮前链路数据 (30min)
- cc2 (cc4101-primary): 0 req (无流量)
- 其他 caller:
  | caller | model | status | count | avg_dur |
  |--------|-------|--------|-------|---------|
  | hermes | dsv4p_nv | 200 | 3 | 11360 |
  | hermes | dsv4p_nv | 429 | 6 | 1587 |

  hermes→dsv4p_nv SR=33.3% (3/9, all_tiers_exhausted ×6, NVCF 侧 dsv4p 配额限流, 5min 周期 02:15-02:40).
  **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 30min 错误分类
| error_type | sub | count | avg_dur |
|------------|-----|-------|---------|
| all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 6 | 1587 |

全部 6× 是 hermes→dsv4p_nv 的 NVCF 配额限流, 非 cc2 链路.

## 参数快照 (无变化同 post182)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
glm5_2_nv 连续 post100-post183 (84 轮) 无 dsv4p 故障扩散.
