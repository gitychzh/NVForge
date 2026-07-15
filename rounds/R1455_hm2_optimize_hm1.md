# HM2 Optimize HM1 — Round R1455

## 触发分析

cron 脚本输出: "这是我提交的, 不触发" ← FALSE TRIGGER
- 最新 commit author = opc2_uname (HM2)
- HM1 未提交新内容，R1454 为 HM2 NOP 轮
- 此轮为 double-dispatch 继续链（R1395 链的第 61 轮）

## 数据 (改前必有数据)

### 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 35 |
| 成功 | 14 (40.0%) |
| 失败 | 21 (60.0%) |

### 错误分类
| 错误类型 | 数量 | 模型 |
|----------|------|------|
| all_tiers_exhausted | 11 | 10 dsv4p_nv + 1 glm5_2_nv |
| zombie_empty_completion | 10 | glm5_2_nv (NVCF content-filter) |

### 模型维度
| 模型 | 请求 | 成功 | SR% | 平均延迟 |
|------|------|------|-----|----------|
| glm5_2_nv | 25 | 14 | 56.0% | 18.6s |
| dsv4p_nv | 10 | 0 | 0.0% | 82.1s |

### 路径维度
| 路径 | 请求 | 成功 | 失败 |
|------|------|------|------|
| nv_integrate | 24 | 14 | 10 |
| (NULL/pexec) | 11 | 0 | 11 |

### ms_gw
- 25/21 84.0% SR
- dsv4p_ms fallback relay: TimeoutError 284s (code-level streaming sync defect)

### 其他
- tier_attempts: 0
- fallback: 0
- IncompleteRead: 0
- key_cycle_429s: 0

## 容器状态
- 重启时间: 2026-07-15T10:49:16Z (~1h 前)
- 状态: Up About an hour (healthy)
- Compose md5: 51079b89019ddfb1a08f65e79e847b51

## 当前参数 (all floor/optimal)
- UPSTREAM_TIMEOUT=66
- TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_FORCE_STREAM_UPGRADE=0
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_TIER_BUDGET_DSV4P_NV=66
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- NVU_PEER_FALLBACK_ENABLED=1
- NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS=""
- NV_INTEGRATE_KEY_COOLDOWN_S=0

## 判定

**NOP** — 所有参数已在地板/最优值，无配置空间可优化。
- zombie=10 (NVCF content-filter，非配置可修复)
- ATE=11 (dsv4p_nv NVCF 504，ms_gw relay TimeoutError 284s 为代码级缺陷)
- 0 tier_attempts, 0 key_cycle_429s, 0 IncompleteRead
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
