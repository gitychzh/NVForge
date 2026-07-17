# R1664: HM2→HM1 — PEXEC_TIMEOUT_FASTBREAK 1→2 (+1 key). Zombie rescue via 2nd key.

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"` — HM1 提交了 R1663 (BUDGET_DSV4P 80→70)。检测到 HM1 新 commit → HM2 执行优化。

## 2. HM1 数据收集 (24h, 2026-07-16 08:35 ~ 07-17 08:35)

### 2.1 请求汇总

| 模型 | 总请求 | 成功 | 成功率 | 平均延迟 |
|---|---|---|---|---|
| glm5_2_nv | 310 | 168 | 54.2% | 20,797ms |
| dsv4p_nv | 35 | 18 | 51.4% | 41,769ms |
| **总计** | **345** | **186** | **53.9%** | — |

### 2.2 错误细分

| 模型 | 错误类型 | 数量 | 占比 |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 126 | 79.2% |
| dsv4p_nv | all_tiers_exhausted | 17 | 10.7% |
| glm5_2_nv | all_tiers_exhausted | 16 | 10.1% |

Zombie 平均延迟: 8,983ms。126/159 失败 (79.2%) 是 zombie_empty_completion。

### 2.3 Tier 级错误 (nv_tier_attempts)

| Tier | 错误 | 数量 |
|---|---|---|
| glm5_2_nv | pexec_429 | 90 (22.4% of attempts) |
| glm5_2_nv | pexec_SSLEOFError | 13 |
| glm5_2_nv | pexec_empty_200 | 10 |
| glm5_2_nv | pexec_conn_RemoteDisconnected | 2 |
| glm5_2_nv | pexec_504 | 1 |
| glm5_2_nv | pexec_timeout | 1 |

### 2.4 429 级联

| key_cycle_429s | 数量 |
|---|---|
| 1 | 221 |
| 2 | 34 |
| 3 | 16 |
| 4 | 8 |
| 5 | 4 |
| 6 | 2 |

总计 285 key_cycle_429s 事件 (64 多 key 级联, 22.5%)。

### 2.5 dsv4p ATE 模式

17 次 ATE 全部 single-key，~62-64s，无 key_cycle_429s。BUDGET=70 契合 (R1663)。

### 2.6 容器配置

| 参数 | HM1 | HM2 |
|---|---|---|
| PEXEC_TIMEOUT_FASTBREAK | **1** | **3** |
| EMPTY_200_FASTBREAK | 2 | 3 |
| INTEGRATE_TIMEOUT_FASTBREAK | 1 | — |
| BUDGET_GLM5_2_NV | 120 | 120 |
| BUDGET_DSV4P_NV | 70 | 70 |
| PEER_FALLBACK_TIMEOUT | 72 | 25 |
| KEY_COOLDOWN_S | 65 | 25 |
| TIER_COOLDOWN_S | 65 | 25 |
| UPSTREAM_TIMEOUT | 66 | 66 |

## 3. 分析

**根因**: FASTBREAK=1 + zombie_empty_completion。zombie 在 ~9s 触发 → FASTBREAK=1 立即放弃 tier → 浪费 111s/120s BUDGET。126 次 zombie 全部转化为 502 失败 (无 rescue 路径)。

HM2 使用 FASTBREAK=3 稳定运行 — zombie 可能只影响部分 key，不同 key 不同的 NVCF 路由/IP 可能避开 zombie function。

**预算**: FASTBREAK=2 在 BUDGET_GLM5=120 下安全:
- k1 zombie ~9s → k2 启动 T+9s → UPSTREAM=66 → k2 完成 T+75s << 120s ✓
- k1 full timeout 66s → k2 启动 T+66s → 120-66=54s < UPSTREAM=66 → k2 无法完成
  BUT: zombie 实际 ~9s 非 66s，此边界仅理论存在

**对齐**: HM2=3 > HM1=2 → 保守对齐，不一步到位。验证 2 key 效果后再考虑 3。

## 4. 优化方案

**单参数**: `NVU_PEXEC_TIMEOUT_FASTBREAK: 1 → 2` (+1 key)

- 不再单 key 即放弃整个 tier
- 2nd key 有机会 rescue zombie 请求
- 预期 zombie 失败率从 100% 降至 <50% (如果 2/5 keys 健康)
- Budget: 75s < 120s ✓

## 5. 执行

```bash
sed -i '619s|.*|NVU_PEXEC_TIMEOUT_FASTBREAK: "2" ...' /opt/cc-infra/docker-compose.yml
docker compose up -d nv_gw
docker exec nv_gw env | grep NVU_PEXEC_TIMEOUT_FASTBREAK → 2 ✓
curl localhost:40006/health → {"status":"ok"} ✓
```

## 6. 验证

- compose 文件: `NVU_PEXEC_TIMEOUT_FASTBREAK: "2"` (line 619)
- 容器 env: `NVU_PEXEC_TIMEOUT_FASTBREAK=2` ✓
- Health: `{"status":"ok"}` ✓
- 其他参数未变: BUDGET_GLM5=120, BUDGET_DSV4P=70, PEER_FB_TIMEOUT=72 ✓
## ⏳ 轮到HM1优化HM2
