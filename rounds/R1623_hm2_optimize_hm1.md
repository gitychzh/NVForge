# R1623: HM2→HM1 — NOP (false trigger, double-dispatch of R1622, PEER_FALLBACK_TIMEOUT=72 just deployed 14min ago, both hosts NVCF 504 degradation, zombie NVCF content-filter)

## 触发分析

- cron 脚本输出: `"已处理过此commit(918db6c93d43a49e0e0485574839225e1117b94c), 等待新提交"`
- 最新 commit = R1622 (918db6c), author=opc2_uname (HM2)
- 判定: **FALSE TRIGGER** — double-dispatch of R1622
- HM1 未提交任何新 commit
- R1622 的 PEER_FALLBACK_TIMEOUT=72 刚部署 14min 前

## 数据采集 (改前必有数据)

### HM1 环境
| 参数 | 值 | 来源 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | container env |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | container env |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | container env |
| TIER_TIMEOUT_BUDGET_S | 205 | container env |
| TIER_COOLDOWN_S | 15 | container env |
| KEY_COOLDOWN_S | 25 | container env |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | container env |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | container env |
| NVU_EMPTY_200_FASTBREAK | 2 | container env |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | container env (R1622) |
| NVU_PEER_FB_SKIP_MODELS | (空) | container env |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms | container env (R1609, no dsv4p_nv) |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | container env |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | container env |
| container started | 2026-07-16T06:23:10Z (14min ago) | docker inspect |
| compose md5 | 9a8691d63bb2cb8126776b6bb510d3d6 | md5sum |

### 6h 总体 (created_at >= 14:36 CST)
```
28req/16OK/12fail = 57.1% SR
```

### 6h 按模型
| 模型 | 请求 | OK | 失败 | SR | avg_dur | max_dur |
|------|------|----|----|------|---------|---------|
| glm5_2_nv | 15 | 8 | 7 | 53.3% | 15,365ms | 36,764ms |
| dsv4p_nv | 13 | 8 | 5 | 61.5% | 35,977ms | 64,259ms |

### 6h 错误分类
| 错误类型 | 数量 | 模型 |
|---------|------|------|
| zombie_empty_completion | 7 | glm5_2_nv (NVCF content-filter, avg input ~227K chars, avg dur 15.8s) |
| all_tiers_exhausted | 5 | dsv4p_nv (NVCF 504 function-level degradation) |

### dsv4p_nv ATE 详情
- **8 recovered (status=200)**: 全部 pre-restart, avg 9607-41189ms, fallback_occurred=false, upstream_type=NULL
  - 恢复路径: peer-fb → HM2 (HM2当时健康, dsv4p_nv function正常)
- **5 unrecovered (status=502)**: 4 pre-restart (63,594-64,259ms) + 1 post-restart (66,073ms)
  - 失败原因: NVCF 504 function-level → 本地5 keys全部504 → peer-fb to HM2 → HM2也返回502
  - Post-restart peer-fb: 70394ms → HM2 returned 502
- **0 tier_attempts**: 全部504是NVCF function-level (非key-level), 无key可轮换

### glm5_2_nv zombie 详情
- 7 zombie_empty_completion, avg input 226,524 chars, avg dur 15,779ms
- NVCF content-filter: finish_reason=stop, content_chars=14 (<50 threshold), input > 5K
- Gateway detection+error-chunk correct → zombie 在 3-15s 内返回 502
- 不可配置修复 (NVCF平台行为)

### ms_gw
- 7/7 100% SR (all glm5_2_nv via ZHIPUAI/GLM-5.2)
- dsv4p_ms 不在 MODELMAP (R1609), 无 dsv4p_ms relay
- ms_gw 日志: 全部 MS-OK-STREAM + MS-STREAM-DONE, 正常交付

### 1h 快照
```
6req/2OK/4fail (1h window, post-restart 14min: 2req/1OK/1fail)
```

### Post-restart (14min)
```
2req: 1 OK (glm5_2_nv, 34s) + 1 peer-fb→502 (dsv4p_nv, 70394ms)
1 peer-fb attempt: HM2 returned 502 after 70394ms
```

### 6h tier_attempts
```
glm5_2_nv pexec_success: 15 (avg 14,681ms)
glm5_2_nv pexec_SSLEOFError: 2 (avg 5,002ms, SSLEOF cycle)
dsv4p_nv: 0 tier_attempts (全部504是function-level, 非key-level)
```

### 6h hourly SR
| 小时 (UTC) | 总量 | OK | 失败 | SR |
|-----------|------|----|----|------|
| 03:00 | 4 | 3 | 1 | 75.0% |
| 04:00 | 9 | 5 | 4 | 55.6% |
| 05:00 | 10 | 6 | 4 | 60.0% |
| 06:00 | 5 | 2 | 3 | 40.0% |

### nv_gw 日志
- glm5_2_nv: SSLEOFError → mode advance → key cycle (正常恢复)
- glm5_2_nv: NV-ZOMBIE-EMPTY detection correct (content-filter stop+14 chars, input 227K)
- dsv4p_nv: SSLEOFError → key cycle (正常)
- dsv4p_nv: NV-PEER-FB → HM2 returned 502 after 70394ms

## 决策: NOP

**零参数, 零 compose 修改, 零容器重启。**

### 根因分析

| 失败数 | 错误类型 | 根因 | 可配置修复? |
|--------|---------|------|-----------|
| 7 | zombie_empty_completion | NVCF content-filter (glm5_2_nv) | ❌ NVCF平台行为 |
| 5 | all_tiers_exhausted (dsv4p_nv) | NVCF 504 function-level degradation | ❌ NVCF平台行为 |

**全部12个失败均为NVCF平台级别问题**:
- glm5_2_nv zombie: NVCF content-filter stop+14 chars, gateway detection正确, 3-15s内返回502
- dsv4p_nv ATE: NVCF 504 function-level — 所有5个keys同时返回504, 0 tier_attempts = 无key可轮换
- dsv4p_nv 8个恢复 (status=200): peer-fb → HM2 (HM2当时健康), avg 9.6-41s
- 5个不可恢复: 双方同时NVCF退化 → peer-fb也返回502

### 候选参数评估

| 候选 | 当前值 | 候选值 | 风险 | 收益 | 结论 |
|------|--------|--------|------|------|------|
| PEER_FB_SKIP_MODELS 加 dsv4p_nv | "" | "dsv4p_nv" | 若HM2恢复而HM1未恢复, 丢失peer-fb救援 | 省72s per failed peer-fb | ❌ 1数据点不足以决策 |
| PEER_FALLBACK_TIMEOUT 72→78 | 72 | 78 | 延长失败等待, 增加总延迟 | 若HM2 BUDGET>72, 给更多时间 | ❌ HM2 BUDGET=70, 72已足够 |
| TIER_BUDGET_DSV4P_NV 66→60 | 66 | 60 | 可能制造新失败 | 省6s per tier | ❌ 504非超时, 减budget无用 |
| UPSTREAM_TIMEOUT 66→60 | 66 | 60 | SSLEOFError 5s, 非超时绑定 | 无 | ❌ 非绑定 |

**全部 rejected**: 所有参数已在floor/optimal, 全部失败是NVCF平台级, 不可配置修复。

### 为什么是NOP

1. **False trigger**: R1622刚部署14min, PEER_FALLBACK_TIMEOUT=72刚生效, 数据不足评估
2. **Post-restart仅2请求**: 1 OK + 1 peer-fb→502, 不足以判断peer-fb skip策略
3. **所有失败NVCF平台级**: 504 function-level + content-filter zombie, 非nv_gw config可修复
4. **ms_gw 100% SR**: 7/7 glm5_2_nv正常交付, fallback路径健康
5. **8/13 dsv4p_nv恢复**: peer-fb to HM2在HM2健康时有效 (pre-restart), 证明peer-fb有价值
6. **铁律:只改HM1不改HM2** ✓
## ⏳ 轮到HM1优化HM2
