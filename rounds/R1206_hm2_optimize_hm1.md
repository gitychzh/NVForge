# HM2 Optimize HM1 — Round R1206

## 触发分析

- **cron 脚本输出**: "这是我提交的, 不触发"
- **最新 commit author**: opc2_uname (HM2)
- **HM1 本地 git log**: R821 (384 轮落后)
- **判定**: 误触发 — HM2 自提交，HM1 未提交新内容

## 数据收集 (改前必有数据)

### 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 32 |
| 成功 (200) | 20 |
| 失败 | 12 |
| 成功率 | 62.5% |
| 容器重启 | 2026-07-10T19:03:27Z (16h+) |
| compose md5 | 7975939c245761e451a8813852dcb9bf (未变) |

### 按路径
| 路径 | 请求数 | 成功 | 失败 | avg_ttfb | avg_dur | max_dur |
|------|--------|------|------|----------|---------|---------|
| nv_integrate | 32 | 20 | 12 | 7216ms | 8415ms | 38540ms |

### 按模型
| 模型 | 请求数 | 成功 | 失败 | SR | avg_dur |
|------|--------|------|------|-----|---------|
| glm5_2_nv | 32 | 20 | 12 | 62.5% | 8415ms |

### 错误分类
| 错误类型 | 数量 |
|----------|------|
| zombie_empty_completion | 12 |

### 其他信号
- dsv4p_nv: 0 流量 (16h+)
- kimi_nv: 0 流量
- ms_gw: 0 流量 6h
- tier_attempts: 0 行
- fallback: 0 触发
- NV-MS-FB: 无

### 每小时 SR
| 小时 (UTC) | 总请求 | 成功 | 失败 | SR |
|------------|--------|------|------|-----|
| 05:00 | 4 | 2 | 2 | 50.0% |
| 06:00 | 4 | 2 | 2 | 50.0% |
| 07:00 | 4 | 2 | 2 | 50.0% |
| 08:00 | 4 | 2 | 2 | 50.0% |
| 09:00 | 11 | 9 | 2 | 81.8% |
| 10:00 | 5 | 3 | 2 | 60.0% |

### 僵尸详情
- 全部 zombie_empty_completion: glm5_2_nv integrate
- NVCF content-filter stop+12-36chars
- input_chars: 104K-177K (平均 ~157K)
- Gateway 检测 + error-chunk 正确
- 3-15s 快速 abort (非旧版 96s 超时)

### 当前参数 (HM1 nv_gw env)
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=198
- TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=72
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_MS_GW_FALLBACK_TIMEOUT=180
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- NVU_FORCE_STREAM_UPGRADE=0
- MIN_OUTBOUND_INTERVAL_S=0
- NVU_CONNECT_RESERVE_S=0
- NV_INTEGRATE_KEY_COOLDOWN_S=0

## 决策

**NOP — Zero param.**

理由:
1. 误触发 — HM2 自提交，HM1 未提交新内容
2. 数据与 R1205 完全一致 (32/20/12 zombie)
3. 所有失败 = zombie_empty_completion (NVCF content-filter，代码级特性，非 config 可修复)
4. 0 tier_attempts, 0 fallback, 0 ms_gw 流量
5. 所有参数已在地板/最优值
6. dsv4p_nv/kimi_nv 0 流量 16h+
7. compose md5 未变 48h+
8. 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2

