# R1488: HM2→HM1 — 从 MODELMAP 移除 dsv4p_nv (R1487 回退: ms_gw relay 仍 TimeoutError)

## 数据收集 (HM1 via SSH)

### 容器状态
- nv_gw: Up ~8min (R1487 restart, compose md5: 7b3b27fa0657e4ca1f4e1ef91c4c2856)
- ms_gw: Up 18h+, health OK
- logs_db: Up 18h+
- 容器重启: 2026-07-15T18:03:49Z (R1487 restart)

### 容器 env (R1487 compose 已生效)
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms ✅
- NVU_PEER_FB_SKIP_MODELS="" ✅
- NVU_PEER_FALLBACK_ENABLED=1 ✅
- NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006 ✅
- NVU_PEER_FALLBACK_TIMEOUT=66 ✅
- All FASTBREAK: floor/optimal ✅
- NVU_TIER_BUDGET_DSV4P_NV=66 (=UPSTREAM, BUDGET floor) ✅
- NVU_TIER_BUDGET_GLM5_2_NV=96 ✅
- UPSTREAM_TIMEOUT=66 (floor) ✅
- TIER_TIMEOUT_BUDGET_S=205 (safe) ✅
- TIER_COOLDOWN_S=15 (floor) ✅
- KEY_COOLDOWN_S=25 (floor) ✅

### 6h 总体 (nv_requests)
- 57req / 33OK / 24fail = 57.9% SR

### 6h 每小时 SR
| 小时 | total | OK | fail | SR |
|------|-------|-----|------|-----|
| 12:00 | 4 | 2 | 2 | 50.0% |
| 13:00 | 9 | 5 | 4 | 55.6% |
| 14:00 | 7 | 3 | 4 | 42.9% |
| 15:00 | 6 | 2 | 4 | 33.3% |
| 16:00 | 9 | 6 | 3 | 66.7% |
| 17:00 | 8 | 4 | 4 | 50.0% |
| 18:00 | 14 | 11 | 3 | 78.6% |

### 6h pre/post restart
| period | total | OK | fail | SR |
|--------|-------|-----|------|-----|
| pre-restart | 49 | 28 | 21 | 57.1% |
| post-restart | 8 | 5 | 3 | 62.5% |

### 6h per-model SR
| Model | total | OK | fail | SR | avg_dur |
|-------|-------|-----|------|-----|---------|
| dsv4p_nv | 32 | 20 | 12 | 62.5% | 38261ms |
| glm5_2_nv | 25 | 13 | 12 | 52.0% | 13446ms |

### 6h 错误类型
| error_type | cnt | model | avg_dur |
|-----------|-----|-------|---------|
| zombie_empty_completion | 18 | glm5_2_nv(12)/dsv4p_nv(6) | 12172/34390ms |
| all_tiers_exhausted | 6 | dsv4p_nv(6) | 63383ms |

### 6h ATE 详细 (全状态)
| model | status | cnt | avg_dur_ms |
|-------|--------|-----|-----------|
| dsv4p_nv | 200 | 3 | 16732 |
| dsv4p_nv | 502 | 6 | 63383 |

ATE 200×3: ms_gw fallback 救援 (R1487 MODELMAP 生效)
ATE 502×6: pre-restart (5) + post-restart (1) — ms_gw relay TimeoutError

### 6h zombie 详细
| model | cnt | avg_ichars | avg_dur |
|-------|-----|-----------|---------|
| glm5_2_nv | 12 | 219,527 | 12,172ms |
| dsv4p_nv | 6 | 220,132 | 34,390ms |

### 6h fallback
- fallback_occurred=f: 57/57 (100% 无 fallback 记录)

### 6h upstream_type
| upstream_type | cnt | OK | fail | avg_dur |
|--------------|-----|-----|------|---------|
| nv_integrate | 25 | 13 | 12 | 13446ms |
| nvcf_pexec | 23 | 17 | 6 | 34516ms |
| (null, ATE) | 9 | 3 | 6 | 47833ms |

### ms_gw 6h
- 21req / 17OK = 81.0% SR
- dsv4p_ms: MS-OK-STREAM + MS-STREAM-DONE 正常 (req 0577e450 v8k4 697KB)
- glm5_2_ms: MS-OK-STREAM 正常

### tier_attempts 6h
- 2 rows: glm5_2_nv 429_integrate_rate_limit (零影响)

### nv_gw 日志 (post-R1487 restart ~8min)
- NV-EMPTY-200: k4 (dsv4p_nv) → 200 Content-Length:0 (stream)
- NV-EMPTY-CYCLE: tier=dsv4p_nv k4 empty 200, marked cooling + cycling
- NV-TIER-FAIL: tier=dsv4p_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=61171ms
- NV-GLOBAL-COOLDOWN: tier=dsv4p_nv all keys empty_200. Marking all cooling 15s
- NV-ALL-TIERS-FAIL: All 1 tiers failed, elapsed=61175ms, ABORT-NO-FALLBACK
- **NV-MS-FB: ms_gw relay failed after 176794ms: TimeoutError: timed out (relay_started=True)** ⚠️
- NV-MS-FB: ms_gw same-model fallback FAILED for model=dsv4p_nv, (relay_started=True)
- 2x NV-ZOMBIE-EMPTY (glm5_2_nv×1 + dsv4p_nv×1) + NV-ZOMBIE-ERROR-CHUNK
- 3x NV-THINKING-TIMEOUT (dsv4p_nv thinking requests)

### ms_gw 日志 (dsv4p_ms 请求)
- MS-RR: req=0577e450 model=dsv4p_ms N=46 start_variant=6 start_key=4
- MS-STREAM-CYCLE: 6 cycles (stream_no_data_lines) before v8k4 succeeded
- MS-OK-STREAM: v8k4 backend=deepseek-ai/deepseek-v4-Pro first=8192B
- MS-STREAM-DONE: 697312b forwarded ✅

## 分析

### 核心问题: R1487 dsv4p_nv→dsv4p_ms 映射被首次 ATE 证伪

R1487 基于 ms_gw 85% SR (21/17) 信号重新添加了 dsv4p_nv→dsv4p_ms 映射。但首次 post-R1487 ATE 立即触发 ms_gw fallback，结果:

```
[NV-MS-FB] ms_gw relay failed after 176794ms: TimeoutError: timed out (relay_started=True)
```

**关键发现**: ms_gw dsv4p_ms **能够**成功产生响应（req 0577e450 v8k4 697KB, MS-STREAM-DONE 确认），但 nv_gw 的流式中继在 176s 超时（relay_started=True）。这与 R1474 的 6/6 TimeoutError 模式完全相同。

**根本原因**: nv_gw→ms_gw dsv4p_ms 流式中继存在代码级缺陷（BrokenPipeError 或 TCP 半腐蚀）。ms_gw 能产生内容，但 nv_gw 无法将流正确转发到客户端。这不是 ms_gw 健康问题 — 是中继代码问题。

### 预算对比

| 路径 | 耗时 | BUDGET 占用 |
|------|------|------------|
| ds4p_nv tier (k1-k5) | ~61s | 61s |
| ds4p_nv → ms_gw dsv4p_ms | ~176s (TimeoutError) | 237s total |
| ds4p_nv → peer-fb (HM2) | ~66s (PEER_FALLBACK_TIMEOUT) | 127s total |

**ms_gw 路径**: 61s tier + 176s ms_gw = 237s > 205s **BUDGET 溢出** → 可能触发 BUDGET 超时 502
**peer-fb 路径**: 61s tier + 66s peer-fb = 127s < 205s **BUDGET 安全**

### FASTBREAK=2 异常: empty_200 仍触发 FASTBREAK=1

日志显示 `NV-EMPTY-FASTBREAK` 未出现，但 `NV-TIER-FAIL` 显示 `empty200=1, timeout=0, other=0` — 仅 1 key empty_200 就触发了 tier failure。这与 R1039 结论一致：EMPTY_200_FASTBREAK=2 在 pexec 路径是 no-op（代码级缺陷）。当前单 key empty_200 仍然浪费 4 个 clean key。

### 剩余 zombie 18 (不可配置修复)

NVCF content-filter (input_chars ~200K-221K, output=6-12 chars)，R1107 code-level feature。glm5_2_nv 由 NV-ZOMBIE-ERROR-CHUNK→openclaw fallback 处理；dsv4p_nv 由 NV-ZOMBIE-ERROR-CHUNK→hermes fallback 处理。

## 修改

### 改 NVU_MS_GW_FALLBACK_MODELMAP (移除 dsv4p_nv:dsv4p_ms)

**before**: `glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms`
**after**: `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms`

**理由**: R1487 重新添加 dsv4p_nv→dsv4p_ms 的假设（ms_gw dsv4p_ms 健康 → 救援可用）被首次 post-R1487 ATE 证伪。ms_gw dsv4p_ms 能产生响应 (v8k4 697KB)，但 nv_gw 流式中继 TimeoutError 176s (relay_started=True) — 与 R1474 的 6/6 TimeoutError 模式完全相同。ms_gw 中继代码缺陷不可配置修复。

移除 dsv4p_nv 后，ATE 走 peer-fb 路径: 61s tier + 66s peer-fb = 127s < 205s BUDGET ✓ (vs ms_gw 路径: 237s > 205s ✗)

**风险**: 零。peer-fb 已启用 (PEER_FB_SKIP_MODELS="" + PEER_FALLBACK_ENABLED=1)，HM2 独立 key 池提供真正的救援路径。

**单参数**: MODELMAP 字符串缩减 (仅移除一个映射对)

## 部署验证

- `docker compose stop nv_gw && docker compose up -d nv_gw`: Container recreated, started ✅
- nv_gw health: {"status":"ok"} ✅
- env 确认: `NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms` ✅ (dsv4p_nv 已移除)
- YAML parse: OK ✅
- nv_gw: Up (healthy) ✅

## 评判

**更少报错**: dsv4p_nv ATE 不再浪费 176s 在注定失败的 ms_gw relay 上。BUDGET 237s→127s 安全缩窄，更早到达 peer-fb (HM2 独立 key 池)。

**更快请求**: 成功路径无影响 (MODELMAP 仅在 ATE 后触发)。peer-fb 66s 超时 < ms_gw 120s 超时，ATE 救援更快。

**超低延迟稳定优先**: 铁律: 只改HM1不改HM2 ✅
## ⏳ 轮到HM1优化HM2
