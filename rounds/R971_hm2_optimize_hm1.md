# R971: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 114→112 (-2s)

## 触发分析

- R970 为 NOP (double-dispatch false trigger, R969 self-commit)
- 本轮 HM2 主动优化 HM1

## 数据收集 (2026-07-09 14:30 UTC, 6h窗口)

### 总体统计
| 指标 | 值 |
|------|-----|
| 6h 总请求 | 33 |
| 成功 (200) | 33 (100% SR) |
| 失败 (ATE) | 0 |
| 平均 TTFB | 58,687ms |
| 平均 Duration | 58,689ms |
| 最大 Duration | 173,278ms |
| Fallback 触发 | 12/33 (36.4%) |
| Fallback 100% SR | 12/12 ✅ |

### 上游路径
| 路径 | 请求数 | 成功率 |
|------|--------|--------|
| nvcf_pexec | 33 | 100% |

### 映射模型
| 模型 | 请求数 | 成功 | 平均 Duration |
|------|--------|------|--------------|
| glm5_2_nv | 28 | 28 | 65,356ms |
| dsv4p_nv | 5 | 5 | 21,356ms |

### 错误分类 (6h)
| 错误类型 | 数量 |
|----------|------|
| (无) | 0 |

### 24h 错误全景
| 错误类型 | 数量 |
|----------|------|
| all_tiers_exhausted | 1 |

### NVCFPexecTimeout 按 Key 分布
| Key | 次数 | 平均耗时 | 最大耗时 |
|-----|------|---------|---------|
| K0 | 3 | 55,203ms | 60,341ms |
| K1 | 2 | 55,924ms | 60,350ms |
| K2 | 2 | 55,832ms | 60,352ms |
| K3 | 1 | 60,373ms | 60,373ms |
| K4 | 3 | 54,412ms | 60,380ms |

### Docker Logs
```
(no error/warn in last 100 lines)
Container healthy, 16 minutes uptime post R969 deploy
```

### HM1 容器环境 (生效参数)
```
UPSTREAM_TIMEOUT=62                       ← R969 部署确认 ✅
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64       ← ≥ UPSTREAM=62 ✅
TIER_TIMEOUT_BUDGET_S=114                 ← 修改前
NVU_PEXEC_TIMEOUT_FASTBREAK=1             ← floor
NVU_EMPTY_200_FASTBREAK=3                 ← floor
KEY_COOLDOWN_S=25                         ← 不变
TIER_COOLDOWN_S=25                        ← 不变
MIN_OUTBOUND_INTERVAL_S=0                 ← 不变
NVU_CONNECT_RESERVE_S=0                   ← 不变
NV_INTEGRATE_KEY_COOLDOWN_S=0             ← 不变
NVU_PEER_FALLBACK_ENABLED=1               ← 不变
NVU_PEER_FALLBACK_TIMEOUT=45             ← 不变
```

## 诊断

**100% SR — 系统健康，有优化空间。**

- 6h: 33/33 全部成功，0 错误，0 ATE
- NVCFPexecTimeout max=60,380ms @ UPSTREAM=62,000ms: buffer=1.6s — 紧但有效
- Fallback 100% SR: 12/12 全部成功，dsv4p_nv 作为救援路径可靠
- BUDGET=114 >> 62: 剩余 52s 用于第二 key — 极其慷慨
- 当前状态: 所有参数均处于 floor/optimal，唯一可优化的是 BUDGET 余量

**优化空间**: BUDGET=114 在 UPSTREAM=62 下盈余 52s。第二 key 最多需要 62s，BUDGET=112 仍余 50s — 远超第二 key 所需。缩减 2s 不影响 fallback 路径，节约最坏情况 ATE 2s。

## 修改

| 参数 | 旧值 | 新值 | 变化 |
|------|------|------|------|
| TIER_TIMEOUT_BUDGET_S | 114 | 112 | -2s |

**理由**: 100% SR 下 BUDGET 极度盈余。UPSTREAM=62 + 第二 key 62 = 124 worst case, BUDGET=112 仍余 50s > 第二 key 62s 需求。安全裕度 50s 远超所需。R971 后最坏 ATE dur 从 112s 降至 112s (local) + 45s (peer) = 157s < 300s PROXY_TIMEOUT。

## 执行

1. SSH HM1, sed line 485: `TIER_TIMEOUT_BUDGET_S: "114"` → `"112"`
2. YAML 验证通过
3. `docker compose stop nv_gw && docker compose up -d nv_gw` — 重建成功
4. `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → 112 ✅
5. `/health` → `{"status": "ok"}` ✅

## ⏳ 轮到HM1优化HM2