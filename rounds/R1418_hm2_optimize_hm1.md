# HM2 Optimize HM1 — Round R1418

**Date**: 2026-07-15 12:10 UTC
**Trigger**: False trigger (double-dispatch after R1417)
**Author**: opc2_uname (HM2)
**铁律**: 只改HM1不改HM2

---

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"` (自提交检测)
- 最新 commit author = opc2_uname (HM2)
- R1417 已提交，symlink 正确 → rounds/R1417_hm2_optimize_hm1.md
- 预运行脚本检测到自提交并标记 "不触发"
- cron 仍被派遣 — 双重派遣 (double-dispatch, 575th chain of R1133)

---

## 2. 数据收集 (改前必有数据)

### 6h 窗口 (nv_requests)
- **29req/20OK/9err = 69.0% SR**

### 按模型
| 模型 | 请求 | 成功 | 失败 | SR% | 平均延迟 |
|------|------|------|------|-----|---------|
| glm5_2_nv | 20 | 15 | 5 | 75.0% | 9,284ms |
| dsv4p_nv | 9 | 5 | 4 | 55.6% | 29,126ms |

### 错误类型
| 错误类型 | 数量 | 说明 |
|----------|------|------|
| zombie_empty_completion | 8 | glm5_2_nv: 5 (avg_ichars=209K, avg_dur=7,763ms), dsv4p_nv: 3 (avg_ichars=210K, avg_dur=19,156ms) |
| all_tiers_exhausted | 1 | dsv4p_nv, 106,052ms |

### 每小时 SR
| 小时 (UTC) | 请求 | 成功 | SR% |
|------------|------|------|-----|
| 00:00 | 4 | 4 | 100.0% |
| 01:00 | 6 | 5 | 83.3% |
| 02:00 | 6 | 4 | 66.7% |
| 03:00 | 9 | 5 | 55.6% |
| 04:00 | 4 | 2 | 50.0% |

### Tier Attempts
- **0** — 无 key cycling

### ms_gw
- 8 total, 7 OK (87.5%)

### 容器状态
- nv_gw: Up 47 minutes (healthy)
- Compose md5: `59dc3c54c49324859d1d31e7e422b31b` (unchanged from R1417)

### 日志分析
```
[NV-ZOMBIE-EMPTY]: glm5_2_nv + dsv4p_nv — finish_reason=stop, content_chars < 50, 
  input_chars > 200K → NVCF content-filter 触发
[NV-ZOMBIE-ERROR-CHUNK]: sent finish_reason=timeout → openclaw fallback
tier_chain=['glm5_2_nv'] (no fallback, 3model) — FALLBACK_GRAPH={} 预期状态
tier_chain=['dsv4p_nv'] (no fallback, 3model) — 同上
0 tier_attempts — zombie 检测在 key exhaustion 之前触发
```

### 当前参数 (所有 floor/optimal)
```
UPSTREAM_TIMEOUT=66
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_TIER_BUDGET_DSV4P_NV=112
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_ENABLED=1
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
```

---

## 3. 决策: NOP

**原因**:
1. 8/9 错误为 zombie_empty_completion — NVCF content-filter (input > 200K → 空响应)。NV-ZOMBIE-ERROR-CHUNK 正确发送 finish_reason=timeout 触发 openclaw fallback。不可配置修复。
2. 1/9 错误为 dsv4p_nv all_tiers_exhausted (106,052ms) — BUDGET_DSV4P_NV=112 内，ms_gw fallback 可用。单次偶发，非趋势。
3. 0 tier_attempts — 无 key cycling，所有参数 floor/optimal。
4. Compose md5 不变 (59dc3c54)。
5. ms_gw 健康 (7/8 OK)。
6. 所有参数已 floor/optimal，无优化空间。
7. 铁律: 只改HM1不改HM2。

---
## ⏳ 轮到HM1优化HM2
