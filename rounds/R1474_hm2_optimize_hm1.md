# HM2 → HM1 优化轮次 R1474

## 触发分析
- **cron脚本输出**: "这是我提交的, 不触发"
- **判定**: 假触发 (false trigger, HM1 提交的是自己的 commit, 非 HM2 的优化)
- **最新 commit**: 6f4931d (R1473, author=opc2_uname, HM2)
- **行动**: 收集数据 → 发现优化空间 → 执行优化

## 6h 数据 (nv_gw)
| 指标 | 值 |
|------|-----|
| 总请求 | 40 |
| 成功 (200) | 16 |
| 失败 (502) | 24 |
| SR | 40.0% |

### 失败分类
| 错误类型 | 数量 | 模型 | 平均延迟(ms) | 可配置修复? |
|----------|------|------|-------------|-------------|
| zombie_empty_completion | 14 | glm5_2_nv(11) + dsv4p_nv(3) | 14393/49159 | ❌ NVCF content-filter |
| all_tiers_exhausted | 10 | dsv4p_nv(9) + glm5_2_nv(1) | 63932/187171 | ⚠️ 部分可修 |

### nv_gw 日志关键信号
- 2 NV-CYCLE (dsv4p_nv k3/k4 → 504_nv_gateway_timeout, k1 fail)
- ABORT-NO-FALLBACK (dsv4p_nv, 63-64s)
- NV-MS-FB → ms_gw relay TimeoutError at ~124s (relay_started=True) — **6/6 全部 TimeoutError**
- 0 peer-fb 日志 (peer_fallback enabled but code path never reached — ms_gw `elif` blocks it)
- 0 NV-PEER-FB 日志
- 0 tier_attempts (干净 key 池)

## ms_gw 6h
| 指标 | 值 |
|------|-----|
| 总请求 | 26 |
| 成功 | 19 |
| 失败 | 7 |
| SR | 73.1% |

### ms_gw 失败分析
- 7 errors, null error_message (ModelScope 上游 variant exhaustion)
- 日志显示 dsv4p_ms 所有 10 variants 全部 exhausted (0cbcfcbb)
- ms_gw 健康: ok, rr_counters: glm5_2=200, dsv4p=44

## 🔍 关键发现: ms_gw dsv4p_ms 100% 失败率 → 阻塞 peer-fb

### 证据链
1. dsv4p_nv ATE (504_nv_gateway_timeout) → ABORT-NO-FALLBACK
2. ms_gw dsv4p_ms fallback 触发: 6/6 TimeoutError (~124s, relay_started=True)
3. peer-fallback 代码路径: `elif` 在 ms_gw 之后 → **ms_gw 失败后不 fallthrough 到 peer-fb**
4. 结果: dsv4p_nv ATE 被 ms_gw 消耗 120s (FALLBACK_TIMEOUT) 后仍然 502，peer-fb 从未触发

### 代码路径 (handlers.py L345-382)
```python
if (NVU_MS_GW_FALLBACK_ENABLED and ...
        and mapped_model in NVU_MS_GW_FALLBACK_MODELMAP):  # dsv4p_nv in MODELMAP
    ...  # ms_gw fallback → 6/6 TimeoutError → FAILED
elif (NVU_PEER_FALLBACK_ENABLED and ...
        and mapped_model not in _peer_skip):  # NEVER REACHED for dsv4p_nv
    ...  # peer-fb unreachable
```

dsv4p_nv 在 MODELMAP 中 → ms_gw 先尝试 → 100% 失败 → 消耗 120s → 回 502，peer-fb 永远不触发。

## 优化: 移除 dsv4p_nv 从 MS_GW_FALLBACK_MODELMAP

| 参数 | 旧值 | 新值 |
|------|------|------|
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms |

### 变更理由
- **ms_gw dsv4p_ms 6/6 TimeoutError** — 所有 10 variants 耗尽，100% 失败率
- **ms_gw fallback 消耗 120s** (FALLBACK_TIMEOUT)，peer-fb 无机会执行
- **移除 dsv4p_nv 后**: dsv4p_nv ATE → `elif` 直接进入 peer-fb → HM2 独立 key 池救援
- **预期效果**: dsv4p_nv ATE 救援时间从 ~185s (66s tier + 120s ms_gw) 降至 ~66s tier + peer-fb 最多 66s = ~132s
- **glm5_2_nv/kimi_nv**: 保留在 MODELMAP 中（ms_gw glm5_2_ms 仍有 73.1% SR，有用）

### 参数状态
- **compose md5**: 变更 (NVU_MS_GW_FALLBACK_MODELMAP 修改)
- **tier_attempts**: 0 (干净 key 池)
- **所有 nv_gw 参数**: 地板/最优
- **所有 FASTBREAK 参数**: 已到最优值
- **TIER_BUDGET_DSV4P_NV=66**: 已到 UPSTREAM_TIMEOUT 地板
- **PEER_FB_SKIP_MODELS**: 空 (peer-fb 已启用)
- **zombie 14**: NVCF content-filter — 不可配置修复

## 部署验证
- ✅ YAML 语法检查通过
- ✅ docker compose up -d nv_gw 成功
- ✅ 容器内 env 确认: `NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms`
- ✅ /health 返回 ok
- ✅ 单参数修改，铁律: 只改 HM1 不改 HM2

## 决策
**OPTIMIZE** — 移除 dsv4p_nv 从 ms_gw MODELMAP。ms_gw dsv4p_ms 100% 失败率且阻塞 peer-fb 代码路径。移除后 dsv4p_nv ATE 直接进入 peer-fb (HM2 独立 key 池)，预期节省 ~120s/ATE。zombie 14 不可修复。单参数，少改多轮。

## ⏳ 轮到HM1优化HM2
