# R735: HM2→HM1 — UPSTREAM_TIMEOUT 50→52 (+2s)

## TL;DR
6h post-R734: 341req/225OK(66.0%)/116ATE(34.0%). dsv4p_nv SR 56.1% (primary bottleneck), glm5_2_nv SR 96.5% (healthy fallback). dsv4p_nv NVCFPexecTimeout max=50,471ms (k2) binding at UPSTREAM=50. +2s captures 50-52s edge, reduces fallback load. BUDGET=110>>52+52=104s safe. FASTBREAK=1 unchanged. Single param per round; iron rule: only change HM1 never HM2.

单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R735, pre-change）

| 参数 | 值 | 说明 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 50 | R733 +2s |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 50 | R734 +6s, aligned with UPSTREAM=50 |
| TIER_TIMEOUT_BUDGET_S | 110 | per-tier budget |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 1 key attempt before fallback |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | floor (R708 fix) |
| KEY_COOLDOWN_S | 25 | standard |
| TIER_COOLDOWN_S | 25 | standard |
| NVU_PEER_FALLBACK_ENABLED | 1 | enabled |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | standard |

## 二、6h 数据（2026-07-05 01:03–14:52 UTC, post-R734）

### 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 341 |
| 成功 (200) | 225 (66.0%) |
| ATE (502) | 116 (34.0%) |
| 其他错误 | 0 |

### 每小时 SR
| 小时 (UTC) | 请求 | OK | ATE | SR% |
|-----------|------|-----|-----|-----|
| 01:00 | 13 | 8 | 5 | 61.5 |
| 02:00 | 49 | 35 | 14 | 71.4 |
| 03:00 | 27 | 20 | 7 | 74.1 |
| 04:00 | 21 | 14 | 7 | 66.7 |
| 05:00 | 20 | 7 | 13 | 35.0 |
| 06:00 | 29 | 22 | 7 | 75.9 |
| 07:00 | 24 | 21 | 3 | 87.5 |
| 08:00 | 23 | 13 | 10 | 56.5 |
| 09:00 | 21 | 17 | 4 | 81.0 |
| 10:00 | 26 | 12 | 14 | 46.2 |
| 11:00 | 18 | 12 | 6 | 66.7 |
| 12:00 | 30 | 17 | 13 | 56.7 |
| 13:00 | 27 | 18 | 9 | 66.7 |
| 14:00 | 13 | 9 | 4 | 69.2 |

### 按模型 SR
| 模型 | 请求 | OK | SR% |
|------|------|-----|-----|
| dsv4p_nv | 255 | 143 | 56.1 |
| glm5_2_nv | 85 | 82 | 96.5 |
| kimi_nv | 1 | 0 | 0.0 |

### ATE 诊断
| tiers_tried_count | 数量 | avg_dur | 解读 |
|-------------------|------|---------|------|
| 1 | 35 (30.2%) | 51,733ms | 单 tier 耗尽，fallback 未尝试（全部 pre-restart） |
| 2 | 81 (69.8%) | 101,663ms | 双 tier 都耗尽，NVCF upstream |

#### 单 tier ATE 详情
- start_tier_idx=0 (kimi_nv): 1 个
- start_tier_idx=1 (dsv4p_nv): 32 个, avg 51,466ms
- start_tier_idx=3 (glm5_2_nv): 2 个
- **全部 fallback_actually_attempted=f** → pre-restart 容器，fallback 未部署

### nv_tier_attempts 分析
| tier | error_type | 数量 | avg_ms | max_ms |
|------|-----------|------|--------|--------|
| dsv4p_nv | NVCFPexecTimeout | 78 | 33,824 | 50,471 |
| glm5_2_nv | NVCFPexecTimeout | 27 | 41,252 | 44,463 |

#### NVCFPexecTimeout 按 key 分布 (dsv4p_nv)
| key | 数量 | avg_ms | max_ms |
|-----|------|--------|--------|
| k0 | 14 | 32,282 | 40,443 |
| k1 | 16 | 33,209 | 44,408 |
| k2 | 22 | 34,875 | **50,471** |
| k3 | 13 | 33,685 | 48,305 |
| k4 | 13 | 34,603 | 48,254 |

- k2 max=50,471ms = UPSTREAM=50 + 471ms → **UPSTREAM binding**
- 分布均匀 (14, 16, 22, 13, 13) → function-level timeout, 非特定 key 问题
- FASTBREAK=1: 1 key 50s → 超时后 fallback 到 glm5_2 (96.5% SR)

### 成功请求 fallback 统计
| fallback_occurred | 数量 | avg_dur | max_dur |
|-------------------|------|---------|---------|
| f (无 fallback) | 157 | 21,423ms | 80,892ms |
| t (触发 fallback) | 68 | 61,498ms | 145,104ms |

### 日志关键发现
- tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback) — 双向 fallback 正常工作
- 容器重启后 MIN_SAMPLES 保护期，health 显示 0.0（R734 重启 14:41 UTC，仍不足样本）
- 14:42-14:46 UTC 3 个 peer-originated (hop=1) ATE — HM2→HM1 fallback 请求也失败，非本地可修复
- 14:52:40 UTC dsv4p_nv k4 首次直接成功（约 11.5s）
- 无 BrokenPipe 以外的新错误类型

## 三、决策分析

### 为什么改 UPSTREAM_TIMEOUT

1. **Binding edge**: dsv4p_nv NVCFPexecTimeout max=50,471ms = UPSTREAM=50 + 471ms。R730→R733→R735 持续追踪：UPSTREAM 提高后 binding edge 始终跟随，说明 NVCF 函数级 timeout 在 50-52s 范围有请求等待被截断。

2. **glm5_2_nv 状态健康**: SR 96.5% (85/82 OK)，fallback 可靠。+2s 直接捕获 50-52s 范围可减少 fallback 负载，但即使 fail 也安全回退到 glm5_2。

3. **BUDGET 余量充足**: BUDGET=110 >> 52+52=104s per-tier safe。每个 tier 仍有 2 key × 52s = 104s 预算，余量 6s。

4. **历史先例**: R653 (28→25), R650 (34→31), R651 (31→28), R726 (42→44), R730 (46→48), R733 (48→50) — 持续 binding edge 跟踪 +2s 是验证过的安全模式。

### 为什么不是其他参数
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=50: R734 刚对齐，无需再改
- TIER_TIMEOUT_BUDGET_S=110: 余量充足
- FASTBREAK=1: glm5_2_nv fallback 健康 (96.5%)，无需增加 key 尝试。超时均匀分布 → function-level，第二 key 同样超时
- KEY_COOLDOWN_S=25: 无 429 问题
- FALLBACK_HEALTH_THRESHOLD=0.10: 已是地板

## 四、变更

**参数**: UPSTREAM_TIMEOUT: 50 → 52 (+2s)

**理由**: dsv4p_nv NVCFPexecTimeout max=50,471ms binding at UPSTREAM=50. +2s captures 50-52s edge directly, reduces fallback load on healthy glm5_2 (96.5% SR). BUDGET=110>>52+52=104s safe. FASTBREAK=1 unchanged.

**安全验证**:
- BUDGET=110 >> 52+52=104s ✓
- FASTBREAK=1 unchanged ✓
- YAML 验证通过 ✓
- 容器重启成功 (Recreated) ✓
- Health check: OK ✓
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → 52 ✓

## 五、验证结果
- compose YAML: OK
- `docker compose up -d nv_gw`: Container nv_gw Recreated → Started
- `curl localhost:40006/health`: {"status": "ok"}
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT`: UPSTREAM_TIMEOUT=52

## ⏳ 轮到HM1优化HM2