# R2080 — hermes2 R24 巡检轮: NVCF 502 暴增, SR 崩溃至 26.2%

- 日期: 2026-07-20
- agent: hermes2 (HM2, opc2_uname)
- 链路: dsv4p_nv (40006 nv_gw)
- 决策: 巡检轮 (不改代码)
- 仓库: NVForge, commit pending

## 数据快照 (30min 窗口)

### nv_requests (dsv4p_nv, mapped_model)
```
status   | count
-------- | -----
502      | 72
200      | 27
429      | 4
总计: 103
SR = 27/103 = 26.2%
```

### 与前轮对比
| 指标 | R23 | R24 | 变化 |
|------|-----|-----|------|
| 502 | 13 | 72 | **+454%** ⚠️⚠️⚠️ |
| 成功(200) | 17 | 27 | +58.8% |
| 429 | 2 | 4 | +100% |
| Tier 429 | 43 | 36 | -16.3% |
| SR | 53.1% | 26.2% | **-26.9pp** ⚠️⚠️ |
| all_tiers_exhausted | 15 | 72 | +380% |
| fallback (hm4104) | 184 | 165 | -10.3% |
| PRIMARY-FAIL-STREAM | 13 | 13 | 持平 |
| FALLBACK-FAIL-STREAM | - | 9 | - |

### Tier 层 (nv_tier_attempts)
- 429_nv_rate_limit: 36 (R23: 43, -16.3%)
- pexec_success: 33
- NVCFPexecTimeout: 1
- pexec_SSLEOFError: 1

### 429 按 key
| key | R23 | R24 | 变化 |
|-----|-----|-----|------|
| k0 | 8 | 5 | -37.5% |
| k1 | 12 | 9 | -25% |
| k2 | 11 | 13 | +18.2% |
| k3 | 7 | 9 | +28.6% |
| k4 | 3 | 0 | -100% |

### 502 错误分类
- all_tiers_exhausted: 68 (94.4% of 502)
- zombie_empty_completion: 3
- stream_first_byte_timeout: 1
- error_subcategory 明细: 57 (空), 15 (all_tiers_failed_in_mapped_tier)

### PRIMARY-FAIL-STREAM 模式
- 502 after 63s (流式慢 502)
- 502 after 7-11ms (快速 502, NVCF 直接拒绝)
- 429 after 500ms

### fallback 明细 (hm4104)
- FALLBACK-STREAM: 持续 (breaker OPEN 下正常)
- PRIMARY-BREAKER-SKIP-STREAM: 持续
- FALLBACK-FAIL-STREAM: ms_gw 流式 timeout after 30s = 兜底也有压力

## 核心判断

**NVCF 上游服务 502 暴增, SR 崩溃至 26.2% ⚠️⚠️⚠️**

- 429 从 43 降至 36 (-16.3%), 限流在缓解 —— 好消息
- 但 502 从 13 暴增至 72 (+454%), SR 从 53.1% 崩溃至 26.2% (-26.9pp)
- 502 模式: 瞬时拒绝(7-9ms)占比高 = NVCF 上游直接返回 502, 不是超时
- 多数请求先被 429 踢了几把 key, 最后一把 key 返回 502 → all_tiers_exhausted
- **按 R24 判断标准: 502 > 10 且 SR < 50% → 触发"NVCF 上游服务不稳定"⚠️**
- 这是第一轮触发, 按交接棒规则: 连续 2 轮 → 联系 NVCF 侧

### 为什么不用 R24 以前的对比 (502=13)

R23 502=13, R21/R22 502=11/2。但那些轮 Tier 429 在 26-48, 限流主导。R24 限流在缓解 (36), 但 502 取而代之成为主要失败源。不像是 R20/R21 同样的模式 —— 现在是 NVCF 上游服务故障 (瞬时 502) 而不是单纯限流。

## R24 决策: 巡检轮, 不改代码

按 R24 判断标准:
- Tier 429 = **36** → 在 30-49 范围 (限流反弹持续, 但有回落迹象)
- SR = **26.2% < 50%** 且 502 = **72 > 10** → 触发"NVCF 上游服务不稳定"
- 第一轮触发, 不改代码, 下一轮若仍在→联系 NVCF 侧
- breaker OPEN → 不重启 (重启不治 502)

### 验证
- `curl /health` OK
- `docker ps`: nv_gw Up 2h / hm4104 Up 5h / ms_gw Up 3d

## 下一步 (R25): 观察 502 是否回落

- 若 502 < 10 且 SR > 50%: 巡检轮, 标注"502回落, 恢复中"
- 若 502 仍在 > 10 且 SR < 50%: **连续 2 轮触发, 联系 NVCF 侧**
- 若 429 继续下降 < 20: 限流消退中, 但 502 问题更紧迫
- breaker OPEN 持续 → 不重启, 除非 502 清零后再考虑

## 不要做的事

- **不要重启 nv_gw**: 502 是 NVCF 上游故障, 重启无效
- **不要改 KEY_COOLDOWN_S**: 与 502 无关
- **不要改 TIER 配置**: 502 不是 tier routing 问题