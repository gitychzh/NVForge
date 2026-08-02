# R-nvonly-post158.1 hm2 cc2 — NOP 巡检轮 (post159, 2026-08-02)

> 上一轮: R-nvonly-post158 (fabecf0). 本轮 post159.
> 接棒 STATE: cc2 30min 0 req 无流量, 链路健康, 0 改动 0 重启.

## 本轮判定: NOP 巡检轮

### 轮前链路分析 (2026-08-02 09:09:32 CST)
- cc2 (cc4101-primary) 30min: **0 req** (session 轮前无 cc2 流量产生, 无数据可判 cc2 SR)
- 30min 全 caller × model × status:
  - hermes | dsv4p_nv | 429 | 6
  - openclaw | dsv4p_nv | 200 | 2
- dsv4p_nv SR=25.0% (2/8) — 全部 6×429 是 hermes 打的, error_type=all_tiers_exhausted
- fallback 发生率: f|8 (8 次全 fallback 到 ms, 均为 hermes→dsv4p_nv 限流触发, 非 cc2 链路)
- tier 错误: 0 (空)
- buffer/wait 日志: 空 (无 BUFFER-/WAIT- 触发)

### 判稳依据
1. **cc2 (cc4101-primary) 0 req** — session 轮前无流量, 无数据可判 SR, 链路无故障迹象.
2. **dsv4p_nv 429 与 cc2 无关** — cc2 走 `glm5_2_nv` (PRIMARY_UPSTREAM_MODEL=glm5_2_nv), 不打 dsv4p_nv.
   hermes 打 dsv4p_nv 6×429 (all_tiers_exhausted, NVCF 侧 dsv4p 配额限流, 周期性 5min 一发).
   openclaw 同模型 2×200 佐证: 429 是 NVCF 配额限流, 非链路级故障.
3. **glm5_2_nv 链路连续 post100-post158 (59 轮) 无故障扩散** — cc2 自身链路稳定.
4. **0 tier error, 0 buffer/wait 日志** — nv_gw 内部无异常.

## 健康验证 (09:10 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 7h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 req (无流量, 链路健康无故障) ✓ |
| 30min tier error | 0 ✓ |
| 30min 全 caller | hermes 6×429 (dsv4p_nv 限流), openclaw 2×200, cc2 0 req ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 本轮改动
**0 改动, 0 重启** — NOP 巡检轮, 只记数据不改码.

## 下一步
- 持续监控 cc2 (cc4101-primary) glm5_2_nv SR. cc2 有流量后再判 SR 是否 99%+.
- dsv4p_nv 的 hermes 限流是 NVCF 侧配额问题, 非 cc2 范畴, 不干预.
- 若 cc2 流量出现且 SR<99% 或有新错误类型, 才进入修复轮.

## 参数快照 (2026-08-02 09:10 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms
