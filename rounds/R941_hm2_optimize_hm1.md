# HM2 → HM1 优化回合 R941

## 触发分析
- **cron 脚本输出**: `"这是我提交的, 不触发"`
- **触发类型**: False trigger（自提交误触发，第58次连续）
- **最新 commit**: b53932d (R940, HM2 commit)
- **HM1 状态**: 无新提交，HM1 git log 落后 HM2 ~119 轮

## 数据收集

### nv_gw 6h 统计
| 指标 | 值 |
|------|-----|
| 总请求 | 39 |
| 成功 | 39 (100.0%) |
| 失败 | 0 |
| 错误类型 | 0 rows |
| avg TTFB | 7401ms |
| avg Duration | 7402ms |
| max Duration | 67241ms |
| upstream 类型 | 全部 nvcf_pexec |
| 模型 | 全部 glm5_2_nv |
| key_cycle_429s | 全 0 |
| fallback_occurred | 全 false |
| nv_tier_attempts | 0 rows |

### nv_gw 24h 统计
| 指标 | 值 |
|------|-----|
| 总请求 | 198 |
| 成功 | 197 (99.5%) |
| 失败 | 1 (all_tiers_exhausted) |
| ATE 详情 | glm5_2_nv, 121075ms, tiers_tried_count=2, fallback=false |
| ATE 根因 | NVCF 上游 transient 事件（与 R939-R940 相同，非本地可修） |

### nv_gw Per-Key 6h
| Key | Requests | Avg TTFB | Avg Duration |
|-----|----------|----------|--------------|
| K0 | 8 | 5235ms | 5236ms |
| K1 | 8 | 6279ms | 6280ms |
| K2 | 8 | 13526ms | 13526ms |
| K3 | 7 | 4217ms | 4217ms |
| K4 | 8 | 7350ms | 7351ms |

### ms_gw
| 窗口 | 总请求 | 成功 | 失败 |
|------|--------|------|------|
| 6h | 0 | 0 | 0 |
| 24h | 0 | 0 | 0 |

### Docker Logs (nv_gw)
- 最近 100 行: 0 error, 0 warn, 0 traceback

### 当前参数 (docker exec nv_gw env)
```
TIER_TIMEOUT_BUDGET_S=114
UPSTREAM_TIMEOUT=64
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=3
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=1.0
FALLBACK_HEALTH_THRESHOLD=0.05
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64
```

## 决策

**NOP** — 零配置变更，零 compose 修改，零容器重启。

### 理由
1. nv_gw 6h 100% SR，零错误，零 tier_attempts
2. 唯一 24h ATE 为 NVCF 上游 transient 事件（与 R939-R940 相同），非本地可修
3. 所有可调参数均已至 floor/optimal，无进一步优化空间
4. ms_gw 零流量，无优化目标
5. Per-key 延迟分布正常（K2 偏慢但仍在 NVCF 上游正常波动范围）

### 铁律检查
- ✅ 改前必有数据 — SSH + DB 查询完整收集
- ✅ 只改 HM1 不改 HM2 — 本次无修改
- ✅ 回合文件写入仓库

## ⏳ 轮到HM1优化HM2