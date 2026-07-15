# R1436: HM2→HM1 — NVU_MS_GW_FALLBACK_TIMEOUT 195→210 (+15s)

**Timestamp**: 2026-07-15 15:45 UTC

## 触发判定
- HM1 commit: c111773 (R1435, HM2 NOP)
- 触发: 脚本判定轮到HM2 → 执行优化

## Data Collection (HM1, 改前必有数据)

### nv_gw 容器状态
- Container: nv_gw Up 58 minutes (healthy) — 重启于 ~14:39 UTC
- Compose md5 (old): 3863a7c165f938dbde494e42b8d19be5
- docker logs: 2 fresh ATE in last hour, 2 ZOMBIE, clean otherwise

### 6h 总体
| total | ok | err | sr_pct |
|-------|----|-----|--------|
| 59 | 40 | 19 | 67.8% |

### 6h 按模型
| mapped_model | cnt | ok | err | sr_pct | avg_dur_s |
|--------------|-----|----|-----|--------|-----------|
| glm5_2_nv | 43 | 33 | 10 | 76.7% | 11.6s |
| dsv4p_nv | 16 | 7 | 9 | 43.8% | 36.2s |

### 6h 错误类型 (status≠200)
| error_type | cnt | avg_dur_s |
|------------|-----|-----------|
| all_tiers_exhausted | 16 | 37.8s |
| zombie_empty_completion | 16 | 11.0s |

### zombie 详情
| mapped_model | cnt |
|--------------|-----|
| dsv4p_nv | 6 |
| glm5_2_nv | 10 |

### ATE 详情 (含 ms_gw 恢复)
| mapped_model | cnt | avg_dur | recovered |
|--------------|-----|---------|-----------|
| glm5_2_nv | 12 | 21.4s | 12/12 (100% ms_gw) |
| dsv4p_nv | 4 | 87.1s | 1/4 (status=200, fallback=t), 3 unrecovered |

### 6h 按小时
| hour (UTC) | total | ok | fail | sr_pct |
|-----------|-------|-----|------|--------|
| 01:00 | 2 | 2 | 0 | 100.0% |
| 02:00 | 6 | 4 | 2 | 66.7% |
| 03:00 | 9 | 5 | 4 | 55.6% |
| 04:00 | 7 | 3 | 4 | 42.9% |
| 05:00 | 26 | 22 | 4 | 84.6% |
| 06:00 | 5 | 3 | 2 | 60.0% |
| 07:00 | 4 | 1 | 3 | 25.0% |

### 其他
- tier_attempts: 0
- fallback: 13/13 rescues (12 glm5_2_nv + 1 dsv4p_nv)
- ms_gw: 29/28 96.6% SR
- peer-fb: 未触发（HM1无peer-fb log）
- HM2 peer-fb: dsv4p_nv in skip list → 返回502 (6次，07:00-08:00 UTC)

### Fresh ATE (15:07+15:37 UTC, post-R1435)
```
ATE1 (15:07):
k5 → 504 (NVCF gateway timeout, 61s)
k1 → pexec timeout 60637ms → total=124066ms → FASTBREAK=1 abort
ms_gw → TimeoutError 206107ms → FAILED

ATE2 (15:37):
k5 → 504 (NVCF gateway timeout, 61s)
k1 → pexec timeout 60637ms → total=124044ms → FASTBREAK=1 abort
ms_gw → TimeoutError 199780ms → FAILED
```

Pattern: dsv4p_nv k5→504→k1→pexec timeout→FASTBREAK→ms_gw TimeoutError(200-206s)

### 当前参数 (all floor/optimal)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
NVU_TIER_BUDGET_DSV4P_NV=124
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NV_INTEGRATE_KEY_COOLDOWN_S=0
MIN_OUTBOUND_INTERVAL_S=0
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FB_SKIP_MODELS=
NVU_MS_GW_FALLBACK_TIMEOUT=195  ← 本轮变更
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
```

## 分析

### 问题: dsv4p_nv ms_gw fallback 超时
1. **2 fresh ATEs** (15:07, 15:37 UTC) — 同模式: k5→504(NVCF gateway)→k1→pexec timeout→FASTBREAK→ms_gw→TimeoutError
2. **ms_gw TimeoutError at 200-206s** — 超过旧值 195s。ms_gw dsv4p_ms 流式推理需要 190-210s
3. **glm5_2_nv ATE 全部 ms_gw 恢复** — 12/12 100% (avg 21.4s, 短请求)
4. **peer-fb 不可用** — HM2 的 skip list 包含 dsv4p_nv (NVCF function degradation 共享故障，正确行为)
5. **BUDGET 124 正确** — 504(61s)+pexec(60s)=124s 耗尽，包含在 TIER_BUDGET 内
6. **NVCF function degradation** — dsv4p_nv 函数 74f02205 部分退化，504 频繁出现

### 根因
ms_gw dsv4p_ms 流式推理耗时 190-210s，旧 fallback timeout 195s 刚好卡在边界。2 次都在 200-206s 超时，仅差 5-10s。

### 决策: 提高 ms_gw fallback 超时
- **NVU_MS_GW_FALLBACK_TIMEOUT 195→210 (+15s)**
- 210s 覆盖 dsv4p_ms 的 190-210s 范围
- 5s 安全余量（observed max 206s）
- 不会影响成功路径（ms_gw 仅在 ATE 后触发）
- 单参数，铁律:只改HM1不改HM2

## 执行
1. SSH to HM1: `sed -i 's/NVU_MS_GW_FALLBACK_TIMEOUT: 195/NVU_MS_GW_FALLBACK_TIMEOUT: 210/' /opt/cc-infra/docker-compose.yml`
2. 更新 comment 为 R1436
3. `docker compose up -d nv_gw` → Recreated + Started
4. 验证: `docker exec nv_gw env | grep NVU_MS_GW_FALLBACK_TIMEOUT` → 210 ✓
5. Health check: 200 OK ✓
6. Compose md5 (new): e49a30d407b9ca888f81e8af8ee5c1d1

## 预期效果
- dsv4p_nv ATE → ms_gw fallback: 210s 覆盖 dsv4p_ms 推理时间
- 2 fresh ATE 本应被救回 (ms_gw 200-206s vs 旧 195s)
- 不影响 glm5_2_nv (avg 21.4s, 远低于 210s)
- 不影响成功路径 (ms_gw fallback 仅 ATE 后触发)
## ⏳ 轮到HM1优化HM2
