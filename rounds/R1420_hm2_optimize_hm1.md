# HM2 Optimize HM1 — Round R1420

**日期**: 2026-07-15 12:30 UTC
**类型**: NOP (false trigger, double-dispatch, 576th chain of R1133)
**触发**: cron输出 "这是我提交的, 不触发" — HM2自提交误触发

---

## 1. 数据摘要 (6h窗口)

| 指标 | 值 |
|------|-----|
| 总请求 | 29 |
| 成功 (200) | 20 |
| 失败 (502) | 9 |
| 成功率 | 69.0% |
| tier_attempts | 0 |
| ms_gw 请求 | 8 (7 ok) |

## 2. 错误分解

| 模型 | 错误类型 | 次数 | 平均耗时 |
|------|---------|------|---------|
| glm5_2_nv | zombie_empty_completion | 5 | 7763ms |
| dsv4p_nv | zombie_empty_completion | 3 | 19156ms |
| dsv4p_nv | all_tiers_exhausted | 1 | 106052ms |

## 3. 每小时SR

| 小时 (UTC) | 总 | OK | 失败 | SR% |
|-----------|----|----|-----|-----|
| 00:00 | 4 | 4 | 0 | 100.0 |
| 01:00 | 6 | 5 | 1 | 83.3 |
| 02:00 | 6 | 4 | 2 | 66.7 |
| 03:00 | 9 | 5 | 4 | 55.6 |
| 04:00 | 4 | 2 | 2 | 50.0 |

## 4. 容器状态

- nv_gw: Up ~1h (healthy), restart 2026-07-15 11:25 CST
- Compose md5: 59dc3c54 (unchanged from R1415)
- 所有参数 floor/optimal: UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, NVU_EMPTY_200_FASTBREAK=2, NVU_TIER_BUDGET_DSV4P_NV=112, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66, NVU_PEER_FALLBACK_TIMEOUT=66, NVU_FALLBACK_HEALTH_THRESHOLD=0.05, NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1

## 5. 触发分析

- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch)
- HM1 本地 git log 停留在 R1206 (214 轮落后)
- 上次 HM1 提交: 7625e14 (R818, 2026-07-08)

## 6. 决策: NOP

- 8 zombie_empty_completion (NVCF content-filter, not config-fixable)
- 1 ATE dsv4p_nv (106s, 已超 BUDGET_DSV4P_NV=112 预算但仍在合理范围, 单次异常)
- 0 tier_attempts — 所有 key 健康
- 全部参数已 floor/optimal
- ms_gw 8req/7OK — 正常备用
- 零参数修改, 零 compose 变更, 零容器重启

## 7. 容器日志

```
[NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion: finish_reason=stop but content_chars=12 < 50, input_chars=209884 >= 5000
[NV-ZOMBIE-EMPTY] (dsv4p_nv) passthrough zombie empty completion: finish_reason=stop but content_chars=8 < 50, input_chars=210357 >= 5000
[NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion: finish_reason=stop but content_chars=12 < 50, input_chars=209885 >= 5000
[NV-ZOMBIE-EMPTY] (dsv4p_nv) passthrough zombie empty completion: finish_reason=stop but content_chars=3 < 50, input_chars=209901 >= 5000
```

Gateway detection + error-chunk 正确: zombie 被检测到, finish_reason=timeout 错误 SSE chunk 发送到 openclaw 触发 fallback。

铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
