# R-nvonly-post110 — NOP 巡检轮 (2026-08-02)

## 摘要
NOP 巡检轮. cc2 (cc4101-primary) 30min 0 req (session 轮前无流量产生, 无数据可判 SR).
链路健康无故障: 容器全 Up (nv_gw/cc4101/nv_gw_stable 5h, ms_gw/logs_db 2d),
env 配置正确 (NVU_DISABLE_MS_FALLBACK=0 fallback 已恢复, buffer 5×90s=450s, cc4101 deadline 470s),
0 cc2 tier error, 0 cc2 buffer/wait/error 日志. 0 改动, 0 重启.

hermes 打 dsv4p_nv SR=37.5% (3/8, 3×200 + 5×429/all_tiers_exhausted, 周期性 5min 一发)
仍是 NVCF 侧 dsv4p 限流, 非 cc2 链路 (cc2 走 glm5_2_nv).
glm5_2_nv 连续 post100-post110 (11 轮) 无 dsv4p 故障扩散.

## 本轮数据 (30min 窗口)

### 1. cc4101-primary (cc2) — 0 req
无流量产生. 无数据可判 cc2 SR. 链路健康: 容器全 Up, env 正确, 0 cc2 tier error,
0 buffer/wait 日志, 0 stream_total_deadline.

### 2. 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |

dsv4p_nv SR=37.5% (3/8): 5×429 (all_tiers_exhausted, 5key 全挂) 周期性 5min 一发.
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
30min fallback 发生率: f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作).

### 3. dsv4p_nv 按分钟趋势 (周期性 429, UTC)
| 分钟 (UTC) | status | count |
|------|--------|-------|
| 22:25 | 429 | 1 |
| 22:30 | 429 | 1 |
| 22:35 | 429 | 1 |
| 22:40 | 200 | 3 |
| 22:45 | 429 | 1 |
| 22:50 | 429 | 1 |

周期性 5min 一发 429 后 22:40 恢复 200×3, NVCF 侧 dsv4p 限流模式. 与 post109 相同.

## 健康验证 (06:52 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| nv_gw env | NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, TOTAL_DEADLINE=450s, UPSTREAM_TIMEOUT=90s ✓ |
| cc4101 env | STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK=ms_gw:40007 ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |
| 30min tier error | 0 rows (无 cc2 流量) ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 判稳结论
- cc2 链路: 健康, 0 流量, 无故障 → NOP.
- dsv4p_nv 37.5% SR 是 hermes caller 打 dsv4p 受 NVCF 限流, 非 cc2 链路 (cc2 走 glm5_2_nv).
- 与 post100-post109 (11 轮) 一致, dsv4p 故障未扩散到 glm5_2_nv.
- 0 改动, 0 重启.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
