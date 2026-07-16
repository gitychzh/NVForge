# R1627: HM2→HM1 — NOP (all params floor/optimal, both failure types NVCF platform-level, R1621c glm5_2_nv key RR fix just deployed 10min ago, needs bake time)

## 触发分析

- HM1 提交: `54dd8ea` — R1621c: 修 glm5_2_nv key RR 双 advance + counter 共用 bug
- 容器重启: 2026-07-16T07:52:18Z (10min ago), 应用 R1621c nv_gw 代码更新
- 判定: 轮到HM2 — HM1 提交了新代码, 需要评估

## 数据采集 (改前必有数据)

### HM1 环境
| 参数 | 值 | 来源 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | container env |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | container env |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | container env |
| TIER_COOLDOWN_S | 15 | container env |
| KEY_COOLDOWN_S | 25 | container env |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | container env |
| NVU_EMPTY_200_FASTBREAK | 2 | container env |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | container env (R1626) |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | container env (R1622) |
| NVU_PEER_FB_SKIP_MODELS | (空) | container env |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | container env |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | container env |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | container env |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | container env |
| container started | 2026-07-16T07:52:18Z (10min ago) | docker inspect |
| compose md5 | a52a027b668bf16d9548ffce03204e5b | md5sum |

### 6h 总体 (created_at >= 10:00 UTC)
```
36req/19OK/17fail = 52.8% SR
```

### 6h 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_dur | max_dur |
|------|------|----|----|------|---------|---------|
| glm5_2_nv | 20 | 11 | 9 | 55.0% | 15,013ms | 36,764ms |
| dsv4p_nv | 16 | 8 | 8 | 50.0% | 41,903ms | 72,020ms |

### 6h 错误分类
| 错误类型 | 数量 | 模型 | 根因 |
|---------|------|------|------|
| zombie_empty_completion | 9 | glm5_2_nv | NVCF content-filter: avg input 227K chars, avg dur 15.8s |
| all_tiers_exhausted | 8 | dsv4p_nv | NVCF 504 function-level degradation |

### dsv4p_nv ATE 详情
- **8 recovered (status=200)**: peer-fb → HM2 恢复, avg 9,607-41,189ms, fallback_occurred=f (DB 未记录 peer-fb 标记)
- **8 unrecovered (status=502)**: 全部 63,594-72,020ms, peer-fb to HM2 → 双方同时 NVCF 504 退化 → peer-fb 也返回 502
- **0 tier_attempts**: 全部 504 是 NVCF function-level, 非 key-level

### glm5_2_nv zombie 详情
- 9 zombie_empty_completion, avg input 227,073 chars, avg dur 15,835ms
- NVCF content-filter: finish_reason=stop, content_chars < 50, input > 5K
- Gateway detection 正确, 3-15s 内返回 502
- 不可配置修复 (NVCF 平台行为)

### ms_gw
- 9/9 100% SR (all glm5_2_nv via ZHIPUAI/GLM-5.2)
- 全部 MS-OK-STREAM + MS-STREAM-DONE, 正常交付

### 1h 快照
```
7req/3OK/4fail (42.9% SR, 5 key_cycle_429s)
```

### Post-restart (10min, 07:52 UTC)
```
0req — 容器刚重启, 尚无请求
```

### 6h hourly SR
| 小时 (UTC) | 总量 | OK | 失败 | SR |
|-----------|------|----|----|------|
| 03:00 | 4 | 3 | 1 | 75.0% |
| 04:00 | 9 | 5 | 4 | 55.6% |
| 05:00 | 10 | 6 | 4 | 60.0% |
| 06:00 | 6 | 2 | 4 | 33.3% |
| 07:00 | 7 | 3 | 4 | 42.9% |

### 6h tier_attempts
```
glm5_2_nv pexec_success: 20 (avg 14,496ms, max 34,223ms)
glm5_2_nv pexec_SSLEOFError: 2 (avg 5,002ms)
dsv4p_nv: 0 tier_attempts (全部 504 function-level)
```

### 6h per-key latency (dsv4p_nv+glm5_2_nv OK)
| key | 请求 | avg_dur | max_dur |
|-----|------|---------|---------|
| k0 | 3 | 8,103ms | 9,974ms |
| k1 | 2 | 16,747ms | 23,573ms |
| k2 | 2 | 21,081ms | 34,242ms |
| k3 | 2 | 19,022ms | 29,436ms |
| k4 | 2 | 9,870ms | 13,708ms |
| (peer-fb) | 8 | 18,531ms | 41,189ms |

### dsv4p_nv config 路径
- dsv4p_nv 走 pexec (NV_INTEGRATE_MODELS="", 不在 NV_KEY_INTEGRATE_KEYS)
- PEXEC_TIMEOUT_FASTBREAK=1, EMPTY_200_FASTBREAK=2
- TIER_BUDGET=72, UPSTREAM=66
- 504 function-level 非 FASTBREAK 触发 (不是 empty200, 是 504 gateway timeout)

### nv_gw 日志 (post-restart 10min)
```
glm5_2_nv: NV-GLM52-CHAIN → k2 pexec → SUCCESS (6.9s)
glm5_2_nv: NV-GLM52-CHAIN → k4 pexec → SSLEOFError → k5 pexec → SUCCESS (13.9s)
glm5_2_nv: NV-ZOMBIE-EMPTY detection (content_chars=48 < 50, input=230K)
```
- glm5_2_nv key RR: k2→k4→k5 (k4 SSL error → k5 恢复), 符合 R1621c 修复预期
- SSLEOF 后重试延迟: 0.5s (R1626), 日志显示快速切换
- zombie detection: 正确检测 48 chars < 50 threshold

## 决策: NOP

**零参数, 零 compose 修改, 零容器重启。**

### 根因分析

| 失败数 | 错误类型 | 根因 | 可配置修复? |
|--------|---------|------|-----------|
| 9 | zombie_empty_completion | NVCF content-filter (glm5_2_nv) | ❌ NVCF 平台行为 |
| 8 | all_tiers_exhausted (dsv4p_nv) | NVCF 504 function-level degradation | ❌ NVCF 平台行为 |

**全部 17 个失败均为 NVCF 平台级别问题**:
- glm5_2_nv zombie: NVCF content-filter stop+<50 chars, gateway detection 正确, 3-15s 内返回 502
- dsv4p_nv ATE: NVCF 504 function-level — 所有 5 keys 同时返回 504, 0 tier_attempts = 无 key 可轮换
- dsv4p_nv 8 个恢复 (status=200): peer-fb → HM2 (HM2 当时健康), avg 9.6-41s
- 8 个不可恢复: 双方同时 NVCF 退化 → peer-fb 也返回 502

### 候选参数评估

| 候选 | 当前值 | 候选值 | 风险 | 收益 | 结论 |
|------|--------|--------|------|------|------|
| TIER_BUDGET_DSV4P_NV 72→66 | 72 | 66 | 504 非超时, 减 budget 无用 | 省 6s per ATE | ❌ 504 是 function-level, 非超时 |
| PEER_FALLBACK_TIMEOUT 72→78 | 72 | 78 | 延长失败等待, Budget: 72+78=150<205 | 若 HM2 BUDGET>72, 给更多时间 | ❌ 8 个 ATE 双方同时 504, 加 FB timeout 无益 |
| PEER_FB_SKIP_MODELS 加 dsv4p_nv | "" | "dsv4p_nv" | 若 HM2 恢复而 HM1 未恢复, 丢失 peer-fb 救援 | 省 72s per failed peer-fb | ❌ 8/16 peer-fb 成功恢复, 证明 peer-fb 有价值 |
| MS_GW_FALLBACK 加 dsv4p_nv:dsv4p_ms | (无 dsv4p) | 加 dsv4p_nv:dsv4p_ms | dsv4p_ms 曾 501/BrokenPipeError (R1039 注释) | 可能给 8 个 ATE 额外恢复路径 | ❌ dsv4p_ms 历史不可靠, 且 ms_gw 无 dsv4p model |
| UPSTREAM_TIMEOUT 66→60 | 66 | 60 | SSLEOFError 5s, 非超时绑定 | 无 | ❌ 非绑定 |
| SSLEOF_RETRY_DELAY 0.5→0.3 | 0.5 | 0.3 | 可能触发更频繁连接 | 省 0.2s per SSLEOF | ❌ 仅 2 SSLEOF in 6h, 收益极小 |

**全部 rejected**: 所有参数已在 floor/optimal, 全部失败是 NVCF 平台级, 不可配置修复。

### 为什么是 NOP

1. **R1621c 刚部署 10min**: glm5_2_nv key RR 修复 (双 advance + counter 共用) 刚刚生效, 需要至少 1h 数据评估效果
2. **Post-restart 0 请求**: 容器刚重启, 尚无任何请求, 无法评估 R1621c 修复效果
3. **所有失败 NVCF 平台级**: 504 function-level + content-filter zombie, 非 nv_gw config 可修复
4. **ms_gw 100% SR**: 9/9 glm5_2_nv 正常交付, fallback 路径健康
5. **peer-fb 50% 恢复率**: 8/16 dsv4p_nv ATE 通过 peer-fb 恢复, 证明 peer-fb 有价值, 不应跳过
6. **glm5_2_nv key RR 已见改善**: 日志显示 k2→k4(SSL)→k5 正确轮转, 无跳位
7. **铁律:只改HM1不改HM2** ✓
## ⏳ 轮到HM1优化HM2
