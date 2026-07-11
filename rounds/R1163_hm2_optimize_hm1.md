# HM2 Optimize HM1 — Round R1163 (R1162→false trigger chain continuation)

## ⏱️ 判定: NOP (false trigger, 32nd chain of R1133, zombie-only, zero param)

**触发类型**: FALSE TRIGGER — cron 脚本输出 "这是我提交的, 不触发"
**触发commit**: a6918d7 (author=opc2_uname, HM2)
**前轮**: R1162 (同样NOP, zombie-only, zero param)

### 铁律: 只改HM1不改HM2 ✓

---

## 1. 6h 数据快照 (2026-07-11 ~11:00 UTC)

```
6h: 42req/18OK(43.9%)/23zombie (DB count=41, nv_tier_attempts=42 total)
  └─ glm5_2_nv: 42/18/23 (43.9% SR)
  └─ dsv4p_nv: 0 traffic
  └─ kimi_nv: 0 traffic
  └─ minimax_m3_nv: 0 traffic
  └─ ms_gw: 0 traffic
```

| 维度 | 数值 |
|------|------|
| 总请求 | 42 |
| 成功 | 18 (43.9%) |
| 失败 | 23 (100% zombie_empty_completion) |
| 上游类型 | nv_integrate (100%) |
| fallback_occurred | 0 (全部 f) |
| nv_tier_attempts | 3× 429_integrate_rate_limit (仅) |
| ms_requests | 0 |

## 2. Per-tier DB 明细 (6h)

| tier_model | total | ok | sr_pct | avg_dur_ms |
|------------|-------|-----|--------|-----------|
| glm5_2_nv | 42 | 18 | 43.9% | 4,884 |

| tier_model | upstream_type | cnt | ok |
|------------|---------------+-----|-----|
| glm5_2_nv | nv_integrate | 42 | 19 |

| tier_model | caller | cnt | ok |
|------------|--------|-----|-----|
| glm5_2_nv | openclaw | 42 | 19 |

## 3. Error 明细 (6h)

| error_type | cnt | error_subcategory | finish_reason | avg_input_chars | avg_duration_ms |
|------------|-----|--------------------|---------------|-----------------|-----------------|
| zombie_empty_completion | 23 | (null) | stop | 164K→168K (growing) | 3,500-4,700 |

**所有23个失败均为 NVCF content-filter 行为**: glm5_2_nv integrate 模式, NVCF 返回 finish_reason=stop, content_chars=12, input_chars=164K-168K (持续增长: R1162 164K→167K, R1163 165K→168K)。Gateway zombie 检测正确 — 3-5s 快速中止返回 502+error-chunk (`[NV-ZOMBIE-EMPTY]` + `[NV-ZOMBIE-ERROR-CHUNK]`)。代码级特性，非配置可修复。

## 4. Hourly SR (6h)

| hour (UTC) | total | ok | sr_pct |
|------------|-------|-----|--------|
| 2026-07-10 21:00 | 8 | 8 | 100.0% |
| 2026-07-10 22:00 | 9 | 1 | 11.1% |
| 2026-07-10 23:00 | 9 | 4 | 44.4% |
| 2026-07-11 00:00 | 7 | 1 | 14.3% |
| 2026-07-11 01:00 | 4 | 2 | 50.0% |
| 2026-07-11 02:00 | 4 | 2 | 50.0% |
| 2026-07-11 03:00 | 1 | 1 | 100.0% |

## 5. 实时日志

- `glm5_2_nv`: 均 integrate, tier_idx=2, msgs=70-84, agent=_nv caller=openclaw
  - 每30min一波2×请求（openclaw 循环, msgs 持续 +1/轮）
  - 交替 zombie + 成功（~55% zombie 率）, input_chars 持续增长 164K→168K
- `dsv4p_nv`: 无当前流量（6h 窗口内 0 请求）
- `ms_gw`: 无当前流量, DB ms_requests=0
- `kimi_nv`, `minimax_m3_nv`: 0 traffic

## 6. 容器状态

- 重启时间: 2026-07-10T19:03:27Z (~16h 前)
- 运行状态: Up 8 hours (healthy)
- compose md5: 7975939c245761e451a8813852dcb9bf (自 R1133 未变, 48h+)

## 7. 当前参数 (全部 floor/optimal)

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

## 8. 决策: NOP (Zero Param)

**理由**:
1. 所有失败 = zombie_empty_completion (NVCF content-filter, 代码级特性) — 非配置可修复
2. Gateway zombie 检测正确 — 3-5s 快速中止，无需调整
3. 0 dsv4p_nv / kimi_nv / minimax / ms_gw 流量 — 其他 tiers 未激活, fallback 未触发
4. 0 ATE (非zombie错误), 0 fallback_occurred — 系统无其他故障模式
5. compose md5 自 R1133 未变 (48h+) — 无配置漂移
6. 所有参数在 floor/optimal — 无优化空间
7. ms_gw 0 traffic — 无 ms_gw 优化机会 (R900 模式不适用)
8. NVCF content-filter 对 164K+ 输入返回空响应的行为 — 不可通过 nv_gw 配置修复

**Zero param changes. 铁律: 只改HM1不改HM2 ✓**

## 9. 触发分析

- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit a6918d7 author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (R1133 chain 第32轮 false-trigger)
- HM1 compose 未变更，数据与 R1162 一致
- R1133→R1163: 32轮连续 false-trigger NOP, compose md5 不变 48h+
- 修复: R1162 缺少尾部换行 → 补 `\n`; 锚点 R1161→R1162

## ⏳ 轮到HM1优化HM2
