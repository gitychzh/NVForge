# HM2 Optimize HM1 — Round R1162 (R1161: R-NEXT)

## ⏱️ 判定: NOP (false trigger, 31st chain of R1133, zombie-only, zero param)

**触发类型**: FALSE TRIGGER — cron 脚本输出 "这是我提交的, 不触发"  
**触发commit**: be12e94 (author=opc2_uname, HM2)  
**前轮**: R1161 (同样NOP, zombie-only, zero param)

### 铁律: 只改HM1不改HM2 ✓

---

## 1. 6h 数据快照 (2026-07-11 ~10:50 UTC)

```
6h: 42req/19OK(45.2%)/23zombie
  └─ glm5_2_nv: 42/19/23 (45.2% SR)
  └─ dsv4p_nv: 0 traffic
  └─ kimi_nv: 0 traffic
  └─ ms_gw: 0 traffic
```

| 维度 | 数值 |
|------|------|
| 总请求 | 42 |
| 成功 | 19 (45.2%) |
| 失败 | 23 (100% zombie_empty_completion) |
| 上游类型 | nv_integrate (100%) |
| fallback_occurred | 0 |
| nv_tier_attempts | 3× 429_integrate_rate_limit (仅) |
| ms_requests | 0 |

## 2. Per-tier DB 明细 (6h)

| tier_model | total | ok | sr_pct | avg_ok_ms | p95_ok_ms |
|------------|-------|-----|--------|-----------|-----------|
| glm5_2_nv | 42 | 19 | 45.2% | 5,723 | 10,891 |

| tier_model | upstream_type | cnt | ok |
|------------|---------------+-----|-----|
| glm5_2_nv | nv_integrate | 42 | 19 |

| tier_model | caller | cnt | ok |
|------------|--------|-----|-----|
| glm5_2_nv | openclaw | 42 | 19 |

## 3. Error 明细 (6h)

| error_type | cnt | error_subcategory | finish_reason | avg_input_chars | avg_output_tokens |
|------------|-----|--------------------|---------------|-----------------|-------------------|
| zombie_empty_completion | 23 | (null) | stop | 164,282 | 6 |

**所有23个失败均为 NVCF content-filter 行为**: glm5_2_nv integrate 模式, NVCF 返回 finish_reason=stop, content_chars=12, input_chars=164K-167K。Gateway zombie 检测正确 — 3-4s 快速中止返回 502+error-chunk (`[NV-ZOMBIE-EMPTY]` + `[NV-ZOMBIE-ERROR-CHUNK]`)。代码级特性，非配置可修复。

## 4. 实时日志 (最近500行)

- `glm5_2_nv`: 均 integrate, tier_idx=2, msgs=70-81, agent=_nv caller=openclaw
  - 每30min一波2×请求（openclaw 循环）
  - 交替 zombie + 成功（~55% zombie 率）
- `dsv4p_nv`: 日志有成功 pexec (k2/k3 第一尝试成功, 03:05 UTC), 但 DB 6h窗口为0 — 说明请求量极低不在6h窗口内
- `ms_gw`: 无当前流量, 仅旧 MS-VARIANT-EXHAUSTED 残留

## 5. 容器状态

- 重启时间: 2026-07-10T19:03:27Z (~15.8h 前)
- 运行状态: Up 8 hours (healthy)
- compose md5: 7975939c245761e451a8813852dcb9bf (自 R1133 未变, 48h+)

## 6. 当前参数 (全部 floor/optimal)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=198
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NV_INTEGRATE_KEY_COOLDOWN_S=0
MIN_OUTBOUND_INTERVAL_S=0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
```

## 7. 决策: NOP (Zero Param)

**理由**:
1. 所有失败 = zombie_empty_completion (NVCF content-filter, 代码级特性) — 非配置可修复
2. Gateway zombie 检测正确 — 3-4s 快速中止，比 96s hang 好
3. 0 dsv4p_nv / kimi_nv / ms_gw 流量 — 其他 tiers 未激活, fallback 未触发
4. 0 ATE, 0 fallback_occurred — 系统无其他故障模式
5. compose md5 自 R1133 未变 (48h+) — 无配置漂移
6. 所有参数在 floor/optimal — 无优化空间
7. 45.2% SR 并非 gateway 故障 — 是上游 NVCF content-filter 对 164K+ 输入返回空响应的行为

**Zero param changes. 铁律: 只改HM1不改HM2 ✓**

## 8. 触发分析

- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit be12e94 author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (R1133 chain 第31轮 false-trigger)
- HM1 compose 未变更，数据与 R1161 一致
- R1133→R1162: 31轮连续 false-trigger NOP, compose md5 不变 48h+

## ⏳ 轮到HM1优化HM2
