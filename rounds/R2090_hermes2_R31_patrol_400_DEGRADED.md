# R2090: hermes2 R31 巡检 — NVCF dsv4p function DEGRADED, SR=0%

> **日期**: 2026-07-20
> **轮次**: hermes2 R31 (仓库 R2090)
> **类型**: 巡检轮 (不改代码)
> **模式**: 暂停自优化, 等 NVCF 恢复

## ⚠️ 重大诊断修正: 不是"502 灾难", 是"NVCF function DEGRADED"

R30 的诊断是"NVCF 后端 502 灾难级故障"。本轮 nv_gw 日志揭露了**完全不同的根因**:

```
[NV-NONCYCLE-ERR] tier=dsv4p_nv k3 resp.status=400 non-cycling, aborting tier (no key cycle).
  body={"status": 400, "title": "Bad Request",
  "detail": "Function id '74f02205-c7ba-438f-b81a-2537955bd7ec': DEGRADED function cannot be invoked"}

[NV-TIER-DEGRADED] tier=dsv4p_nv marked DEGRADED cooldown 60s (400 DEGRADED non-cycling)

[NV-TIER-DEGRADED-SKIP] tier=dsv4p_nv in DEGRADED cooldown, short-circuit (skip key loop) → tier fail
```

**真相**: NVCF 返回的原始响应是 **400** (不是 502), 消息是 "DEGRADED function cannot be invoked"。
nv_gw 的 R814 DEGRADED short-circuit 逻辑正确检测到 400 DEGRADED, 标记 tier 为 DEGRADED 并设置 60s cooldown。
cooldown 期间所有请求被短接跳过 (NV-TIER-DEGRADED-SKIP), 不实际发送到 NVCF。
cooldown 过期后下一发请求又命中 400 DEGRADED → 再次标记 cooldown → 死循环。

DB 里看到的 502 是 hm4104 层面的状态码 (primary 故障 → 返回 502), 不是 NVCF 原始响应码。

## 数据依据 (30min 窗口, 北京时间 22:13-22:43)

### nv_requests (dsv4p_nv)

| 状态 | 数量 | 占比 |
|------|------|------|
| 502 | 143 | 96.6% |
| 429 | 5 | 3.4% |
| 200 | 0 | 0% |
| **总计** | **148** | **SR=0%** |

### 1h 窗口补充

| 状态 | 数量 |
|------|------|
| 200 | 14 |
| 502 | 255 |
| 429 | 11 |
| 总计 | 280 |
| **SR** | **5.0%** |

(1h SR=5.0% 说明 30min 前还有零星成功, 最近 30min 完全归零)

### 错误分类

- `all_tiers_exhausted`: 148 (100% 失败)
- Tier 层: pexec_success=3, pexec_conn_RemoteDisconnected=1 (可能是 glm5_2 的流量)

### nv_gw 日志 DEGRADED 统计

- 过去 500 行日志中 DEGRADED 出现 120 次
- "cannot be invoked" 出现 22 次 (实际 NVCF 400 响应)
- 其余 98 次是 DEGRADED-SKIP (cooldown 期间短接)

### fallback (hm4104 日志)

- 30min fallback 关键词: 209 次
- PRIMARY-FAIL-STREAM: 持续 (上游 502)
- PRIMARY-BREAKER-SKIP-STREAM: 持续 OPEN
- FALLBACK-FAIL-STREAM: ms_gw 也有 30s timeout

### 调用方分布

| caller | 502 | 429 | 200 |
|--------|-----|-----|-----|
| other | 131 | 4 | 0 |
| unknown | 9 | 1 | 0 |
| openclaw | 3 | 0 | 0 |

(全部失败, 无成功请求)

### 与 R30 对比

| 指标 | R30 | R31 | 变化 |
|------|-----|-----|------|
| 502 | 112 | 143 | +27.7% ❌ |
| 429 | 9 | 5 | -44.4% |
| 200 | 12 | 0 | -100% ❌ |
| 总请求 | 133 | 148 | +11.3% |
| **SR** | **9.0%** | **0%** | **-9.0pp** ❌❌❌ |

## 六轮 502/SR 趋势 (R26-R31)

| 轮次 | 502 | SR | Tier 429 | 判断 |
|------|-----|-----|----------|------|
| R26 | 6 | 73.1% | 57 | 持续恢复 |
| R27 | 9 | 55.0% | 28 | 恶化 |
| R28 | 10 | 50.0% | 22 | 恶化 |
| R29 | 11 | 35.3% | 13 | 触发阈值 |
| R30 | 112 | 9.0% | 6 | 灾难级 |
| **R31** | **143** | **0%** | 5 | **功能 DEGRADED** |

## 核心判断

**NVCF dsv4p function (74f02205-c7ba-438f-b81a-2537955bd7ec, ai-deepseek-v4-pro) 在 NVCF 平台侧被标记为 DEGRADED 状态。** 这不是"后端 502" (网关故障), 而是 NVCF 平台主动将该 function 置为 DEGRADED (可能原因: 后端资源不足、维护中、配额耗尽、或 NVCF 内部问题)。

nv_gw 的 R814 DEGRADED short-circuit 逻辑**正确工作**:
- 检测到 400 DEGRADED → 标记 tier cooldown 60s
- cooldown 期间跳过所有请求 (不浪费资源)
- cooldown 过期后重新探测 → 又命中 400 DEGRADED → 循环

**根因在天 (NVCF 平台侧), 不在人 (nv_gw 配置)**。nv_gw 配置正确, R814 DEGRADED 处理逻辑正确, 但 NVCF 平台将该 function 置为 DEGRADED 后, 任何 key 都返回 400。

## 本轮改动

**无** (巡检轮, 不改代码)

## 验证

- `curl /health`: OK
- `docker ps`: nv_gw / hm4104 / ms_gw / logs_db all running
- nv_gw 日志: DEGRADED cooldown 循环正常 (R814 逻辑正确工作)

## 下一步 (R32 = 继续巡检, 等 NVCF 恢复 DEGRADED 状态)

### R32 决策矩阵

| 条件 | 决策 |
|------|------|
| 400 DEGRADED 消失, SR > 70% 持续 2 轮 | 恢复优化模式 |
| 400 DEGRADED 消失, SR > 50% | 巡检轮, 标注"恢复中" |
| 400 DEGRADED 持续, SR < 20% | 巡检轮, 标注"NVCF function DEGRADED, 需人为联系 NVCF" |

### 如果连续 3 轮 (R29-R31) 仍然 DEGRADED

**强烈建议人为介入联系 NVCF 支持**, 询问 function_id `74f02205-c7ba-438f-b81a-2537955bd7ec` (ai-deepseek-v4-pro) 为何被置为 DEGRADED 状态, 以及预计何时恢复。

### 不要做的事

- 不要重启 nv_gw (DEGRADED 是 NVCF 侧状态, 重启无效)
- 不要改任何 nv_gw 参数 (根因不在 nv_gw)
- 不要动 ms_gw (它是当前唯一能用的链路)
- 不要改 NVCF function_id (除非 NVCF 侧提供新的 function_id)
- 不要调低 DEGRADED cooldown (R814 的 60s 是合理的, 调低只会增加对 NVCF 的无用请求)