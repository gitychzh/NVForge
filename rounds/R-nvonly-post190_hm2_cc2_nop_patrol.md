# R-nvonly-post190 hm2 cc2 NOP 巡检轮

## 元信息
- 时间: 2026-08-02 11:10 CST
- 主机: HM2 (100.109.57.26, opc2_uname)
- 方向: R-nvonly (nv_gw 40006, glm5_2_nv)
- 类型: NOP 巡检轮 (无 cc2 流量, 链路健康无故障)
- 改动: 0  重启: 0

## 本轮决策
- 30min cc2 (cc4101-primary) = 0 req, 6h cc2 = 0 req → 无数据判 SR, 链路健康.
- 30min 全 caller: hermes→dsv4p_nv 6×429 all_tiers_exhausted (NVCF 侧配额限流), openclaw→dsv4p_nv 1×200.
- dsv4p_nv 限流与 cc2 无关 (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
- glm5_2_nv 连续 post100-post190 (91 轮) 无 dsv4p 故障扩散.
- → NOP, 不改码.

## 链路数据 (30min)
### cc2 (cc4101-primary)
- 0 req, 0 error, 0 tier error, 0 buffer/wait 日志.

### 其他 caller
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |
| openclaw | dsv4p_nv | 200 | 1 |

### 错误分类 (全 caller)
| error_type | count |
|------------|-------|
| all_tiers_exhausted | 6 |

全部 hermes→dsv4p_nv NVCF 配额限流, 非 cc2 链路.

### KeyManager 日志 (dsv4p_nv, 正常退避)
- 10:55-11:05 dsv4p_nv 5key 429 指数退避 (count 1→6, cooldown 180s→480s).
- count decayed (>300s) 自动 reset, 429 退避机制工作正常.
- 与 cc2 无关.

## 健康验证 (11:10 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 9h, ms_gw/logs_db Up 3d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康) ✓ |
| 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 参数快照 (无变化, 同 post188)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
继续 NOP 巡检. 等 cc2 流量产生后再判 SR. 若 dsv4p_nv 配额限流持续扩散到 glm5_2_nv 再介入.
