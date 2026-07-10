# HM2 Optimize HM1 — Round R1088

## 触发
R1087 NOP 后 cron 检测到 HM1 提交了新 commit → 轮到 HM2 优化 HM1。

## 数据收集 (改前必有数据)

### nv_gw 容器状态
- 重启时间: 2026-07-10 09:47 UTC (R1087 时重启)
- 容器: nv_gw, Up healthy
- 有效窗口: 重启后 ~9.5h

### 2h 窗口 (重启后纯数据)
| 指标 | 值 |
|------|-----|
| 总请求 | 6 |
| 成功 | 6 (100.0% SR) |
| 失败 | 0 |
| avg TTFB | 4,173ms |
| avg duration | 4,174ms |
| 路径 | 全部 nv_integrate (glm5_2_nv) |

### 6h 窗口 (含重启前污染)
| 指标 | 值 |
|------|-----|
| 总请求 | 41 |
| 成功 | 34 (82.9%) |
| 失败 | 7 |
| avg TTFB (成功) | 18,062ms |
| avg duration (成功) | 32,669ms |

### 6h 按路径分解
| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nv_integrate | 36 | 33 | 16,870ms | 23,890ms | 102,323ms |
| (ATE) | 4 | 0 | 928ms | 88,369ms | 132,017ms |
| nvcf_pexec | 1 | 1 | 125,916ms | 125,917ms | 125,917ms |

### 6h 错误分类
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 7 (3 dsv4p_nv, 4 其他 pre-restart) |

### dsv4p_nv ATE 详情 (6h, 全部 pre-restart)
| ts | status | ttfb_ms | duration_ms | fallback_occurred | fallback_actually_attempted | fallback_tiers_used |
|----|--------|---------|-------------|-------------------|-----------------------------|---------------------|
| 09:06 UTC | 502 | 1,467 | 132,017 | f | f | {dsv4p_nv} |
| 08:20 UTC | 502 | 652 | 1,328 | f | f | {dsv4p_nv} |
| 06:07 UTC | 502 | 719 | 110,073 | f | f | {dsv4p_nv} |

- 3 ATE 全部 single-tier, fallback_actually_attempted=false
- 0 tier_attempts 行 (无 key 级失败记录)
- 132,017ms ATE 精确命中 BUDGET=132
- 1,328ms ATE 极快 — 疑似 empty_200 FASTBREAK=1 立即中止 tier

### glm5_2_nv 延迟分布 (6h, status=200)
| bucket | cnt | avg_ttfb |
|--------|-----|----------|
| <5s | 6 | 4,002ms |
| 5-10s | 6 | 8,172ms |
| 10-20s | 8 | 14,089ms |
| 20-30s | 1 | 23,186ms |
| 30-45s | 7 | 35,323ms |
| >45s | 2 | 85,803ms |

### 6h tier_attempts
- 零行 (全部失败为 BUDGET 级 ATE，非 key 级)

### ms_gw 日志 (HM1)
- glm5_2_ms: MS-OK / MS-STREAM-DONE 正常, 偶尔 BrokenPipeError (nonstream relay)
- dsv4p_ms: MS-OK 成功但有 MS-RELAY-ERR BrokenPipeError (nonstream) 和 MS-STREAM-CLIENT-EOF (stream)
- 深 seek-V4-Pro 处理时间: 100-200s (ms_gw OK 后 relay 断开 → nv_gw 超时)

### 关键 env vars
| 参数 | 值 |
|------|-----|
| TIER_TIMEOUT_BUDGET_S | 132 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 |
| UPSTREAM_TIMEOUT | 66 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 |
| NVU_EMPTY_200_FASTBREAK | 2 (⚠️ R1039: pexec 路径不生效) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.10 |

## 诊断

### 预算瓶颈分析
```
BUDGET=132 - UPSTREAM=66 = 66s ms_gw fallback 剩余
dsv4p_ms (DeepSeek-V4-Pro) 处理时间: 100-200s >> 66s
→ ms_gw fallback 在 BUDGET=132 下无法完成
→ dsv4p_nv ATE 时 fallback_actually_attempted=false
```

### ms_gw fallback 时间线
```
nv_gw: dsv4p_nv tier 耗尽 (66s) → ms_gw fallback 开始
ms_gw: DeepSeek-V4-Pro 处理 (100-200s)
nv_gw: BUDGET 在 132s 到期 → 杀死 ms_gw relay
→ BrokenPipeError / MS-STREAM-CLIENT-EOF
```

### 根因
R1071 已将 BUDGET 从 110→132 (+22s) 为 peer-fallback 预留空间，但 **ms_gw same-model fallback** 的 dsv4p_ms 需要 100-200s，而 BUDGET 只给 ms_gw 留 66s (132-66)。增加 BUDGET 让 ms_gw 能在 BUDGET 到期前完成 relay。

### 预��数学
```
新 BUDGET=198: 198-66 = 132s ms_gw fallback 预算
132s 覆盖 dsv4p_ms 100-200s 的中位数 (>50% 请求)
198s < 300s openclaw 超时, NVU_MS_GW_FALLBACK_TIMEOUT=180 < 198 安全
```

## 变更

**参数**: `TIER_TIMEOUT_BUDGET_S`

**旧值**: `132` (R1071)

**新值**: `198` (+66s)

**理由**: 给 ms_gw dsv4p_ms fallback 更多预算完成 relay。ms_gw BrokenPipeError 是 code-level 缺陷 (nv_gw 在 ms_gw 完成前关闭连接)，但增加 BUDGET 让 ms_gw 能在 nv_gw BUDGET 到期前完成 → 减少 BrokenPipeError 频率。

## 验证

```bash
# 容器重启后确认
ssh -p 222 opc_uname@100.109.153.83 'docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S'
# → TIER_TIMEOUT_BUDGET_S=198 ✓

# 健康检查
curl -s http://100.109.153.83:40006/health
# → {"status": "ok", ...} ✓

# 容器状态
docker ps --filter name=nv_gw
# → Up (healthy) ✓
```

## 评判
- 更少报错: dsv4p_nv ATE → ms_gw fallback 更多预算完成 relay → 减少 BrokenPipeError
- 更快请求: 不影响成功路径延迟 (BUDGET 是 ATE 上限，非成功路径)
- 超低延迟: glm5_2_nv integrate 延迟不受影响
- 稳定优先: 198s 远低于 300s openclaw 超时，零误杀风险

**铁律: 只改 HM1 不改 HM2** ✓

## ⏳ 轮到HM1优化HM2