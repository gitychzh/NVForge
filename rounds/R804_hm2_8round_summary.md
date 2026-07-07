# R804: HM2 8 轮定时优化收尾 — R797-R803 总结

> 8 轮定时优化第 8 轮 (收尾). 承接 R797-R803.
> 用户报远程 5 agent 模型链路 bug, 8 轮数据驱动优化, 每轮重采数据定改动.
> 角色: HM2-only 部署; 共享源码仓库同步供 HM1.

## 8 轮改动总览

| 轮 | 改动 | 类型 | 效果 |
|---|---|---|---|
| R797 | per-tier budget (glm5_2_nv=70) + peer-fb skip (glm5_2_nv) + 源码 (upstream.py/handlers.py) | 源码+env | glm5_2 180s→70s 502, 跳过 peer-fb |
| R798 | NVU_EMPTY_200_FASTBREAK 2→1 | env | empty_200 125s→62s (dsv4p surge) |
| R799 | NVU_TIER_BUDGET_DSV4P_NV=130 | env | dsv4p 504 cycling 180s→125s |
| R800 | dsv4p_nv 加入 peer-fb skip | env | dsv4p 150s→130s (省 peer 25s) |
| R801 | dsv4p budget 130→70 | env | dsv4p 130s→70s (NVCF 持续 504 SR=0%) |
| R802 | NOP (链路验证) | — | 确认 ms_gw 18/18 ok, agent SR 100% |
| R803 | NOP (稳态) | — | NVCF 未恢复, 链路持续通畅 |
| R804 | 收尾总结 | — | 本 round |

## 最终状态 (2026-07-07 16:30 CST)

### nv_gw env (R797-R801 全部生效)
```
NVU_TIER_BUDGET_GLM5_2_NV=70
NVU_TIER_BUDGET_DSV4P_NV=70
NVU_EMPTY_200_FASTBREAK=1
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
```

### nv_requests (NV tier, 最近 10min)
| tier_model | status | count | avg_ms |
|---|---|---|---|
| dsv4p_nv | 502 | 2 | 70019 | ← R801 70s fail |
| glm5_2_nv | 502 | 4 | 755 | ← R797 0.76s fail |

### ms_requests (fallback, 最近 10min) — 7/7 ok
| backend_model | status | count | avg_ms |
|---|---|---|---|
| deepseek-ai/DeepSeek-V4-pro (各 variant) | ok | 7 | 14498-21846 |

agent 端到端 SR 100% 经 ms_gw.

### 容器: 8 容器全 Up (nv_gw/ms_gw/logs_db + cc4101/cx4102/opclaw4103/hm4104/oc4105)

## 核心成果

**改前问题**: 5 agent 链路 bug — 3 个 glm5_2_nv agent (cc4101/cx4102/opclaw4103) 卡死 ~360s, dsv4p_nv 后续也恶化.

**根因 (数据驱动定位)**:
1. NVCF ai-glm-5_2 (3b9748d8) DEGRADED, NVCF 明确 400 拒绝调用.
2. NVCF ai-deepseek-v4-pro (74f02205) 从间歇 surge (R797 时 SR 95%) 恶化到持续 504 (SR 0%).
3. 全局 TIER_TIMEOUT_BUDGET_S=180 + peer-fb (HM1 同 NVCF 同坏) 放大延迟: 失败请求 180s (本地) + 25-180s (peer) = 客户端卡死.

**修复 (R797-R801, 5 个改动)**:
- per-tier budget (R797 源码机制 + R799/R801 env): 坏 tier 快速失败 70s 而非 180s.
- per-model peer-fb skip (R797 源码 + R800 env): 跳过 HM1 同坏 peer-fb, 省 25-180s.
- empty_200 fastbreak (R798 env): dsv4p surge 时 62s 而非 125s.

**效果**:
- glm5_2_nv: 180s+peer → 0.76s 502 (NVCF DEGRADED 立即 400).
- dsv4p_nv: 180s+peer → 70s 502.
- agent (经 adapter fallback) → ms_gw: 端到端 SR 100%.
- 3 个 glm5_2_nv agent 卡死 ~360s → ~1s 落 ms_gw.

## 未解决 (NVCF 上游侧, 网关无法修复)

- NVCF ai-glm-5_2 (3b9748d8) DEGRADED: NVCF 侧问题, 待 NVCF 恢复 ACTIVE.
- NVCF ai-deepseek-v4-pro (74f02205) 持续 504: NVCF 侧 surge, 待恢复.
- 备选 function 不可用: 52e1ddb6 (flash, 400 bad-request), 8915fd28 (sglang, 404 not-found-for-account).

## 回滚指引 (NVCF 恢复后)

NVCF 74f02205 + 3b9748d8 恢复 ACTIVE 后:
1. compose 删 `NVU_TIER_BUDGET_DSV4P_NV` (或改 130, R799 值, 留 margin 给慢成功 max 108s).
2. compose 删 `NVU_TIER_BUDGET_GLM5_2_NV` (回退全局 180s).
3. compose `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv` (移除 dsv4p_nv, 恢复 peer-fb rescue).
4. `NVU_EMPTY_200_FASTBREAK` 可留 1 (无害, surge 时仍省时间).
5. upstream.py/handlers.py 源码改动保留 (无 env 时回退全局, 等价原行为).

## 跨机协作备注

- R797-R801 共享源码 (upstream.py/handlers.py) + env, HM2 已部署+仓库同步. HM1 同 NVCF 上游同坏, 远程 CC pull 后请部署 HM1:
  - 源码: `deploy_artifacts/R797_glm52_fast_fail/{upstream.py,handlers.py}` → `/opt/cc-infra/proxy/nv-gw/gateway/`.
  - compose env: 加 4 行 (NVU_TIER_BUDGET_GLM5_2_NV=70, NVU_TIER_BUDGET_DSV4P_NV=70, NVU_EMPTY_200_FASTBREAK=1, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv).
  - `docker compose up -d nv_gw`.
- 远程 CC 已有 R797-R807 的 NOP round (HM2→HM1 方向), 本系列 R797-R804 文件名带后缀区分不冲突.
