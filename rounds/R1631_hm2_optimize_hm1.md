# R1631: HM2→HM1 — NOP (all params at floor, all failures NVCF platform-level, zero config-fixable errors. 3rd consecutive NOP)

## 触发分析

- HM1 提交: `5562184` — R1630: HM2→HM1 NOP
- 判定: 轮到HM2 — HM1 提交了 R1630, 需要评估
- R1630 本身就是 NOP (零改动), R1628 BUDGET 66 已运行 ~3h

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

### 6h 总体 (created_at >= NOW() - INTERVAL '6 hours')
| 指标 | 值 |
|------|-----|
| 总请求 | 46 |
| 成功 | 23 (50.0%) |
| 失败 | 23 |

### 6h 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_ok_ms | avg_fail_ms |
|------|------|----|------|-----|-----------|-------------|
| dsv4p_nv | 20 | 9 | 11 | 45.0% | 16,493 | 65,633 |
| glm5_2_nv | 26 | 14 | 12 | 53.8% | 12,860 | 14,223 |

### 6h 错误分类
| 错误类型 | 数量 | 模型 | 根因 |
|---------|------|------|------|
| all_tiers_exhausted | 11 | dsv4p_nv | NVCF 504 function-level degradation |
| zombie_empty_completion | 12 | glm5_2_nv | NVCF content-filter |

### dsv4p_nv ATE 详情
- 11 ATE, 全部 all_tiers_failed_in_mapped_tier (NVCF 504 function-level)
- 全部 single tier, single key → 504 ~64s → give up
- avg 65,633ms, max 72,030ms, min 63,594ms
- Error log: `504_nv_gateway_timeout` on function `74f02205`
- 0 empty_200, 0 SSLEOF, 0 timeout, 0 429

### dsv4p_nv 成功路径
- 9 OK, avg 16,493ms
- 全部本地 key 成功

### glm5_2_nv zombie 详情
- 12 zombie_empty_completion, avg 14,223ms
- NVCF content-filter: finish_reason=stop, content_chars < 50, input > 5K
- Gateway detection 正确, 3-15s 内返回 502

### 30min 快照 (latest)
```
3req/1OK/2fail (33.3% SR)
```
- dsv4p_nv: 1 ATE (63653ms, 504_nv_gateway_timeout)
- glm5_2_nv: 1 OK (9348ms) + 1 zombie (5273ms)
- Peer-fb: 1 attempt, 72084ms → TimeoutError (HM2 不可达)

### Proxy 日志 (tail 200)
```
NV-GLM52-ATTEMPT x2: k4→k1 (pexec_us_rr), both 5-9s success
NV-ZOMBIE-EMPTY x2: glm5_2_nv, 48 chars < 50, 231K/232K input → abort
NV-CYCLE: dsv4p_nv k4 → 504_nv_gateway_timeout, k5 → 504_nv_gateway_timeout
NV-TIER-FAIL: both dsv4p_nv, 64s/63s, all 5 keys: other=1
NV-PEER-FB: 1st → 502 after 70s, 2nd → TimeoutError after 72s
```

### Peer-fallback 健康
- HM1→HM2: 2 recent attempts
  - 1st: 70,404ms → HM2 502 (HM2 也 NVCF degraded)
  - 2nd: 72,084ms → TimeoutError (HM2 不可达, 可能连接超时)
- HM2 peer-fb TO=25 (HM2 自己控制, 不修改)
- 双方同时 degraded → peer-fb 无益

### ms_gw
- 健康: `{"status":"ok"}`
- dsv4p_ms 不在 MODELMAP (R1609 移除, relay streaming sync defect)
- ms_gw 仅 glm5_2_ms, kimi_ms 在 MODELMAP

## 决策: NOP

**零参数, 零 compose 修改, 零容器重启。**

### 根因分析

| 失败数 | 错误类型 | 根因 | 可配置修复? |
|--------|---------|------|-----------|
| 11 | all_tiers_exhausted (dsv4p_nv) | NVCF 504 function-level degradation | ❌ NVCF 平台行为 |
| 12 | zombie_empty_completion (glm5_2_nv) | NVCF content-filter | ❌ NVCF 平台行为 |

**全部 23 个失败均为 NVCF 平台级别问题:**
- dsv4p_nv ATE: NVCF 504 function-level — 所有 5 keys 同时返回 504, function `74f02205` 持续 degraded
- glm5_2_nv zombie: NVCF content-filter stop+<50 chars, gateway detection 正确
- dsv4p_nv 9 个成功: 本地 key 成功, avg 16.5s
- Peer-fb 2 最近: 70.4s→HM2 502, 72.1s→TimeoutError — 双方同时 NVCF degraded

### 候选参数评估

| 候选 | 当前值 | 候选值 | 风险 | 收益 | 结论 |
|------|--------|--------|------|------|------|
| BUDGET_DSV4P_NV 66→60 | 66 | 60 | 504 非超时, 减 budget 无用; 60<UPSTREAM=66 违反 BUDGET≥UPSTREAM | 省 6s per ATE | ❌ 504 是 function-level, 非超时; 60<66 违反 BUDGET≥UPSTREAM |
| PEER_FALLBACK_TIMEOUT 72→66 | 72 | 66 | 66 < HM2_BUDGET(70)+2=72 → 违反 peer-fb 约束 | 省 6s per failed peer-fb | ❌ 违反 peer-fb≥PEER_BUDGET+2 ��束 |
| PEER_FB_SKIP_MODELS 加 dsv4p_nv | "" | "dsv4p_nv" | 丢失 peer-fb 救援 | 省 72s per failed peer-fb | ❌ peer-fb 在 HM2 健康时有价值 |
| MS_GW_FALLBACK 加 dsv4p_nv:dsv4p_ms | (无) | 加 dsv4p_nv:dsv4p_ms | dsv4p_ms relay streaming sync defect (R1609) | 可能给 ATE 额外恢复路径 | ❌ dsv4p_ms relay 100% fails (R1609) |
| UPSTREAM_TIMEOUT 66→60 | 66 | 60 | 504 不是超时, 减 UPSTREAM 无用; 可能误杀正常请求 | 无 | ❌ 非绑定 |
| NVU_SSLEOF_RETRY_DELAY 0.5→0.3 | 0.5 | 0.3 | 可能触发更频繁连接 | 省 0.2s per SSLEOF | ❌ 0 SSLEOF in 6h, 收益 ~0s |
| KEY_COOLDOWN_S 25→20 | 25 | 20 | 可能触发 429 | 更快 key 恢复 | ❌ 0 key_cycle_429s, 无 key cooldown 事件 |

**全部 rejected**: 所有参数已在 floor/optimal, 全部失败是 NVCF 平台级, 不可配置修复。

### 与 R1629/R1630 对比

| 轮次 | 决策 | 6h SR | dsv4p ATE | glm5_2 zombie | 理由 |
|------|------|-------|-----------|---------------|------|
| R1629 | NOP | (R1628 刚部署, 0 post-restart req) | 0 | 0 | 无数据, 等 bake |
| R1630 | NOP | 53.2% (47/25) | 10 | 12 | 全部 NVCF 平台级 |
| R1631 | NOP | 50.0% (46/23) | 11 | 12 | 与 R1630 一致, 全部 NVCF 平台级 |

- 连续三轮 NOP: NVCF function `74f02205` (dsv4p_nv) 持续 degraded, glm5_2_nv content-filter 持续触发
- 双方同时 degraded: peer-fb 2/2 失败 (1x 502, 1x TimeoutError)
- 等 NVCF 恢复后才有优化空间

## 铁律验证
- ✅ 只改HM1: 未修改任何配置
- ✅ 改前必有数据: 6h DB + docker logs + error log 分析
- ✅ 改后必有验证: 无需验证 (NOP)
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮文件 + git push
## ⏳ 轮到HM1优化HM2
