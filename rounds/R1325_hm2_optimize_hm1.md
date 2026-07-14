# HM2 Optimize HM1 — Round R1325

## 触发分析

cron 脚本输出: `这是我提交的, 不触发`
- 最新 GitHub commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, 39th consecutive post-R1286)
- HM1 本地 git log 停留在 R1206 (119 轮落后)

## 数据收集 (改前必有数据)

### 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 54 |
| 成功 (200) | 47 |
| 失败 (502) | 7 |
| 成功率 | 87.0% |
| 模型分布 | glm5_2_nv 54/54 (100%) |
| 路径分布 | nv_integrate 54/54 (100%) |
| fallback 触发 | 0/54 |
| tier_attempts | 0 |
| ATE | 0 |
| IncompleteRead | 0 |

### 错误分类
| 错误类型 | 数量 | 可修复 |
|---------|------|--------|
| zombie_empty_completion | 7 | ❌ 代码级 (NVCF content-filter stop) |

### Zombie 详情
| 模型 | 数量 | avg input_chars | avg duration_ms | avg output_tokens |
|------|------|-----------------|-----------------|-------------------|
| glm5_2_nv | 7 | 190,653 | 6,085 | 15 |

### 每小时 SR
| 小时 | 总量 | OK | 失败 | SR |
|------|------|-----|------|-----|
| 23:00 | 3 | 2 | 1 | 66.7% |
| 00:00 | 6 | 5 | 1 | 83.3% |
| 01:00 | 29 | 28 | 1 | 96.6% |
| 02:00 | 5 | 5 | 0 | 100.0% |
| 03:00 | 5 | 3 | 2 | 60.0% |
| 04:00 | 4 | 3 | 1 | 75.0% |
| 05:00 | 2 | 1 | 1 | 50.0% |

### ms_gw 信号
| 总请求 | 成功 | SR |
|--------|------|-----|
| 13 | 13 | 100% |

### 容器状态
- nv_gw: Up 7 hours (healthy), started 2026-07-13T22:14:51Z
- Compose md5: 6e1b58bc70eca49e500e3034b08376d9 (stable, unchanged from R1323-R1324)
- NVU_PEER_FB_SKIP_MODELS: empty

### 参数状态
所有参数处于 floor/optimal:
- UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- TIER_TIMEOUT_BUDGET_S=205
- MIN_OUTBOUND_INTERVAL_S=0
- NVU_SSLEOF_RETRY_DELAY_S=1.0

## 决策: NOP

### 原因
1. **数据与 R1324 高度一致**: 54req/47OK/87.0%SR (R1324: 55req/49OK/89.1%), 7 zombie (R1324: 6), 0 tier_attempts, 0 ATE, 0 fallback, ms_gw 13/13
2. **zombie_empty_completion 不可配置修复**: 所有 7 个失败均为 glm5_2_nv integrate NVCF content-filter stop (input_chars ~191K avg, output 15 tokens avg, finish_reason=stop). 网关检测 (NV-ZOMBIE-EMPTY) + error-chunk (NV-ZOMBIE-ERROR-CHUNK) 正确执行。这是 NVCF 侧行为，非配置参数可控。
3. **所有参数已处于 floor/optimal**: 无调整空间
4. **ms_gw 100% SR**: 备用链路健康
5. **Compose md5 稳定**: 6e1b58bc 未变 (R1323 baseline)
6. **HM1 未提交任何新内容**: git log 停留在 R1206 (119 轮落后)

### 变更
- **零参数变更** — 不修改任何配置
- **零 compose 编辑** — 不修改 docker-compose.yml
- **零容器重启** — 不重启 nv_gw

## 铁律: 只改HM1不改HM2
本次回合未修改任何配置，铁律自然满足。

## ⏳ 轮到HM1优化HM2
