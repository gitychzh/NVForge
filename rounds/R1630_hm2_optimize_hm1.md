# R1630: HM2→HM1 — NOP (all params at floor, all failures NVCF platform-level, zero config-fixable errors)

## 触发分析

- HM1 提交: `fc9f389` — R1629: HM2→HM1 NOP
- 判定: 轮到HM2 — HM1 提交了 R1629, 需要评估
- 但 R1629 本身就是 NOP (零改动), R1628 BUDGET 66 已运行 ~2.5h

## 数据采集 (改前必有数据)

### HM1 环境 (container env)
| 参数 | 值 | 来源 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | container env |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | container env (R1628) |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | container env |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | container env |
| TIER_COOLDOWN_S | 15 | container env |
| KEY_COOLDOWN_S | 25 | container env |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | container env |
| NVU_EMPTY_200_FASTBREAK | 2 | container env |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | container env |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | container env |
| NVU_PEER_FB_SKIP_MODELS | (空) | container env |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | container env |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | container env |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | container env |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | container env |
| MIN_OUTBOUND_INTERVAL_S | 0 | container env |
| TIER_TIMEOUT_BUDGET_S | 205 | container env |
| NVU_FORCE_STREAM_UPGRADE | 0 | container env |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | container env |
| container uptime | ~33 min | docker ps |
| HM2 peer reachable | 200 OK | curl health check |

### 6h 总体 (created_at >= NOW() - INTERVAL '6 hours')
| 指标 | 值 |
|------|-----|
| 总请求 | 47 |
| 成功 | 25 (53.2%) |
| 失败 | 22 |

### 6h 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_ok_ms | avg_fail_ms |
|------|------|----|------|-----|-----------|-------------|
| dsv4p_nv | 21 | 11 | 10 | 52.4% | 17,528 | 65,831 |
| glm5_2_nv | 26 | 14 | 12 | 53.8% | 12,901 | 14,441 |

### 6h 错误分类
| 错误类型 | 数量 | 模型 | 根因 |
|---------|------|------|------|
| all_tiers_exhausted | 10 | dsv4p_nv | NVCF 504 function-level degradation |
| zombie_empty_completion | 12 | glm5_2_nv | NVCF content-filter |

### dsv4p_nv ATE 详情
- 10 ATE, 全部 all_tiers_failed_in_mapped_tier (NVCF 504 function-level)
- 全部 single tier, single key → 504 ~64s → give up
- avg 65,831ms, max 72,030ms, min 63,594ms
- Error log: `504_nv_gateway_timeout` on function `74f02205`
- 0 empty_200, 0 SSLEOF, 0 timeout, 0 429

### dsv4p_nv 成功路径
- 11 OK, avg 17,528ms, max 41,189ms
- 全部 fallback_occurred=f (本地 key 成功)

### glm5_2_nv zombie 详情
- 12 zombie_empty_completion, avg 14,441ms
- NVCF content-filter: finish_reason=stop, content_chars < 50, input > 5K
- Gateway detection 正确, 3-15s 内返回 502

### 30min 快照 (latest)
```
3req/1OK/2fail (33.3% SR)
```
- dsv4p_nv: 1 ATE (64087ms, 504_nv_gateway_timeout)
- glm5_2_nv: 1 OK + 1 zombie (12089ms)
- Peer-fb: 1 attempt, 70404ms → HM2 502 (HM2 also NVCF degraded)

### Proxy 日志 (tail 100)
```
NV-GLM52-ATTEMPT x3: k5→k2 SSLEOF→k3 (pexec_us_rr mode chain)
NV-ZOMBIE-EMPTY: glm5_2_nv, 48 chars < 50, 231K input → abort
NV-CYCLE: dsv4p_nv k4 → 504_nv_gateway_timeout
NV-TIER-FAIL: dsv4p_nv all 5 keys failed: 429=0, empty200=0, timeout=0, other=1, elapsed=64083ms
NV-PEER-FB: attempt → peer returned 502 after 70404ms → FAILED
```

### ms_gw
- 健康: `{"status":"ok"}`
- dsv4p_ms 不在 MODELMAP (R1609 移除, relay streaming sync defect)

### Peer-fallback 健康
- HM1→HM2: 1 recent attempt, 70.4s → HM2 502
- HM2 peer-fb TO=25 (HM2 自己控制, 不修改)
- HM2 也 NVCF degraded → 双方同时 504 时 peer-fb 无益

## 决策: NOP

**零参数, 零 compose 修改, 零容器重启。**

### 根因分析

| 失败数 | 错误类型 | 根因 | 可配置修复? |
|--------|---------|------|-----------|
| 10 | all_tiers_exhausted (dsv4p_nv) | NVCF 504 function-level degradation | ❌ NVCF 平台行为 |
| 12 | zombie_empty_completion (glm5_2_nv) | NVCF content-filter | ❌ NVCF 平台行为 |

**全部 22 个失败均为 NVCF 平台级别问题:**
- dsv4p_nv ATE: NVCF 504 function-level — 所有 keys 同时返回 504, 0 tier_attempts = 无 key 可轮换
- glm5_2_nv zombie: NVCF content-filter stop+<50 chars, gateway detection 正确
- dsv4p_nv 11 个成功: 本地 key 成功, avg 17.5s
- peer-fb 1 最近: 70.4s → HM2 502 (双方同时 NVCF degraded)

### 候选参数评估

| 候选 | 当前值 | 候选值 | 风险 | 收益 | 结论 |
|------|--------|--------|------|------|------|
| BUDGET_DSV4P_NV 66→60 | 66 | 60 | 504 非超时, 减 budget 无用; 60<UPSTREAM=66 违反 BUDGET≥UPSTREAM | 省 6s per ATE | ❌ 504 是 function-level, 非超时; 60<66 违反 BUDGET≥UPSTREAM |
| PEER_FALLBACK_TIMEOUT 72→66 | 72 | 66 | 66 < HM2_BUDGET(70)+2=72 → 违反 peer-fb 约束 | 省 6s per failed peer-fb | ❌ 违反 peer-fb≥PEER_BUDGET+2 约束 |
| PEER_FB_SKIP_MODELS 加 dsv4p_nv | "" | "dsv4p_nv" | 丢失 peer-fb 救援 | 省 72s per failed peer-fb | ❌ peer-fb 在 HM2 健康时有价值 |
| MS_GW_FALLBACK 加 dsv4p_nv:dsv4p_ms | (无) | 加 dsv4p_nv:dsv4p_ms | dsv4p_ms relay streaming sync defect (R1609) | 可能给 ATE 额外恢复路径 | ❌ dsv4p_ms relay 100% fails (R1609) |
| UPSTREAM_TIMEOUT 66→60 | 66 | 60 | 504 不是超时, 减 UPSTREAM 无用; 可能误杀正常请求 | 无 | ❌ 非绑定 |
| NVU_SSLEOF_RETRY_DELAY 0.5→0.3 | 0.5 | 0.3 | 可能触发更频繁连接 | 省 0.2s per SSLEOF | ❌ 1 SSLEOF in 6h, 收益 ~0.2s |
| KEY_COOLDOWN_S 25→20 | 25 | 20 | 可能触发 429 | 更快 key 恢复 | ❌ 0 key_cycle_429s, 无 key cooldown 事件 |

**全部 rejected**: 所有参数已在 floor/optimal, 全部失败是 NVCF 平台级, 不可配置修复。

### 为什么是 NOP

1. **R1628 BUDGET 66 已运行 2.5h**: 数据与 R1629 评估一致, 所有失败 NVCF 平台级
2. **所有参数在 floor**: BUDGET=66=UPSTREAM, PEER_FB=72=HM2_BUDGET+2, FASTBREAK=1, MIN_OUTBOUND=0, SSLEOF=0.5
3. **所有失败 NVCF 平台级**: 504 function-level + content-filter zombie, 非 nv_gw config 可修复
4. **双方同时 degraded**: peer-fb 70.4s → HM2 502, 证实双方 NVCF 同时出问题, 不是 HM1 配置问题
5. **ms_gw dsv4p_ms 不可用**: R1609 验证 relay streaming sync defect, 100% fails
6. **铁律:只改HM1不改HM2** ✓

### 与 R1629 对比
- R1629: NOP (R1628 刚部署 2h, post-restart 0 req)
- R1630: NOP (R1628 运行 2.5h 后数据一致: 全部 NVCF 平台级, 参数 floor)
- 连续两轮 NOP: NVCF 本身 degraded, 等 NVCF 恢复后才有优化空间

## 铁律验证
- ✅ 只改HM1: 未修改任何配置
- ✅ 改前必有数据: 6h DB + docker logs + error log 分析
- ✅ 改后必有验证: 无需验证 (NOP)
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮文件 + git push
## ⏳ 轮到HM1优化HM2
