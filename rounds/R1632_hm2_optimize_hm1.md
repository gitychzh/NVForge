# R1632: HM2→HM1 — NOP (all params at floor, all failures NVCF platform-level, zero config-fixable errors. 4th consecutive NOP)

## 触发分析

- HM1 提交: `8000520` — R1627: HM2 nv_gw stream 全量缓冲到结束再 flush (方向C)
- 判定: 轮到HM2 — HM1 提交了 R1627, 需要评估
- R1627 是 HM2 本地 nv_gw 代码改动 (stream buffer), 不影响 HM1 配置

## 数据采集 (改前必有数据)

### HM1 环境 (container env, verified with docker exec)
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
| NVU_CONNECT_RESERVE_S | 0 | container env |

### Compose 验证 (值 ≠ 注释)
- `NVU_TIER_BUDGET_DSV4P_NV: "66"` (line 646) — 与 container env 匹配 ✓
- `NVU_PEER_FALLBACK_TIMEOUT: "72"` (line 513) — 与 container env 匹配 ✓

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
- 11 ATE, 全部 all_tiers_exhausted (NVCF 504 function-level)
- 全部 single tier, first key → 504_nv_gateway_timeout ~64s → BUDGET 剩余 ~2s < 5s minimum → break
- avg 65,633ms, max 72,030ms, min 63,594ms
- Error log: `504_nv_gateway_timeout` on function `74f02205-c7ba-438f-b81a-2537955bd7ec`
- 0 empty_200, 0 SSLEOF, 0 timeout, 0 429
- 全部 5 keys 同时 504 — function-level degradation, 非 key-level

### dsv4p_nv 成功路径
- 9 OK, avg 16,493ms
- 全部本地 key 成功 (NVCF function 健康时的一次性 key 成功)

### glm5_2_nv zombie 详情
- 12 zombie_empty_completion, avg 14,223ms
- NVCF content-filter: finish_reason=stop, content_chars < 50, input > 5K
- Gateway detection 正确: 3-15s 内 abort stream → 返回 502
- GLM5.2 RR 模式正常工作: 2-3 key 轮转, 5-9s per attempt

### Proxy 日志 (tail 500)
```
NV-GLM52-ATTEMPT x3: k5→k2→k3 (pexec_us_rr), ~10s each
NV-GLM52-ERR: k2 SSLEOFError → mode→advance k3
NV-ZOMBIE-EMPTY x2: glm5_2_nv, 48 chars < 50, 231K/232K input → abort stream
NV-CYCLE: dsv4p_nv k4 → 504_nv_gateway_timeout, k5 → 504_nv_gateway_timeout
NV-TIER-BUDGET: dsv4p_nv budget 66.0s remaining 1.9s/2.4s < 5s minimum → break
NV-TIER-FAIL: both dsv4p_nv, 64s/63s, all 5 keys: other=1 (504)
NV-THINKING-TIMEOUT: dsv4p_nv thinking extended → 66s
NV-PEER-FB: 1st → 502 after 70,404ms, 2nd → TimeoutError after 72,084ms
```

### Peer-fallback 健康
- HM1→HM2: 2 recent attempts
  - 1st: 70,404ms → HM2 returned 502 (HM2 also NVCF degraded)
  - 2nd: 72,084ms → TimeoutError (at PEER_FALLBACK_TIMEOUT=72 boundary, HM2 processing ≈70s + network ≈2s)
- Peer-fb constraint: HM1 PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET=70+2=72 ✓ (boundary satisfied)
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
- dsv4p_nv 9 个成功: 本地 key 成功 (NVCF function 健康时), avg 16.5s
- Peer-fb 2 最近: 70.4s→HM2 502, 72.1s→TimeoutError — 双方同时 NVCF degraded
- SSLEOF 1 次: glm5_2_nv RR 模式正确 advance, 不影响结果

### 候选参数评估

| 候选 | 当前值 | 候选值 | 风险 | 收益 | 结论 |
|------|--------|--------|------|------|------|
| BUDGET_DSV4P_NV 66→72 | 66 | 72 | 504 非超时, 增 budget 无用; 66=UPSTREAM 对齐; 每 ATE 浪费 6s | 无 | ❌ 504 是 function-level, 非超时; 单 key 已 64s 到 504, budget 够了 |
| PEER_FALLBACK_TIMEOUT 72→74 | 72 | 74 | 72=70+2 刚好满足约束; 74 浪费 2s per peer-fb | 窄边界, 可能减少 HM2 边界 TimeoutError | ❌ 边界 TimeoutError 是 HM2 也 degraded, 非配置问题; 72≥70+2 已满足 |
| PEER_FB_SKIP_MODELS 加 dsv4p_nv | "" | "dsv4p_nv" | 丢失 peer-fb 救援 | 省 72s per failed peer-fb | ❌ peer-fb 在 HM2 健康时有价值; 当前双方同时 degraded 是暂时 |
| UPSTREAM_TIMEOUT 66→60 | 66 | 60 | 504 不是超时, 减 UPSTREAM 无用; 可能误杀正常请求 | 无 | ❌ 非绑定 |
| NVU_SSLEOF_RETRY_DELAY 0.5→0.3 | 0.5 | 0.3 | 可能触发更频繁连接 | 省 0.2s per SSLEOF | ❌ 1 SSLEOF in 6h, 收益 ~0.2s |
| KEY_COOLDOWN_S 25→20 | 25 | 20 | 可能触发 429 | 更快 key 恢复 | ❌ 0 key_cycle_429s, 无 key cooldown 事件 |
| TIER_COOLDOWN_S 15→12 | 15 | 12 | 可能触发 tier 级 429 | 更快 tier 恢复 | ❌ 0 tier cooldown 事件, 收益 ~0s |

**全部 rejected**: 所有参数已在 floor/optimal, 全部失败是 NVCF 平台级, 不可配置修复。

### 与 R1629/R1630/R1631 对比

| 轮次 | 决策 | 6h SR | dsv4p ATE | glm5_2 zombie | 理由 |
|------|------|-------|-----------|---------------|------|
| R1629 | NOP | (R1628 刚部署, 0 post-restart req) | 0 | 0 | 无数据, 等 bake |
| R1630 | NOP | 53.2% (47/25) | 10 | 12 | 全部 NVCF 平台级 |
| R1631 | NOP | 50.0% (46/23) | 11 | 12 | 与 R1630 一致, 全部 NVCF 平台级 |
| R1632 | NOP | 50.0% (46/23) | 11 | 12 | 与 R1631 一致, 连续 4 轮 NOP |

- 连续四轮 NOP: NVCF function `74f02205` (dsv4p_nv) 持续 degraded, glm5_2_nv content-filter 持续触发
- 双方同时 degraded: peer-fb 2/2 失败 (1x 502, 1x TimeoutError)
- 等 NVCF 恢复后才有优化空间

## 铁律验证
- ✅ 只改HM1: 未修改任何配置
- ✅ 改前必有数据: 6h DB + docker logs + error log 分析
- ✅ 改后必有验证: 无需验证 (NOP)
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮文件 + git push
## ⏳ 轮到HM1优化HM2
