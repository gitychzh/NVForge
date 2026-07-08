# R930: HM2→HM1 NOP — 全参数地板, 61/61 100% SR 6h, 零错误

## 时间
2026-07-09 06:20 UTC

## 触发条件
HM1提交新commit (R929) 到 GitHub, 脚本检测到变更, 触发HM2优化HM1。

## 数据收集

### HM1 容器状态
- 容器 `nv_gw`: Up 2 hours (healthy)
- 容器 `logs_db`: Up 4 days (healthy)

### 6h 请求统计
| 指标 | 值 |
|------|-----|
| 总请求 | 61 |
| 成功 | 61 |
| 失败 | 0 |
| 成功率 | **100.0%** |

### 6h 按模型统计
| 模型 | 请求 | 成功 | 失败 | SR | avg_ms | p50_ms | p95_ms |
|------|------|------|------|-----|--------|--------|--------|
| dsv4p_nv | 5 | 5 | 0 | 100.0% | 26,603 | 23,667 | 51,643 |
| glm5_2_nv | 56 | 56 | 0 | 100.0% | 11,266 | 6,003 | 34,540 |

### 错误分类
- 零错误。无 `all_tiers_exhausted`, 无 `rate_limit`, 无 `timeout`。

### Fallback 统计
- `fallback_occurred=f`: 60
- `fallback_occurred=t`: 1 (成功回退)

### nv_tier_attempts (仅失败尝试)
- dsv4p_nv NVCFPexecTimeout: 1次 (k1, 52,849ms)
- dsv4p_nv empty_200: 1次
- 总计仅2条失败尝试记录

### tier_chain 状态
- glm5_2_nv: `['glm5_2_nv', 'dsv4p_nv']` (dynamic fallback, health={...}) ✅
- dsv4p_nv: `['kimi_nv', 'dsv4p_nv', 'glm5_2_nv']` (3-tier chain) ✅

### HM1 当前配置 (全参数)
```
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=3
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=45
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_PROXY_URL1= (空, DIRECT)
NVU_PROXY_URL2= (空, DIRECT)
NVU_PROXY_URL3= (空, DIRECT)
NVU_PROXY_URL4= (空, DIRECT)
NVU_PROXY_URL5= (空, DIRECT)
NVU_SSLEOF_RETRY_DELAY_S=1.0
TIER_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=114
UPSTREAM_TIMEOUT=64
```

## 分析
- 100% SR, 零错误, 所有参数已在地板位置
- 仅1次 fallback 成功触发, 1次 dsv4p_nv NVCFPexecTimeout (52,849ms) 在 UPSTREAM=64 范围内
- tier_chain 双向健康, 动态 fallback 正常
- **无任何可优化空间**

## 决策: NOP (零变更)
- 不修改任何 HM1 参数
- 系统已处于最优状态

## ⏳ 轮到HM1优化HM2