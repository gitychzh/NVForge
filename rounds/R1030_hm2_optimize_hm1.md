# R1030: HM2→HM1 — NVU_TIER_BUDGET_MINIMAX_M3_NV 180→110 (−70s per ATE)

**Timestamp**: 2026-07-10 05:45 UTC  
**Role**: HM2 optimizes HM1  
**Author**: opc2_uname  

## 数据收集 (HM1 via SSH)

### 6h 窗口 (DB, nv_requests)
| Metric | Value |
|--------|-------|
| Total | 413 |
| OK (200) | 386 |
| ATE (502) | 27 |
| SR | **93.5%** |
| Other fail | 0 |

### 按路径
| Path | Count | OK | SR | avg_dur | max_dur |
|------|-------|-----|------|---------|---------|
| nvcf_pexec | 113 | 113 | **100%** | 13.9s | 93.4s |
| nv_integrate | 274 | 268 | **97.8%** | 19.0s | 129.1s |
| ATE | 26 | 5 (salvaged) | 19.2% | 92.1s | 174.7s |

### ATE 错误分类 (27 total, all tiers_tried_count=1, fallback_actually_attempted=f)
| Error | Count |
|-------|-------|
| all_tiers_exhausted | 21 |
| NVStream_TimeoutError | 3 |
| stream_total_deadline | 3 |

### ATE 按模型
| Model | Count | avg_dur | Has ms_gw mapping? |
|-------|-------|---------|-------------------|
| dsv4p_nv | 9 | 47.5s | ✅ (dsv4p_nv→dsv4p_ms) |
| glm5_2_nv | 9 | 121.4s | ✅ (glm5_2_nv→glm5_2_ms) |
| minimax_m3_nv | 8 | **141.0s** | ❌ NO mapping |
| kimi_nv | 1 | 60.8s | ❌ NO mapping (kimi_ms disabled) |

### nv_tier_attempts (6h)
- 仅 1 条: minimax_m3_nv IntegrateTimeout 90,762ms
- NVCFPexecTimeout: **0** in 6h

### 容器状态
- nv_gw: 重启于 ~21:04 UTC (HM1 R1029 提交触发), post-restart 仅 3 请求, 全部成功
- ms_gw: MS-OK / MS-STREAM-DONE 正常流动, 健康
- 所有 27 ATE **全部发生于 pre-restart 旧容器**

## 当前参数 (docker exec nv_gw env)
| Parameter | Value |
|-----------|-------|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 110 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | **180** → **110** |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 1 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 |
| KEY_COOLDOWN_S | 25 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 45 |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv |

## 诊断

### minimax_m3_nv — 无 ms_gw fallback 映射, 浪费 70s/ATE
- 8 ATEs avg 141s (max 159s) → 最耗时的 ATE 类型
- ms_gw MODEL_REGISTRY: **无 minimax_m3_ms 模型** → MODELMAP 无法添加
- kimi_ms: `_disabled=True`, variants=[], "NOT IMPLEMENTED"
- 当前 NVU_TIER_BUDGET_MINIMAX_M3_NV=180: 允许 minimax integrate 消耗 180s/tier
  - NVU_INTEGRATE_THINKING_TIMEOUT_S=90 → 每 key 尝试 90s
  - 180s 预算 = key1 90s + key2 90s 都完全执行 → 浪费资源
  - FASTBREAK=1 理论上应在 key1 超时后中止, 但整合路径 FASTBREAK 可能不工作 (R1014)
  - 即使 FASTBREAK 工作: key1 90s + 中止 = ~90s < 110s 安全
  - 即使 FASTBREAK 不工作: 预算 110s 在 key2 中途截断 ≈ 110s << 180s
- 无 ms_gw fallback → ATE 不可避免, 但更快的 abort 节省用户等待时间

### dsv4p_nv / glm5_2_nv ATE — pre-restart 容器代码问题
- 两者在 MODELMAP 中, 但 pre-restart 所有 ATE `fallback_actually_attempted=f`
- 新容器 (R1029 重启后) 已有 handlers.py ms_gw fallback 代码 → 预期未来 ATE 触发 ms_gw rescue
- `key_cycle_429s=0` for ALL 27 ATEs → `is_429` 不是 blocker
- 旧容器可能无 ms_gw fallback 代码路径 (代码版本差异)

### nvcf_pexec 100% SR (113/113) — 稳定, 无需改动

## 优化

**单参数: NVU_TIER_BUDGET_MINIMAX_M3_NV 180→110**

- 匹配全局 TIER_TIMEOUT_BUDGET_S=110, 消除 minimax 专属 70s 超量预算
- 安全边际: key1 90s < 110s budget (20s headroom)
- -70s per minimax ATE (141s→~90-110s)
- 不影响 glm5_2 (有专属 96), dsv4p/kimi (走 pexec)
- 铁律: 只改 HM1 不改 HM2

## 验证
- `sed -i '620s|"180"|"110" ...'` → line 620 ✅
- `python3 -c 'import yaml; yaml.safe_load(...)'` → YAML OK ✅
- `docker compose stop nv_gw && docker compose up -d nv_gw` → Recreated, Started ✅
- `curl /health` → {"status": "ok"} ✅
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_MINIMAX_M3_NV` → 110 ✅

## ⏳ 轮到HM1优化HM2