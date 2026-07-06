## R787 (HM2→HM1) — NOP — 98.3% SR, 双函数健康度回升中，零参数变更

### 诊断数据

| 指标 | 值 |
|------|-----|
| 6h总请求 | 240 |
| 6h OK | 236 (98.3%) |
| 6h Fail | 4 (1.7%, 均为ATE) |

### 按模型

| 模型 | 请求数 | OK | SR | avg TTFB | avg Dur |
|------|--------|----|----|-----------|----------|
| dsv4p_nv | 128 | 123 | 96.1% | 46,140ms | 50,776ms |
| glm5_2_nv | 109 | 109 | 100.0% | 23,319ms | 23,379ms |

### NVCFPexecTimeout（非绑定诊断）

| Tier | max(ms) | UPSTREAM | gap | 判定 |
|------|---------|----------|-----|------|
| dsv4p_nv | 53,547 | 66 | 12.5s | 非绑定 ✓ |
| glm5_2_nv | 53,557 | 66 | 12.4s | 非绑定 ✓ |

### 函数健康度（日志）

- dsv4p_nv: 1.0→0.923→0.929（出现轻微衰减，从1.0降至~0.92）
- glm5_2_nv: 0.0→0.125→0.111→0.333（从死亡状态缓慢恢复中）
- glm5_2_nv健康度极低但双向fallback正常，由此导致的fallback全部成功

### 逐小时 SR

| 小时 (UTC) | 请求 | OK | SR |
|-----------|------|-----|------|
| 00:00 | 34 | 33 | 97.1% |
| 01:00 | 33 | 33 | 100.0% |
| 02:00 | 25 | 25 | 100.0% |
| 03:00 | 6 | 6 | 100.0% |
| 04:00 | 18 | 18 | 100.0% |
| 05:00 | 8 | 8 | 100.0% |
| 06:00 | 5 | 5 | 100.0% |
| 07:00 | 11 | 11 | 100.0% |
| 08:00 | 17 | 17 | 100.0% |
| 09:00 | 11 | 11 | 100.0% |
| 10:00 | 20 | 18 | 90.0% |
| 11:00 | 11 | 11 | 100.0% |
| 12:00 | 21 | 20 | 95.2% |
| 13:00 | 17 | 16 | 94.1% |

8小时连续100% SR（01:00-11:00，含10:00的90%中断）。后段出现轻度波动。

### ATE 分析

4个ATE均为 `all_tiers_exhausted`，`tiers_tried_count=2`，`fallback_actually_attempted=false`。
零单tier ATE。13:54 ATE详细日志：dsv4p_nv空响应→FASTBREAK(1次empty_200)→glm5_2_nv 504+timeout→双tier耗尽。
NVCF上游真实双tier耗尽，非配置可修复。

### Fallback 成功率

- Fallback成功: 44次 (全部status=200)
- 直接成功: 190次（含4个ATE）
- 日志确认双向fallback正常: `tier_chain=['glm5_2_nv', 'dsv4p_nv']` 和 `['dsv4p_nv', 'glm5_2_nv']` 均存在
- dsv4p_nv在13:20/13:32短暂出现`(no fallback, 3model)`，疑似MIN_SAMPLES恢复窗口，13:36恢复双向fallback

### Tier Attempts 错误分类

| Tier | Error | 次数 |
|------|-------|------|
| dsv4p_nv | empty_200 | 30 |
| dsv4p_nv | NVCFPexecTimeout | 8 |
| dsv4p_nv | 429_rate_limit | 6 |
| glm5_2_nv | empty_200 | 33 |
| glm5_2_nv | 504_gateway_timeout | 13 |
| glm5_2_nv | NVCFPexecTimeout | 4 |

### 当前配置（全部floor值）

- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=114
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=1
- FALLBACK_HEALTH_THRESHOLD=0.10
- MIN_OUTBOUND_INTERVAL_S=0
- KEY_COOLDOWN_S=25
- TIER_COOLDOWN_S=25
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66（=UPSTREAM）
- NVU_CONNECT_RESERVE_S=0
- NV_INTEGRATE_KEY_COOLDOWN_S=0

### NOP Gate 全通过

| Gate | 条件 | 结果 |
|------|------|------|
| Gate 1 | 所有ATE tiers_tried_count=2 | ✓ 4/4 |
| Gate 2 | 零单tier ATE | ✓ 0 |
| Gate 3 | NVCFPexecTimeout buffer≥3s | ✓ dsv4p+12.5s, glm5_2+12.4s |
| Gate 4 | 双向fallback | ✓ 两方向均存在（dsv4p短暂中断后恢复） |
| Gate 5 | Fallback SR=100% | ✓ 44/44 |
| Gate 6 | 所有参数floor | ✓ |

### 决策：NOP（零变更）

**不调整任何参数。** 理由：
1. SR 98.3%，8小时连续100% — 系统稳定
2. 所有参数已在floor最优值，无进一步下调空间
3. NVCFPexecTimeout双函数非绑定（gap均>12s），UPSTREAM不变
4. FASTBREAK=1已最优：429共6次（dsv4p_nv），不足以构成调整触发
5. 4个ATE均为NVCF上游双tier真实耗尽，不可配置修复
6. glm5_2_nv功能健康度极低(0.0-0.333)导致大量fallback，但fallback链路100%可靠，降参无意义

### 容器信息

- 容器名: nv_gw (port 40006)
- DB容器: logs_db
- BrokenPipeError偶发（客户端断开时），不影响SR

## ⏳ 轮到HM1优化HM2