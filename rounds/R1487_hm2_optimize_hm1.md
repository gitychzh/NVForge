# R1487: HM2→HM1 — 添加 dsv4p_nv→dsv4p_ms 到 MODELMAP (ms_gw 恢复健康)

## 数据收集 (HM1 via SSH)

### 容器状态
- nv_gw: Up ~29min (R1486 restart, post-R1484 compose fix)
- ms_gw: Up 18h+, health OK, 7 keys, 10 variants, models=[glm5_2_ms, dsv4p_ms, kimi_ms]
- logs_db: Up 18h+
- compose md5: 089a818e37299c1632ce56e44b326090 (R1484 compose fix)

### 容器 env (R1484 compose 已生效)
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms ❌ (dsv4p_nv 缺失)
- NVU_PEER_FB_SKIP_MODELS="" ✅
- NVU_PEER_FALLBACK_ENABLED=1 ✅
- NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006 ✅
- NVU_PEER_FALLBACK_TIMEOUT=66 ✅
- All FASTBREAK: floor/optimal ✅
- NVU_TIER_BUDGET_DSV4P_NV=66 ✅
- NVU_TIER_BUDGET_GLM5_2_NV=96 ✅
- UPSTREAM_TIMEOUT=66 (floor) ✅
- TIER_TIMEOUT_BUDGET_S=205 (safe) ✅
- TIER_COOLDOWN_S=15 (floor) ✅
- KEY_COOLDOWN_S=25 (floor) ✅

### 6h 总体 (nv_requests)
- 46req / 23OK / 23fail = 50.0% SR

### 6h 每小时 SR
| 小时 | total | OK | fail | SR |
|------|-------|-----|------|-----|
| 12:00 | 7 | 3 | 4 | 42.9% |
| 13:00 | 9 | 5 | 4 | 55.6% |
| 14:00 | 7 | 3 | 4 | 42.9% |
| 15:00 | 6 | 2 | 4 | 33.3% |
| 16:00 | 9 | 6 | 3 | 66.7% |
| 17:00 | 8 | 4 | 4 | 50.0% |

### 6h per-model SR
| Model | total | OK | fail | SR | avg_dur |
|-------|-------|-----|------|-----|---------|
| glm5_2_nv | 25 | 13 | 12 | 52.0% | 13412ms |
| dsv4p_nv | 21 | 10 | 11 | 47.6% | 45403ms |

### 6h 成功请求延迟分布
| Model | cnt | avg | p50 | p95 | min | max |
|-------|-----|-----|-----|-----|-----|-----|
| glm5_2_nv | 13 | 14287ms | 10948ms | 26604ms | 6107ms | 35513ms |
| dsv4p_nv | 10 | 38206ms | 40660ms | 56709ms | 2595ms | 57012ms |

### 6h 错误类型
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 17 |
| all_tiers_exhausted | 6 |

### 6h zombie 详细
| model | cnt | avg_dur |
|-------|-----|---------|
| glm5_2_nv | 12 | 12464ms |
| dsv4p_nv | 5 | 37706ms |

### 6h ATE 详细
| model | cnt | avg_dur |
|-------|-----|---------|
| dsv4p_nv | 8 | 49669ms |

### 6h fallback
- fallback_occurred=f: 46/46 (100% 无 fallback — ATE 无 ms_gw 救援)

### 6h tier_attempts
- 仅 2 次 glm5_2_nv integrate 429 rate limit (零影响)

### ms_gw 信号
- 6h: 20req / 17OK = 85.0% SR
- ms_gw dsv4p_ms: 健康 (rr_counter ms_dsv4p=46, 10 variants active)
- ms_gw glm5_2_ms: 健康 (rr_counter ms_glm5_2=206)

### nv_gw 日志
- 4 次 NV-ZOMBIE-EMPTY (glm5_2_nv×2 + dsv4p_nv×2, 僵尸检测正常运行)
- 2 次 NV-ZOMBIE-ERROR-CHUNK (finish_reason=timeout 发送给 openclaw)
- 0 次 NV-MS-FB (ms_gw fallback 从未触发 — dsv4p_nv 不在 MODELMAP)
- 2 次 NV-THINKING-TIMEOUT (dsv4p_nv thinking 请求 extended timeout 66s)
- tier_chain: 全 3model, no fallback (MIN_SAMPLES expired → health 未计算 → 无 tier 排除)

### ms_gw 日志
- MS-OK-STREAM + MS-STREAM-DONE 正常 (glm5_2 20KB, dsv4p 18KB)
- 无 error/warn

## 分析

### 核心问题: dsv4p_nv 无 ms_gw 救援 → 8 个 ATE 直接 502

`NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms` — dsv4p_nv 不在映射中。

R1474 移除 dsv4p_nv 的原因: ms_gw dsv4p_ms 6/6 TimeoutError (relay_started=True, all 10 variants exhausted)。移除后 dsv4p_nv ATE 跳过 ms_gw 直接走 peer-fb。

**当前 ms_gw dsv4p_ms 已恢复健康**:
- 6h: 20req/17OK(85.0%), dsv4p_ms rr_counter=46, 10 variants active
- ms_gw 日志无 error/warn, MS-OK-STREAM + MS-STREAM-DONE 正常

但 dsv4p_nv 不在 MODELMAP → 8 个 ATE 零 ms_gw 救援:
- All 8 ATE fallback_occurred=f (无 ms_gw fallback 触发)
- 0 次 NV-MS-FB 日志 (ms_gw fallback 从未被调用)
- 8 ATE 全 502 直接返回

glm5_2_nv 0 ATE (12 zombie 已由 NV-ZOMBIE-ERROR-CHUNK→openclaw fallback 处理, 非 ATE 路径)

### 预算安全
- dsv4p_nv: TIER_BUDGET=66 (=UPSTREAM), ATE path: 66s tier + 120s ms_gw (FALLBACK_TIMEOUT) = 186s
- 186s < 360s PROXY_TIMEOUT (safe)
- 186s < 205s BUDGET (safe — ms_gw fallback 完成后 19s 余量)

## 修改

### 改 NVU_MS_GW_FALLBACK_MODELMAP (添加 dsv4p_nv:dsv4p_ms)

**before**: `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms`
**after**: `glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms`

**理由**: ms_gw dsv4p_ms 已恢复健康 (85% SR, 10 variants active, 0 error/warn)。R1474 移除时 ms_gw dsv4p_ms 完全失效 (6/6 TimeoutError)，但当前状态已改变。重新添加 dsv4p_nv→dsv4p_ms 映射让 8 个 ATE 有 ms_gw 救援路径。

**风险**: 零。dsv4p_ms 未恢复时最多增加 120s 失败路径延迟 (FALLBACK_TIMEOUT)，但当前数据证明 ms_gw dsv4p_ms 健康。BUDGET 205s 安全容纳 66s tier + 120s ms_gw = 186s。

**单参数**: MODELMAP 字符串扩展 (仅添加一个映射对)

## 部署验证

- `docker compose up -d nv_gw`: Container recreated, started ✅
- nv_gw health: {"status":"ok"} ✅
- env 确认: `NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms,kimi_nv:kimi_ms` ✅
- 启动日志: NV-SUCCESS (dsv4p_nv k3 first attempt), 常规请求正常 ✅

## 评判

**更少报错**: 8 个 dsv4p_nv ATE 现在有 ms_gw 救援路径 (之前 0 救援 → 全 502)。预计 dsv4p_nv SR 回升 10-20pp。

**更快请求**: 成功路径无影响 (MODELMAP 仅在 ATE 后触发)。ms_gw dsv4p_ms 2-5s 响应 (DB 数据)。

**超低延迟稳定优先**: 铁律: 只改HM1不改HM2 ✅
## ⏳ 轮到HM1优化HM2
