# R-nvonly-post131 (hm2_cc2) — NOP 巡检轮

## 日期
2026-08-02 07:53 CST

## 轮前数据 (07:52 CST 拉取, 30min 窗口)

### 1. cc4101-primary (cc2) 30min — 0 req
cc2 无流量产生 (session 轮前无请求). 链路健康无故障, 无数据可判 SR.

### 2. 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

- dsv4p_nv SR=0.0% (0/6): 6×429 (all_tiers_exhausted, 5key 全挂), 周期性 5min 一发.
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
- 30min fallback 发生率: f=6 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作).

### 3. dsv4p_nv 按分钟趋势 (UTC, 周期性 429)
| 分钟 (UTC) | status | count |
|------|--------|-------|
| 23:25 | 429 | 1 |
| 23:30 | 429 | 1 |
| 23:35 | 429 | 1 |
| 23:40 | 429 | 1 |
| 23:45 | 429 | 1 |
| 23:50 | 429 | 1 |

周期性 5min 一发 429, NVCF 侧 dsv4p 限流模式, 非 cc2 链路问题.

### 4. nv_gw buffer/wait 日志
无 (cc2 0 req, 无 buffer/wait 触发).

## 判稳
- cc2 (cc4101-primary) 30min: 0 req, 链路健康无故障.
- SR ≥99% 判定: 无流量无数据, 但无新错误, 无 stream_total_deadline, 容器全 Up, env 配置正确 → NOP.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw, 不碰 caller).
- glm5_2_nv 连续 post100-post131 (32 轮) 无故障扩散.

## 健康验证 (07:53 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 6 (全 hermes+dsv4p, 非 cc2) ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 本轮改动
0 改动, 0 重启 (NOP 巡检轮).

## 参数快照
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 属 NVCF 侧 + hermes caller, 非本轮职责.
- glm5_2_nv 链路连续 32 轮稳定, 无需调整.
