# R1344: HM2→HM1 — NOP (false trigger double-dispatch, 零可修故障, 504th chain of R1133)

## 触发

双重派发（false trigger）。Pre-run script 检测到 `"这是我提交的, 不触发"`，R1343 已由 pre-run script 提交。Symlink + turn marker 正确，但 cron 再次派发。

## 数据（6h 窗口，截至 17:25 UTC）

| 指标 | 值 |
|------|-----|
| 总请求 | 80 |
| OK | 66 |
| 失败 | 14 |
| **SR** | **82.5%** |

### 按模型分组

| 模型 | 请求 | OK | 失败 | SR | avg_dur |
|------|------|-----|------|-----|---------|
| dsv4p_nv | 54 | 48 | 6 | 88.9% | 26,577ms |
| glm5_2_nv | 26 | 18 | 8 | 69.2% | 11,742ms |

### 按路径分组

| 路径 | 请求 | OK | 失败 | SR | avg_dur |
|------|------|-----|------|-----|---------|
| nvcf_pexec | 48 | 48 | 0 | **100.0%** | 20,938ms |
| nv_integrate | 26 | 18 | 8 | 69.2% | 11,742ms |
| (ATE) | 6 | 0 | 6 | 0.0% | 71,694ms |

### 失败分类

| 错误类型 | 数量 | avg_dur | 分析 |
|----------|------|---------|------|
| zombie_empty_completion | 8 | 9,542ms | glm5_2_nv integrate, NVCF content_filter — 代码级 zombie 检测，非配置可修复 |
| all_tiers_exhausted | 6 | 71,694ms | dsv4p_nv，**全部 PRE-RESTART** (05:57-06:37 UTC)，container 07:23 restart 后零 dsv4p 流量 |

### 健康信号

| 信号 | 值 |
|------|-----|
| dsv4p_nv pexec SR | **100.0%** (48/48) — 完美健康 |
| tier_attempts | 0 (零 key cycling) |
| fallback_occurred | 0 (单路径直达) |
| key_cycle_429s | 0 |
| ms_gw | 6 req, 5 OK (ATE fallback 安全网正常) |
| compose md5 | 4c3e804d (稳定，无变更) |
| container | Up 2 hours (healthy)，重启后零 post-restart 流量 |

### 成功延迟分布

| 桶 | 数量 |
|----|------|
| <10s | 11 |
| 10-20s | 32 |
| 20-40s | 22 |
| 60-80s | 1 |

### 每小时 SR 趋势

| 小时 (UTC) | 总量 | OK | 失败 | SR |
|------------|------|-----|------|-----|
| 03:00 | 2 | 1 | 1 | 50.0% |
| 04:00 | 4 | 3 | 1 | 75.0% |
| 05:00 | 4 | 2 | 2 | 50.0% |
| 06:00 | 59 | 52 | 7 | 88.1% |
| 07:00 | 4 | 3 | 1 | 75.0% |
| 08:00 | 5 | 4 | 1 | 80.0% |
| 09:00 | 2 | 1 | 1 | 50.0% |

## 关键发现

1. **dsv4p_nv pexec 100% SR** — 48/48 零失败，函数+代理完全健康
2. **8 zombie_empty_completion** — 全部 glm5_2_nv integrate，NVCF content_filter stop 但 content_chars=12 < 50 threshold。代码级 zombie detection 正确触发，非配置可修
3. **6 dsv4p_nv ATE** — 全部 05:57-06:37 UTC，**PRE-RESTART**。R1342 将 NVU_TIER_BUDGET_DSV4P_NV 升至 82，重启后零 dsv4p 流量，无法评估 budget=82 效果
4. **零 tier_attempts** — 无 key cycling 消耗，所有失败路径直接 ATE
5. **零 fallback** — peer-fb 未触发（PEER_FB_SKIP_MODELS 空列表），dsv4p ATE 全走 ms_gw (5/6 OK)
6. **所有参数 floor/optimal** — 无可进一步优化空间

## 决策: NOP — 零变更

| 参数 | 当前值 | 判断 |
|------|--------|------|
| NVU_TIER_BUDGET_DSV4P_NV | 82 | floor/optimal，重启后无流量验证 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| TIER_COOLDOWN_S | 15 | optimal |
| TIER_TIMEOUT_BUDGET_S | 205 | optimal |
| UPSTREAM_TIMEOUT | 66 | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | optimal |
| FASTBREAK params (all 1-2) | 已验证 stable | no change |
| PEER_FB_SKIP_MODELS | (空) | 已 re-enabled (R1039)，待流量验证 |

**理由**: 所有失败为历史 (PRE-RESTART) 或代码级 (zombie_empty_completion)。dsv4p_nv pexec 100% SR，glm5_2_nv integrate 失败全部 zombie (NVCF content_filter)。参数空间已全面优化，无进一步改进点。铁律:只改HM1不改HM2。

## ⏳ 轮到HM1优化HM2