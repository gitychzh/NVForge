# R2092: hermes2 R33 巡检 — NVCF dsv4p function DEGRADED 持续第3轮, SR=0%

- **轮次**: hermes2 R33 (仓库 R2092)
- **日期**: 2026-07-20 23:15 UTC+8
- **类型**: 巡检轮 (不改代码)
- **上一轮**: R2091 (hermes2 R32, NVCF DEGRADED 持续第2轮)

## 数据 (30min 窗口, 改前)

```
dsv4p_nv 请求:
  request_model | status | count
  dsv4p_nv      |    502 |     9

错误分类:
  error_type          | count
  all_tiers_exhausted |     9

nv_tier_attempts:
  error_type   | count
  pexec_success|     2   (其他 tier 的)

hm4104 30min fallback:
  PRIMARY-BREAKER-SKIP: 97  (circuit OPEN, 直走 fallback)
  PRIMARY-FAIL-STREAM:   9  (尝试 primary, 全部 502)
  FALLBACK-STREAM:      98  (总 fallback 事件)
  total fallback grep: 220
```

## nv_gw 日志确认

```
[23:11:34.4] [NV-NONCYCLE-ERR] tier=dsv4p_nv k5 resp.status=400 non-cycling,
  body={"status": 400, "title": "Bad Request",
  "detail": "Function id '74f02205-c7ba-438f-b81a-2537955bd7ec': DEGRADED function cannot be invoked"}
[23:11:34.4] [NV-TIER-DEGRADED] tier=dsv4p_nv marked DEGRADED cooldown 60s
```

## 核心判断

- NVCF dsv4p function `74f02205-c7ba-438f-b81a-2537955bd7ec` 持续 DEGRADED
- 连续第 3 轮 (R31-R33) SR=0%
- R814 DEGRADED short-circuit 正确工作
- hm4104 breaker OPEN，97/106=91.5% 请求跳过 primary 直走 ms_gw
- 请求量下降 (162→9) 是因为 breaker OPEN 后大部分请求不走 nv_gw
- **根因在天 (NVCF 平台侧), 不在人 (nv_gw 配置)**

## 本轮改动

无 (巡检轮, NVCF function DEGRADED, SR=0%, 连续第3轮)

## 八轮 502/SR 趋势 (R26-R33)

| 轮次 | 502 | SR | 判断 |
|------|-----|-----|------|
| R26 | 6 | 73.1% | 持续恢复 |
| R27 | 9 | 55.0% | 恶化 |
| R28 | 10 | 50.0% | 恶化 |
| R29 | 11 | 35.3% | 触发阈值 |
| R30 | 112 | 9.0% | 误判为"502灾难" |
| R31 | 143 | 0% | 确诊: 400 DEGRADED |
| R32 | 161 | 0% | 持续 DEGRADED |
| **R33** | **9** | **0%** | **持续 DEGRADED, breaker OPEN** |

R33 的 502 下降 (161→9) 不是因为 NVCF 恢复, 而是因为 hm4104 breaker OPEN 后
91.5% 请求跳过 nv_gw 直接走 ms_gw, 只有 9 次尝试 primary。

## 验证

- `curl /health`: OK
- `docker ps`: nv_gw/hm4104/ms_gw/logs_db 全部 Up

## 下一步建议

**⚠️ DEGRADED 连续 3 轮 (R31-R33), 强烈建议人为联系 NVCF 支持**:
- function_id `74f02205-c7ba-438f-b81a-2537955bd7ec` (ai-deepseek-v4-pro) 为何被置为 DEGRADED
- 预计何时恢复
- 是否有替代 function_id 可用 (若有, 可更新 config.py 的 function_id)

R34 继续巡检, 不改变码, 直到 NVCF 恢复 DEGRADED 状态。