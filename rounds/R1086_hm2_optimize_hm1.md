# HM2 Optimize HM1 — Round R1086

## 触发
R1085 NOP 后 cron 检测到 HM1 提交了新 commit (R1085: NOP) → 轮到 HM2 优化 HM1。

## 数据收集 (改前必有数据)

### nv_gw 容器状态
- 重启时间: 2026-07-10 09:47 UTC
- 重启后运行: ~9.7h
- 容器: nv_gw, Up 2+ hours (healthy)

### 2h 窗口 DB (容器重启后 = 有效数据)
| 指标 | 值 |
|------|-----|
| 总请求 | 8 |
| 成功 | 8 (100.0% SR) |
| 失败 | 0 |
| 平均 TTFB | 14,420ms |
| 平均 duration | 14,552ms |
| 最大 duration | 45,690ms |

### 按路径分解 (2h)
| upstream_type | cnt | ok | avg_ttfb | avg_dur |
|---------------|-----|-----|----------|---------|
| nv_integrate | 8 | 8 | 14,420ms | 14,552ms |

### 错误分类 (2h)
- 零错误, 零 tier_attempts, 零 429s

### 6h 窗口 (含重启前污染, 仅供参考)
| 指标 | 值 |
|------|-----|
| 总请求 | 52 |
| 成功 | 44 (84.6%) |
| 失败 | 8 |
| glm5_2_nv integrate | 47/43 OK (91.5%) |
| dsv4p_nv | 4/0 OK (0%, 全部 ATE pre-restart) |
| NVStream_TimeoutError | 4 (全部 pre-restart) |
| all_tiers_exhausted | 4 (dsv4p_nv, 全部 pre-restart) |

### nv_gw 日志 (tail 30)
- 全部 [NV-INTEGRATE-SUCCESS] tier=glm5_2_nv k1-k5 1st-key 成功
- 零 NV-TIER-FAIL, 零 NV-MS-FB, 零 NV-PEER-FB, 零 BrokenPipeError
- 零 empty_200, 零 timeout, 零 429
- 键循环正常: k1→k2→k3→k4→k5 均匀轮转

### nv_gw 参数审查 — 全部 floor/optimal
所有参数与 R1085 一致, 无变化, 全部已 floor/optimal:
- UPSTREAM_TIMEOUT=66 (floor), TIER_TIMEOUT_BUDGET_S=132, TIER_COOLDOWN_S=18
- KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60 (R922)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_SSLEOF_RETRY_DELAY_S=1.0, NVU_CONNECT_RESERVE_S=0, MIN_OUTBOUND_INTERVAL_S=0
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_TIER_BUDGET_DSV4P_NV=66, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv (dsv4p not skipped → peer-fb on)
- NVU_FALLBACK_HEALTH_THRESHOLD=0.10, FALLBACK_HEALTH_THRESHOLD=0.05 (legacy dead)
- NVU_STREAM_TOTAL_DEADLINE_S=90, NVU_INTEGRATE_THINKING_TIMEOUT_S=90

## 优化决策

**NOP — 无 config-fixable 信号。**

理由:
1. 重启后 100% SR (8/8), 零失败 — 所有参数已 floor/optimal
2. 全部 8 个失败是重启前 NVCF 504 外部 + ms_gw BrokenPipeError code-level, 非 config-fixable (R1085 已记录)
3. dsv4p_nv 重启后零流量 — 无法判断是否需要调整, 不盲改
4. glm5_2_nv integrate 1st-key 100% SR — 完美稳定
5. 键轮转均匀, 零 429s, 零 tier_attempts — 无 rate-limit 信号
6. 所有 nv_gw 参数已 floor/optimal, 无下探空间

零参数修改。铁律: 只改 HM1 不改 HM2.

## ⏳ 轮到HM1优化HM2
