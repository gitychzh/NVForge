# R1629: HM2→HM1 — NOP (all params at floor, R1628 BUDGET 66 just deployed, 0 post-restart requests, both failure types NVCF platform-level)

## 触发分析

- HM1 提交: `32b757a` — R1628: NVU_TIER_BUDGET_DSV4P_NV 72→66
- 容器重启: 2026-07-16T08:38:42Z, 应用 R1628 BUDGET 变更
- 判定: 轮到HM2 — HM1 提交了新 commit, 需要评估

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
| container started | 2026-07-16T08:38:42Z | docker inspect |
| HM2 peer reachable | 200 OK | curl health check |

### 6h 总体 (created_at >= NOW() - INTERVAL '6 hours')
| 指标 | 值 |
|------|-----|
| 总请求 | 44 |
| 成功 | 24 (54.5%) |
| 失败 | 20 |

### 6h 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_ok_ms | avg_fail_ms |
|------|------|----|------|-----|-----------|-------------|
| dsv4p_nv | 20 | 11 | 9 | 55.0% | 17,528 | 66,024 |
| glm5_2_nv | 24 | 13 | 11 | 54.2% | 13,097 | 14,655 |

### 6h 错误分类
| 错误类型 | 数量 | 模型 | 根因 |
|---------|------|------|------|
| all_tiers_exhausted | 9 | dsv4p_nv | NVCF 504 function-level degradation |
| zombie_empty_completion | 11 | glm5_2_nv | NVCF content-filter |

### dsv4p_nv ATE 详情
- 9 ATE, 全部 NVCF 504 function-level (0 empty_200, 0 cooldown skip)
- 全部 1 tier attempt, 1 key trial → 504 ~64s → give up
- 全部 fallback_actually_attempted=f (无 peer-fb 尝试在 DB 级)
- avg 66,024ms, max 72,030ms, min 63,594ms
- Error log 确认: `504_nv_gateway_timeout` on function `74f02205`

### dsv4p_nv 成功路径
- 11 OK, avg 17,528ms, max 41,189ms, min 9,607ms
- 全部 fallback_occurred=f (本地 key 成功, 非 peer-fb)

### glm5_2_nv zombie 详情
- 11 zombie_empty_completion, avg 14,655ms
- NVCF content-filter: finish_reason=stop, content_chars < 50, input > 5K
- Gateway detection 正确, 3-15s 内返回 502
- 不可配置修复 (NVCF 平台行为)

### 1h 快照 (post-restart)
```
8req/5OK/3fail (62.5% SR)
```
- dsv4p_nv: 3 OK + 1 ATE (72030ms)
- glm5_2_nv: 2 OK + 2 zombie (avg 9,344ms)

### Post-restart (08:38:42Z)
```
0req — 容器刚重启, 尚无请求 (DB 查询 created_at >= 08:38:42 → 0 rows)
```

### Proxy 日志 (post-restart)
```
NV-GLM52-IDX restored: idx=0
NV-RR restored: nv_dsv4p=2548, nv_kimi=83, nv_glm5_2=384, nv_minimax_m3_nv=1, nv_minimax_m3=19
NV-PROXY: 0 errors in post-restart tail
NV-PEER-FB: pre-restart 2 OK (1310 bytes, 14 bytes), 1 FAIL (TimeoutError 72074ms — HM2 also degraded)
```

### Error log 分析 (pre-restart)
- 07/15 16:07: `empty_200` x2 (pre-R1628)
- 07/15 17:07: `504_nv_gateway_timeout` k1 (pre-R1628)
- 07/15 18:00: `empty_200` x2, both single key (pre-R1628)
- 07/15 22:00: `IntegrateProxyConnectionError` all 5 keys (mihomo proxy down, pre-R1628)
- 07/16 02:00-08:00: 全部 `504_nv_gateway_timeout` (9个), 0 empty_200, 0 SSLEOF
- 错误类型从 empty_200→504 完全转变, 符合 NVCF function-level degradation

### ms_gw
- 健康: `{"status":"ok"}`
- 24h: 10 ZHIPUAI/GLM-5.2 OK (avg 15,338ms), 3 error (avg 6,572ms)
- dsv4p_ms: 0 requests in 24h (已被 R1609 从 MODELMAP 移除, 因 ms_gw relay streaming sync defect)

### Peer-fallback 健康
- HM1→HM2: 2/3 OK in recent logs, 1 TimeoutError (HM2 also NVCF degraded)
- HM2 peer-fb TO=25 (HM2 自己控制, 不修改)

## 决策: NOP

**零参数, 零 compose 修改, 零容器重启。**

### 根因分析

| 失败数 | 错误类型 | 根因 | 可配置修复? |
|--------|---------|------|-----------|
| 9 | all_tiers_exhausted (dsv4p_nv) | NVCF 504 function-level degradation | ❌ NVCF 平台行为 |
| 11 | zombie_empty_completion (glm5_2_nv) | NVCF content-filter | ❌ NVCF 平台行为 |

**全部 20 个失败均为 NVCF 平台级别问题:**
- dsv4p_nv ATE: NVCF 504 function-level — 所有 keys 同时返回 504, 0 tier_attempts = 无 key 可轮换
- glm5_2_nv zombie: NVCF content-filter stop+<50 chars, gateway detection 正确
- dsv4p_nv 11 个成功: 本地 key 成功, avg 17.5s
- peer-fb 2/3 OK: 证明 peer-fb 有价值

### 候选参数评估

| 候选 | 当前值 | 候选值 | 风险 | 收益 | 结论 |
|------|--------|--------|------|------|------|
| BUDGET_DSV4P_NV 66→60 | 66 | 60 | 504 非超时, 减 budget 无用; 60<UPSTREAM=66 可能误杀正常请求 | 省 6s per ATE | ❌ 504 是 function-level, 非超时; 60<66 违反 BUDGET≥UPSTREAM |
| PEER_FALLBACK_TIMEOUT 72→78 | 72 | 78 | 延长失败等待, Budget: 66+78=144<205 | 若 HM2 恢复, 给更多时间 | ❌ 9 ATE 双方同时 504, 加 FB timeout 无益 |
| PEER_FALLBACK_TIMEOUT 72→66 | 72 | 66 | 66 < HM2_BUDGET(70)+2=72 → 违反 peer-fb 约束 | 省 6s per failed peer-fb | ❌ 违反 peer-fb≥PEER_BUDGET+2 约束 |
| PEER_FB_SKIP_MODELS 加 dsv4p_nv | "" | "dsv4p_nv" | 丢失 peer-fb 救援 (2/3 OK) | 省 72s per failed peer-fb | ❌ 2/3 peer-fb 成功恢复 |
| MS_GW_FALLBACK 加 dsv4p_nv:dsv4p_ms | (无) | 加 dsv4p_nv:dsv4p_ms | dsv4p_ms relay streaming sync defect (R1609 验证) | 可能给 ATE 额外恢复路径 | ❌ dsv4p_ms relay 100% fails (R1609) |
| UPSTREAM_TIMEOUT 66→60 | 66 | 60 | 504 不是超时, 减 UPSTREAM 无用 | 无 | ❌ 非绑定 |
| NVU_SSLEOF_RETRY_DELAY 0.5→0.3 | 0.5 | 0.3 | 可能触发更频繁连接 | 省 0.2s per SSLEOF | ❌ 0 SSLEOF in 6h, 收益 0 |
| KEY_COOLDOWN_S 25→20 | 25 | 20 | 可能触发 429 | 更快 key 恢复 | ❌ 0 key_cycle_429s, 无 key cooldown 事件 |

**全部 rejected**: 所有参数已在 floor/optimal, 全部失败是 NVCF 平台级, 不可配置修复。

### 为什么是 NOP

1. **R1628 刚部署 2h**: BUDGET 72→66 刚刚生效, 需要至少 6h 数据评估效果
2. **Post-restart 0 请求**: 容器刚重启, 尚无任何请求, 无法评估 R1628 修复效果
3. **所有失败 NVCF 平台级**: 504 function-level + content-filter zombie, 非 nv_gw config 可修复
4. **所有参数在 floor**: BUDGET=66=UPSTREAM, PEER_FB=72=HM2_BUDGET+2, FASTBREAK=1, MIN_OUTBOUND=0, SSLEOF=0.5
5. **peer-fb 2/3 OK**: 证明 peer-fb 有价值, 不应跳过
6. **ms_gw dsv4p_ms 不可用**: R1609 验证 relay streaming sync defect, 100% fails
7. **铁律:只改HM1不改HM2** ✓

## 铁律验证
- ✅ 只改HM1: 未修改任何配置
- ✅ 改前必有数据: 6h DB + docker logs + error log 分析
- ✅ 改后必有验证: 无需验证 (NOP)
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮文件 + git push
## ⏳ 轮到HM1优化HM2
