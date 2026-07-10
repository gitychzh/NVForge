# HM2 Optimize HM1 — Round R1108

## 触发分析

**cron 脚本输出**: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2自提交)
- HM2 本地 git log 最新: R1107 (NOP, false trigger)
- HM1 未提交任何新内容 → false trigger confirmed
- 预运行脚本已 commit R1107, symlink 已指向 R1107
- 当前为 double-dispatch: cron 再次派遣相同 trigger

## 数据收集 (改前必有数据)

### 6h 总体统计
| 指标 | 值 |
|------|-----|
| 总请求 | 128 |
| 成功 | 116 |
| 失败 | 12 |
| 成功率 | 90.6% |
| 容器重启 | 2026-07-10T17:21:04Z (R1103 post-restart) |

### 6h 按上游类型
| upstream_type | cnt | ok | err | avg_ttfb | avg_dur | max_dur |
|---------------|-----|----|-----|----------|---------|---------|
| nv_integrate | 99 | 89 | 10 | 17524 | 19481 | 96999 |
| nvcf_pexec | 27 | 27 | 0 | 11696 | 11696 | 48049 |
| (ATE) | 2 | 0 | 2 | 501 | 61375 | 61376 |

### 6h 错误分类
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 8 |
| NVStream_TimeoutError | 2 |
| all_tiers_exhausted | 2 |

### 6h 按模型
| model | cnt | ok | err | sr_pct | avg_dur |
|-------|-----|----|-----|--------|---------|
| glm5_2_nv | 93 | 83 | 10 | 89.2% | 19697 |
| dsv4p_nv | 19 | 17 | 2 | 89.5% | 19990 |
| minimax_m3_nv | 9 | 9 | 0 | 100.0% | 14483 |
| kimi_nv | 7 | 7 | 0 | 100.0% | 3605 |

### nv_tier_attempts: 0 行 (无 key-level 失败)
### fallback: 0 触发
### ms_gw: logs 正常 (MS-STREAM-DONE), DB 4 total/0 OK (ms_requests 不可靠)

### Docker logs (nv_gw)
- NV-ZOMBIE-EMPTY: glm5_2_nv zombie empty completion (finish_reason=stop, content_chars=2 < 50)
- NV-ZOMBIE-ERROR-CHUNK: 发送 content_filter SSE chunk 触发 openclaw fallback

## 当前 HM1 参数状态 (nv_gw env)

```
KEY_AUTHFAIL_COOLDOWN_S=60
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_COOLDOWN_S=15
TIER_TIMEOUT_BUDGET_S=198
UPSTREAM_TIMEOUT=66
```

## 决策

**NOP — 零参数变更**

理由:
1. **False trigger**: cron 脚本检测到 HM2 自提交 ("这是我提交的, 不触发")
2. **数据稳定**: 128req/116OK/90.6% SR vs R1107 的 124/114/91.9% — 基本一致
3. **所有参数已触底**: TIER_COOLDOWN_S=15(floor), KEY_COOLDOWN_S=25, UPSTREAM_TIMEOUT=66, NVU_EMPTY_200_FASTBREAK=2(floor), NVU_FALLBACK_HEALTH_THRESHOLD=0.05(floor), TIER_TIMEOUT_BUDGET_S=198, NVU_TIER_BUDGET_DSV4P_NV=66, NVU_TIER_BUDGET_GLM5_2_NV=96
4. **zombie_empty_completion (8×)**: R1103 新增的 code-level feature, 非参数可调 — 正确检测到空 completion 并触发 openclaw fallback
5. **ATE (2×)**: dsv4p_nv, 全部 pre-restart artifacts (容器重启后 0 ATE)
6. **NVStream_TimeoutError (2×)**: glm5_2_nv streaming timeout, 预重启残留
7. **ms_gw**: logs 正常, MS-STREAM-DONE 成功, 无需优化
8. **铁律**: 只改 HM1 不改 HM2 — 但 HM1 无优化空间, 无需修改

## ⏳ 轮到HM1优化HM2
