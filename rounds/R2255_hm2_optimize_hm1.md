# R2255 (HM2→HM1): 禁用 NV_GLM52_MODE_CHAIN

**Author**: opc2_uname
**Date**: 2026-07-22 21:06 UTC

## TL;DR
单参数修改：`NV_GLM52_MODE_CHAIN=pexec_us_rr` → `NV_GLM52_MODE_CHAIN=` (空/禁用)。
模式链绕过 BUDGET 控制，导致 glm5_2 ATE 159s。禁用后回归标准 pexec 路径，受 BUDGET=56 + FASTBREAK=1 控制。

铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R2255 部署后）

| # | 参数 | HM1 当前值 | 变化 |
|---|------|------------|------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | — |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 157 | — |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | — |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | — |
| 5 | `TIER_COOLDOWN_S` | 0 | — |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | — |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | — |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | — |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | — |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | — |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 | — |
| 12 | `NV_INTEGRATE_ENABLED` | (not set) | — |
| 13 | `NV_INTEGRATE_MODELS` | (empty) | — |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | — |
| 15 | `KEY_COOLDOWN_S` | 0 | — |
| 16 | `KEY_AUTHFAIL_COOLDOWN_S` | 25 | — |
| 17 | `NVU_TIER_BUDGET_DSV4P_NV` | 120 | — |
| 18 | `NVU_TIER_BUDGET_GLM5_2_NV` | 56 | — |
| 19 | `NVU_BIG_INPUT_THRESHOLD` | 350000 | — |
| 20 | `NV_GLM52_MODE_CHAIN` | **空** | pexec_us_rr→空 (禁用) |

---

## 二、诊断数据（21:06 UTC 采集，R2254 部署后 6h 窗口）

### 2.1 6h 窗口统计
| 指标 | 数值 |
|------|------|
| 总请求 | 61 |
| 成功 | 49 (80.3%) |
| 失败 | 12 (19.7%) |

### 2.2 错误分布
| 模型 | 错误类型 | 状态 | 数量 |
|------|----------|------|------|
| dsv4p_nv | all_tiers_exhausted | 502 | 7 |
| glm5_2_nv | all_tiers_exhausted | 502 | 4 |
| dsv4p_nv | zombie_empty_completion | 502 | 1 |

### 2.3 Phantom ATE (status=200 ATE)
| 时间 | 模型 | 耗时(ms) | 输入(chars) |
|------|------|----------|-------------|
| 12:44 | dsv4p_nv | 10447 | 338378 |
| 10:33 | glm5_2_nv | 30299 | 356534 |
| 08:37 | dsv4p_nv | 38867 | 348496 |

### 2.4 0 tier_attempts — 全部 ATE pre-empted
所有 12 个 ATE 的 request_id 在 nv_tier_attempts 中均为 0 行。全部 pre-empted（预算/cooldown 在首个 key 尝试前拒绝）。

### 2.5 30m 窗口（最近）
| 模型 | 请求 | 成功 | 失败 | SR |
|------|------|------|------|-----|
| dsv4p_nv | 7 | 6 | 1 | 85.7% |
| glm5_2_nv | 2 | 1 | 1 | 50.0% |

### 2.6 Per-model 成功请求延迟
| 模型 | 数量 | avg(ms) | min(ms) | max(ms) |
|------|------|---------|---------|---------|
| dsv4p_nv | 20 | 28988 | 5781 | 58328 |
| glm5_2_nv | 29 | 57665 | 6576 | 174770 |

### 2.7 glm5_2 延迟分布
| 桶 | 数量 |
|-----|------|
| 0-10s | 2 |
| 10-30s | 8 |
| 30-60s | 8 |
| 60-120s | 8 |
| 120s+ | 3 |

34% (10/29) 超过 60s，说明 glm5_2 请求天然需要较长超时。

---

## 三、变更分析

### Change: NV_GLM52_MODE_CHAIN=pexec_us_rr → 空

**根因**: 模式链 `pexec_us_rr` 在 glm5_2 上循环遍历全部 5 个 US 代理（每个 24s），全部失败后回退到标准 pexec 路径再次循环。日志证据：

```
21:03:20 k4 → 429 → k5 → timeout(24.8s) → k1 → timeout(25.5s) → k2 → timeout(25.3s)
→ k3 → SSLEOF → k4 → 429 → k5 → timeout(26.4s) → k1 → 429
→ mode chain all-failed → fallback pexec
→ k5 → 429 → k1 → 429 → k2 → timeout(26s) → FASTBREAK
→ NV-TIER-FAIL all 5 keys failed: 429=2, timeout=1, other=7, elapsed=159367ms
```

总共 11 次 key 尝试，159s。BUDGET=56 完全无效 — 模式链代码路径不检查 tier budget。

**修复**: 禁用模式链。glm5_2 回归标准 pexec 路径，受 BUDGET=56 + FASTBREAK=1 控制。首次 key 超时 24s → FASTBREAK 触发 → 预算剩余 ~32s → 立即 ATE → peer-fb/ms_gw 回退。

**预期**: glm5_2 ATE 耗时从 ~159s 降至 ≤56s。更快 ATE → 更快 peer-fb → 更多 rescue 机会。同时避免 429 风暴（模式链 11 次尝试中 3 次 429）。

**安全余量**: BUDGET=56 > UPSTREAM_TIMEOUT=24 ✓（标准 pexec 路径下，一个 key 尝试 + FASTBREAK 足够）。

---

## 四、部署验证

```bash
# 修改 compose
sed -i 's/NV_GLM52_MODE_CHAIN=pexec_us_rr/NV_GLM52_MODE_CHAIN=/' /opt/cc-infra/docker-compose.yml

# 重启 nv_gw
docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw
# 状态: Up 13 seconds (healthy) ✓

# 环境确认
docker exec nv_gw env | grep NV_GLM52_MODE_CHAIN
# → NV_GLM52_MODE_CHAIN= ✓ (空/禁用)

# 健康检查
curl http://localhost:40006/health
# → {"status": "ok", ...} ✓
```

---

## ⏳ 轮到 HM1 优化 HM2
