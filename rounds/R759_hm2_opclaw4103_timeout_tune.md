# R759: HM2 opclaw4103 超时下调 — 修复 openclaw "LLM request failed" (stuck session abort)

> 仅改 HM2 opclaw4103 adapter env。HM1 全未动。nv_gw/ms_gw 源码未动 (模块化铁律)。

## 改前数据 (openclaw 飞书报 "LLM request failed")

### openclaw 本体日志
- `00:28:36 stuck session recovery: age=270s action=abort_embedded_run`
- `00:28:37 rawError=Request was aborted ... decision=surface_error from=opclaw4103/glm5_2_nv`
- `stuckSessionAbortMs=240000` (openclaw.json: 240s 强制 abort embedded run)

### opclaw4103 改前配置
- PRIMARY_STREAM_TIMEOUT_S=150, FALLBACK_TIMEOUT_S=300, PROXY_TIMEOUT=300
- 最坏: 150s (primary) + 300s (fallback) = 450s >> openclaw 240s stuck abort

### glm5_2_nv 3h (HM2) 量化
- 53 req / 31 OK (58.5%) / 22 502
- 成功 p50=7.1s p90=52s, 失败 avg=90s p50=110s (TIER_TIMEOUT_BUDGET=110 耗尽)
- 失败 100% all_tiers_exhausted, HM2 本地全失败, 靠 PEER-FB 到 HM1 救活

### 故障链
1. openclaw 发流式请求到 opclaw4103 (240s stuck abort 计时开始)
2. opclaw4103 等 primary (nv_gw/glm5_2_nv), nv_gw 本地 tier 110s 耗尽 + PEER-FB 90s = 最坏 200s
3. opclaw4103 PRIMARY_STREAM_TIMEOUT_S=150 在 nv_gw PEER-FB 期间触发 → fallback ms_gw
4. fallback ms_gw 流读取再耗 120s+ → 总 270s+ 超过 openclaw 240s stuck
5. openclaw abort embedded run → `rawError=Request was aborted` → "LLM request failed"

## 改动 (单容器 env, opclaw4103 only)

### opclaw4103 env 调整
| 参数 | 改前 | 改后 | 理由 |
|---|---|---|---|
| PRIMARY_STREAM_TIMEOUT_S | 150 | 90 | glm5_2_nv 成功 p90=52s, 90s 覆盖; 失败 110s 到顶, 90s 已注定失败, 早切 fallback |
| FALLBACK_TIMEOUT_S | 300 | 120 | fallback ms_gw 不该再耗 300s, 120s 够 glm5_2_ms 流式 |
| PROXY_TIMEOUT | 300 | 240 | 对齐 openclaw stuckSessionAbortMs=240s, 留余量 |
| CIRCUIT_FAILURE_THRESHOLD | 3 | 2 | glm5_2_nv HM2 系统性故障 (58.5%), 2 次即开 circuit 避免第 3 次浪费 90s |
| CIRCUIT_OPEN_S | 60 | 300 | 打开后 5min 内直接 fallback, 不重试 primary (glm5_2_nv HM2 短期不会好) |
| FALLBACK_RECOVER_S | 30 | 120 | fallback 后 2min 内不探 primary, 避免每 30s 探一次浪费 |

### 最坏耗时对比
- 改前: 150 + 300 = 450s >> 240s stuck → abort
- 改后: 90 + 120 = 210s < 240s stuck (30s 余量)
- circuit 打开后: 直接 fallback ~5s

### 不改的东西
- 不改 openclaw.json stuckSessionAbortMs (agent 配置, 铁律不碰; 且 240s 合理)
- 不改 nv_gw/ms_gw 源码 (模块化)
- 不改 HM1
- 不改 hm4104/oc4105/cx4102 (它们各自场景不同: hm4104 dsv4p_nv 64.9%, oc4105 kimi_nv 无 fallback, cx4102 已 R751 调过)

## 改后验证

### env 生效
- PRIMARY_STREAM_TIMEOUT_S=90, FALLBACK_TIMEOUT_S=120, CIRCUIT_FAILURE_THRESHOLD=2, CIRCUIT_OPEN_S=300, FALLBACK_RECOVER_S=120 ✓
- health 200 ✓

### 实测
- 非流 primary 失败路径: 90s timeout 触发 PRIMARY-FAIL → fallback ms_gw → 200 + 提醒 "⚠️ [opclaw4103] primary 故障/超时, 已 fallback 到 glm5_2_ms" ✓
- circuit 打开后秒回: 第 2 次请求直接 fallback (2s 返回) ✓
- PEER-FB 救活路径: nv_gw 本地全失败 → PEER-FB HM1 成功 → opclaw4103 收 200 (50s) ✓

### 关键指标
- STREAM-UPSTREAM-ERR (openclaw abort 真因): 改前 2 次/h → 改后 0 ✓
- opclaw4103 总最坏耗时: 450s → 210s < 240s stuck ✓

## 预期 (待飞书实测)
- openclaw 不再 "LLM request failed" (240s 内必返回)
- glm5_2_nv primary 成功时 ~50-70s (PEER-FB 救活)
- glm5_2_nv primary 失败时 ~95s (90s timeout + 5s fallback)
- circuit 打开后 ~5s (直接 fallback ms_gw)

## 风险
- 低: 只改 adapter env, 不碰源码/agent 配置/HM1
- 回滚: env 改回即可
- 注意: circuit 打开后 5min 内 openclaw 全走 ms_gw (glm5_2_ms), 模型一致性保持 (同 glm5.2)

## 遗留
- glm5_2_nv HM2 系统性 58.5% (R696/R705 已知: HM2 mihomo 出口打 NVCF glm5.2 function 挂) — 非 adapter 可解, 靠 PEER-FB HM1 兜底
- UPSTREAM_TIMEOUT=40 漂移 (R758 遗留) 下轮处理
- HM1 同步待授权
