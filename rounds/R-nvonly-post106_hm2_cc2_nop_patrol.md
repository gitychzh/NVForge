# R-nvonly-post106 — hm2_cc2 NOP 巡检轮 (2026-08-02 06:40 CST)

## 轮号 / 基线
- 主仓 HEAD: 9d02a74 (post105 已 push)
- 本轮: R-nvonly-post106 (hm2_cc2) — NOP 巡检轮
- 上轮: post105 (NOP), 上轮数据与本轮完全一致

## 判稳依据
- cc2 (cc4101-primary) 30min 窗口: **0 req** (session 轮前无流量产生, 无数据可判 SR)
- 链路健��无故障: 容器全 Up, env 配置正确, 0 cc2 tier/buffer/wait/error 日志
- 无新错误类型, 无新故障模式 → NOP 巡检轮, 只记数据不改码

## 本轮数据

### cc4101-primary (cc2) 30min — 0 req
session 轮前无流量, 链路健康, 无数据可判 cc2 SR.

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

dsv4p_nv SR=0.0% (0/6): 6×429 (all_tiers_exhausted, 5key 全挂), 周期性 5min 一发 429.
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
30min fallback 发生率: f=6 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作).

### dsv4p_nv 周期性 429 趋势 (UTC)
22:10/22:15/22:20/22:25/22:30/22:35 各 1×429, 周期性 5min 一发.
NVCF 侧 dsv4p 限流模式, 非 cc2 链路问题.
连续 7 轮 (post100-post106) 无扩散到 glm5_2_nv.

## 健康验证 (06:40 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| nv_gw env | NVU_DISABLE_MS_FALLBACK=0, BUFFER 5×90s=450s, MAX_RETRIES=5 ✓ |
| cc4101 env | STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK=ms_gw:40007 ✓ |
| docker ps | nv_gw/cc4101 Up 5h, nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 6 (全 hermes+dsv4p, 非 cc2) ✓ |
| 配置 | fallback 已恢复, deadline 链对齐 (90×5=450<470<500) ✓ |

## 本轮改动
- **0 改动, 0 重启** — NOP 巡检轮

## 下一步
- 继续 NOP 巡检, 等 cc2 流量产生或新错误模式出现
- dsv4p_nv 限流持续 (hermes caller), 非 cc2 范围, 不处理
- 关注 glm5_2_nv 是否被 dsv4p 限流扩散影响 (post100-post106 连续 7 轮无扩散)

## 参数快照 (2026-08-02 06:40 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: STREAM_TOTAL_DEADLINE=470s, PRIMARY_HEADER_TIMEOUT=400s, FALLBACK_UPSTREAM_URL=ms_gw:40007
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复
