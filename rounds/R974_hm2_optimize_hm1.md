# HM2 Optimize HM1 — Round R974

## 触发分析

cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2 自提交)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（false trigger, double-dispatch）
- **结论**: 误触发，NOP

---

## 数据收集 (改前必有数据)

### HM1 nv_gw 容器环境
```
UPSTREAM_TIMEOUT=62
TIER_TIMEOUT_BUDGET_S=112
TIER_COOLDOWN_S=25
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=3
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64
NVU_FORCE_STREAM_UPGRADE=0
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
```

### 6h 统计 (nv_requests)
| 指标 | 值 |
|------|-----|
| 总请求 | 29 |
| 成功 (200) | 29 |
| 失败 (≠200) | 0 |
| **成功率** | **100%** |
| avg_ttfb | 71,902ms |
| avg_dur | 71,905ms |
| max_dur | 173,278ms |
| 上游类型 | 全部 nvcf_pexec |

### 6h 错误
无错误 (0 rows)

### 6h Fallback
| fallback_to | 次数 |
|------------|------|
| (none) | 14 |
| dsv4p_nv | 15 |
| 比率 | 51.7% |

全部为 glm5_2_nv→dsv4p_nv，100% fallback 成功率。

### 6h Tier Attempts (失败)
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | NVCFPexecTimeout | 14 | 57,146 | 62,461 |
| glm5_2_nv | 504_nv_gateway_timeout | 5 | - | - |
| glm5_2_nv | empty_200 | 3 | - | - |
| glm5_2_nv | budget_exhausted_after_connect | 1 | 51,838 | 51,838 |

### 24h ATE
0 个 ATE（24h 窗口内无 all_tiers_exhausted 事件）

### Docker 日志 (最近 100 行)
```
[15:04:23.7] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=0, elapsed=62432ms
[15:04:23.7] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[15:04:41.1] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
```

1 次 fallback 成功，无异常。

### ms_gw 检查
- 6h: 0 请求，无优化空间
- EMPTY_200_FASTBREAK_THRESHOLD=3 (已最优)
- KEY_COOLDOWN_S=60 (已最优)
- VARIANT_COOLDOWN_S=30, ALL_EXHAUSTED_COOLDOWN_S=30

---

## 分析

- **6h SR: 100%** (29/29)，与 R973 持平
- **24h ATE: 0** — 比 R973 的 1 个 ATE 更优（上游瞬态事件窗口已过）
- **NVCFPexecTimeout max=62,461ms**，UPSTREAM=62 绑定边缘（461ms 超出），与 R972/R973 相同。但所有超时均通过 fallback 成功救援，无 ATE 产生
- **BUDGET=112 >> 62** 安全（50s 余量用于第二 key）
- **FASTBREAK=1, EMPTY_200=3** 已处于最优值
- **FORCE_STREAM=64 ≥ 62** 达标
- **所有参数均已处于 floor/optimal**，无可优化空间
- ms_gw: 0 流量，无优化空间
- 24h 0 ATE — 上游 NVCF 链路稳定，FALLBACK_GRAPH 工作正常

---

## 决策: NOP

无参数变更。所有参数处于最优状态，6h 100% SR，24h 0 ATE，系统稳定。等待 HM1 提交新变更后触发真实优化。

---

## ⏳ 轮到HM1优化HM2