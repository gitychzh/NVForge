# HM2 Optimize HM1 — Round R936

## 0. 触发分析
cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)，R935: HM2→HM1 — NOP
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发，第53次连续 (R884→R936)
- HM1 本地 git log 停留在 R821，114 轮落后

## 1. 数据收集 (改前必有数据)

### 1.1 Docker 日志 (nv_gw, 最近100行)
所有日志均为 [NV-SUCCESS]，零错误，零警告，所有请求首次尝试成功。
- 请求模式: glm5_2_nv→glm5_2_nv stream=True，openclaw 调用
- 键轮转: k1→k2→k3→k4→k5 均匀分布，全部 DIRECT
- 耗时: 2-15s 区间，正常

### 1.2 容器 env (nv_gw)
```
UPSTREAM_TIMEOUT=64
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64
TIER_TIMEOUT_BUDGET_S=114
TIER_COOLDOWN_S=25
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=3
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
FALLBACK_HEALTH_THRESHOLD=0.05
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_PEER_FALLBACK_TIMEOUT=45
```
所有参数与 compose 一致，无 drift。

### 1.3 DB 统计 (nv_requests)

**6h 窗口 (07:25 UTC 回溯):**
| 指标 | 值 |
|------|-----|
| 总数 | 52 |
| 成功 | 52 (100%) |
| 失败 | 0 |
| 路径 | 全部 nvcf_pexec |
| 模型 | 全部 glm5_2_nv |
| avg_ttfb | 11523ms |
| avg_dur | 11529ms |
| max_dur | 120515ms (单次异常) |

**6h 错误分类:** 零错误 (0 rows)

**24h 错误分类:**
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 1 |

**6h fallback:**
| fallback_occurred | cnt |
|-------------------|-----|
| f | 51 |
| t | 1 |

**6h tier_attempts (仅失败):**
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| dsv4p_nv | NVCFPexecTimeout | 1 | 52849 | 52849 |
| dsv4p_nv | empty_200 | 1 | - | - |

### 1.4 ms_gw 检查
```
6h 请求: 0/0 (零流量)
EMPTY_200_FASTBREAK_THRESHOLD=3 (floor)
KEY_COOLDOWN_S=60
VARIANT_COOLDOWN_S=30
MIN_OUTBOUND_INTERVAL_S=1.0
UPSTREAM_TIMEOUT=300
```
ms_gw 参数已优化至 floor，零流量，无优化空间。

## 2. 分析

### 2.1 nv_gw 状态
- **100% 6h SR**，零错误，零 key_cycle_429s
- 所有请求均为 glm5_2_nv 首次尝试成功，openclaw 流量
- 24h 仅 1 次 ATE (NVCF 服务端 FALLBACK_GRAPH 瞬时消失，非配置可修)
- 1 次 fallback 触发 (dsv4p_nv NVCFPexecTimeout 52849ms + empty_200)
- 所有参数已至 floor，无下调空间，无上调需求

### 2.2 参数 floor 状态
| 参数 | 当前值 | Floor | 状态 |
|------|--------|-------|------|
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | AT FLOOR |
| NVU_CONNECT_RESERVE_S | 0 | 0 | AT FLOOR |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | AT FLOOR |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 1.0 | AT FLOOR |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 | AT FLOOR |
| NVU_EMPTY_200_FASTBREAK | 3 | 3 | AT FLOOR |
| KEY_COOLDOWN_S | 25 | 25 | AT FLOOR |
| TIER_COOLDOWN_S | 25 | 25 | AT FLOOR |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | 0.05 | AT FLOOR |
| UPSTREAM_TIMEOUT | 64 | - | 无绑定边缘 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | - | 与 UPSTREAM 同步 |
| TIER_TIMEOUT_BUDGET_S | 114 | - | 安全余量充足 |

### 2.3 决策
**NOP** — 所有可调参数已至 floor，零错误零 ATE，无优化攻击面。nv_gw 和 ms_gw 均无参数可动。

## 3. 执行
- 零参数修改
- 零 compose 编辑
- 零容器重启
- 铁律: 只改 HM1 不改 HM2 ✓

## ⏳ 轮到HM1优化HM2