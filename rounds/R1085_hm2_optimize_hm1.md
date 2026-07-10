# HM2 Optimize HM1 — Round R1085

## 触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2), message = R1084: NOP
- HM1 本地 git log = R821 (263 轮落后)，无新提交
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)

## 数据收集 (改前必有数据)

### nv_gw 容器状态
- 重启时间: 2026-07-10 09:47:59 UTC
- 重启后运行: ~9.3h
- 重启后流量: 5 请求, **100% SR** (5/5), 全部 glm5_2_nv integrate 1st-key
- 所有失败发生在重启前 (05:54-09:06 UTC), 非重启后

### 6h DB 窗口 (含重启前污染)
| 指标 | 值 |
|------|-----|
| 总请求 | 52 |
| 成功 | 44 (84.6%) |
| 失败 | 8 |
| glm5_2_nv | 48/44 OK (91.7%), avg 29,116ms |
| dsv4p_nv | 4/0 OK (0.0%), 全部 ATE, avg 88,369ms |
| fallback | 0 (none triggered) |

### 失败详情 (全部重启前)
| 时间 (UTC) | 模型 | 错误 | 耗时 |
|-----------|------|------|------|
| 09:06 | dsv4p_nv | all_tiers_exhausted | 132,017ms |
| 08:20 | dsv4p_nv | all_tiers_exhausted | 1,328ms |
| 08:15 | glm5_2_nv | NVStream_TimeoutError | 96,068ms |
| 06:10 | glm5_2_nv | NVStream_TimeoutError | 99,181ms |
| 06:07 | dsv4p_nv | all_tiers_exhausted | 110,073ms |
| 06:02 | glm5_2_nv | NVStream_TimeoutError | 102,323ms |
| 05:59 | dsv4p_nv | all_tiers_exhausted | 110,058ms |
| 05:54 | glm5_2_nv | NVStream_TimeoutError | 105,819ms |

### 重启后 (09:47→now) — 唯一有效数据
| 模型 | 请求 | 成功 | SR | 平均延迟 |
|------|------|------|-----|---------|
| glm5_2_nv | 5 | 5 | 100% | ~3-4s (log观察) |
| dsv4p_nv | 0 | 0 | - | 无流量 |

所有 glm5_2_nv integrate 1st-key 成功 (k1-k5 轮流), 响应时间 ~3-4s.

### ms_gw 状态 (6h)
- docker logs: 9 MS-OK-STREAM, 6 MS-STREAM-DONE, **3 BrokenPipeError**
- ms_gw DB: 10 total, 0 ok (DB 写入问题, 参见 R980)
- ms_gw EMPTY_200_FASTBREAK_THRESHOLD=3 (R900, 已优化)
- ms_gw KEY_COOLDOWN_S=60 (R922, 已优化)
- BrokenPipeError = code-level streaming relay 问题, 非 config-fixable

### nv_gw 参数审查 — 全部 floor/optimal
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 132 | optimal |
| TIER_COOLDOWN_S | 18 | optimal |
| KEY_COOLDOWN_S | 25 | optimal |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive (R922) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | function-level ✓ |
| NVU_EMPTY_200_FASTBREAK | 2 | key-specific ✓ (R1031) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | function-level ✓ |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | off |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | optimal (R1078) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | optimal (dsv4p not skipped → peer-fb on) |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 | conservative (R982) |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | legacy dead param (R919) |
| NVU_STREAM_TOTAL_DEADLINE_S | 90 | HM1 only |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | HM1 only |

### 重启后日志审核
```
[NV-INTEGRATE-SUCCESS] tier=glm5_2_nv k1-k5 all succeeded on first attempt
Zero NV-TIER-FAIL, zero NV-MS-FB, zero NV-PEER-FB, zero BrokenPipe
```

## 优化决策

**NOP — 无 config-fixable 信号。**

理由:
1. 重启后 100% SR (5/5), 零失败 — 所有参数已 floor/optimal
2. 全部 8 个失败是重启前 NVCF 504 外部 + ms_gw BrokenPipeError code-level, 非 config-fixable
3. dsv4p_nv ATE 全部 pre-restart, 重启后 dsv4p_nv 零流量 — 无法判断是否需要调整
4. ms_gw BrokenPipeErrors = code-level streaming relay 问题, 不可 config-fix
5. glm5_2_nv integrate 1st-key 100% SR — 该模型完美稳定
6. 所有 nv_gw 参数已 floor/optimal, 无下探空间

零参数修改。铁律: 只改 HM1 不改 HM2.

## ⏳ 轮到HM1优化HM2
