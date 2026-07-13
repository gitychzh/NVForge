# HM2→HM1 NOP — Round R1236 (false trigger, double-dispatch)

**触发**: 2026-07-13 19:40 UTC, cron 误触发 (自提交 `907450a` → `"这是我提交的, 不触发"`)

## 1. 数据快照 (6h, 创建时间 ~11:43 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 108 |
| 成功 | 83 (76.9% SR) |
| 失败 | 25 |
| dsv4p_nv | 8req/3OK(37.5%, all ATE null-key) |
| glm5_2_nv | 100req/80OK(80.0%) |

## 2. 错误分类

| 错误类型 | 计数 | 平均延迟 | 状态 |
|----------|------|----------|------|
| zombie_empty_completion | 13 | 24.0s | NVCF content-filter, not config-fixable |
| all_tiers_exhausted | 11 | 136.8s | ms_gw BrokenPipeError code-level defect |
| NVStream_IncompleteRead | 1 | 50.7s | transient |

## 3. Tier 尝试分析 (6h)

| Tier | Key | 错误 | 计数 |
|------|-----|------|------|
| glm5_2_nv | k0 | IntegrateTimeout | 3 (avg 91.0s) |
| glm5_2_nv | k3 | IntegrateTimeout | 2 (avg 92.0s) |
| glm5_2_nv | k2 | IntegrateTimeout | 1 (91.1s) |

IntegrateTimeout 均匀分布在 k0/k2/k3 — function-level 信号，非 per-key 退化。

## 4. Fallback 状态

- fallback 触发: 0/108
- ms_gw 流量: 16 (全部失败, error_type=null → BrokenPipeError code-level defect)
- peer-fb: 无触发 (SKIP_MODELS=glm5_2_nv)

## 5. 参数状态评估

| 参数 | 当前值 | 状态 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 66 | optimal | PexecTimeout max < 66s; buffer sufficient |
| TIER_TIMEOUT_BUDGET_S | 210 | optimal | R1231 部署, 208s peer-fb window |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal | function-level 信号, 已验证 |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal | key-specific empty_200, R1031 修正 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal | function-level integrate timeout |
| TIER_COOLDOWN_S | 15 | optimal | R1103 回退 R1018; key-specific empty_200 |
| KEY_COOLDOWN_S | 25 | floor | |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor | |
| NVU_CONNECT_RESERVE_S | 0 | floor | |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal | R1116 部署 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal | |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | stable | R923 部署 |

## 6. 决策: NOP

**所有参数 floor/optimal。NOP。**

- 13 zombie_empty_completion: NVCF content-filter, 代码级检测, 不可配置修复
- 11 all_tiers_exhausted: ms_gw BrokenPipeError code-level defect, 不可配置修复
- 1 NVStream_IncompleteRead: 瞬态, 无模式
- IntegrateTimeout 均匀分布 (k0/k2/k3): function-level 信号, FASTBREAK=1 正确
- 零 dsv4p_nv pexec 错误 (每 key 100% SR); 5 ATE 全为 null-key (全池耗尽)
- ms_gw 0/16 OK (BrokenPipeError code-level defect, 无法配置修复)
- Compose md5 未变, 无容器重启, 无配置漂移

**0 参数变更。0 容器重启。铁律: 只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2
