# R-dsv4p-adaptive: dsv4p_nv pexec→integrate 跨链路自适应兜底 + tier budget 缩短 + per-key 分流

## 摘要

dsv4p_nv 7天 SR=60% (180/293), all_tiers_exhausted 35% (103次, avg 96s). 根因: 单一 FID 74f02205 pexec 在 NVCF surge 时全 5 key 挂掉, 无 fallback 路径. 本轮新增 pexec→integrate 跨链路 fallback + k3/k4 per-key integrate 分流 + tier budget 120→60s.

## 数据 (改前)

7天 (07-30 ~ 08-04):
| 错误类型 | 次数 | avg ms | avg input chars |
|---|---|---|---|
| SUCCESS | 180 (60%) | 29,659 | 196K |
| all_tiers_exhausted | 103 (35%) | 96,176 | 229K |
| zombie_empty_completion | 9 (3%) | 20,597 | 297K |
| NVStream_IncompleteRead | 1 | 50,670 | 367K |

延迟分位: p50=22.5s, p90=59.2s, p99=103.9s

all_tiers_exhausted duration 分布:
- 60-90s: 31次 (2-3 key timeout)
- 90-110s: 36次 (3-4 key timeout)
- >120s: 28次 (budget 超限)

per-key 错误: k0 10timeout+3SSLEOF, k1 5timeout+2SSLEOF, k2 5timeout+2SSLEOF+1RemoteDisc, k3 9RemoteDisc+5SSLEOF (最差), k4 5timeout+1RemoteDisc+2SSLEOF

## 参数变更

| 参数 | 旧值 | 新值 | 理由 |
|---|---|---|---|
| NVU_TIER_BUDGET_DSV4P_NV | 120 | 60 | p90=59.2s, 60s 覆盖 p90; 失败快走 integrate fallback |
| NV_KEY_INTEGRATE_KEYS | `minimax_m3_nv:5` | `minimax_m3_nv:5;dsv4p_nv:3,4` | k3/k4 走 integrate (R838b per-key), k0/k1/k2 走 pexec |

## 代码变更

### upstream.py: pexec 全挂 → integrate 跨链路 fallback

在 execute_request 的 "All tiers exhausted" 段, 全 tier (pexec) 失败后, 对 dsv4p_nv 尝试 _try_integrate_keys 作为跨链路 fallback:
- 条件: mapped_model == "dsv4p_nv" + 非 429 (429 是 key 级限流, 跨链路不增加 key 池) + NV_INTEGRATE_ENABLED + integrate path 未冷却
- integrate 成功 → 返回成功 (标记 dsv4p_adaptive_path=integrate_fallback)
- integrate 失败 → 累加 attempts, 走原有 all_tiers_exhausted 路径
- pexec (74f02205) 和 integrate (integrate.api.nvidia.com) 是独立故障域

### handlers.py: all_tiers_exhausted 写 key_cycle_details

之前 all_tiers_exhausted 路径不写 `metrics["key_cycle_details"]`, 导致 DB nv_tier_attempts 表无失败请求的 per-key attempt 记录. 补上, 使 DB 可查.

## 部署

```bash
cd /opt/cc-infra && docker compose up -d nv_gw
```

bind-mount gateway/, 无需 rebuild. 修改了 docker-compose.yml env + upstream.py + handlers.py.

## 验证

### E2E 5请求 (dsv4p_nv)
- req1: k1 pexec 9.1s ✅
- req2: k2 pexec 9.7s ✅  
- req3: k3 integrate 18.6s ✅ (R838b per-key 分流生效)
- req4: k4 integrate 5.3s ✅
- req5: k5 pexec 21.3s ✅
- SR=5/5=100%

### 日志确认
- `[NV-R838B-LANE] tier=dsv4p_nv RR peek=k3 → integrate (per-key)` ✅
- `[NV-INTEGRATE-SUCCESS] tier=dsv4p_nv k3 succeeded` ✅
- `[NV-INTEGRATE-SUCCESS] tier=dsv4p_nv k4 succeeded` ✅

### DB 确认
- dsv4p_nv upstream_type 出现 nvcf_pexec + nv_integrate 混合 ✅
- glm5_2_nv 无回归 (仍走 MODE_CHAIN, 不受影响) ✅

## 预期效果

1. all_tiers_exhausted 从 35% → <15% (integrate fallback 覆盖 pexec surge)
2. avg exhausted duration 96s → <40s (60s budget + integrate fallback)
3. 整体 SR 60% → >80%
4. per-key 流量分流: pexec 3 key + integrate 2 key, 降低单一路径压力

## 不改的部分

- UPSTREAM_TIMEOUT=34s (覆盖 pexec 1-7s, margin 充足)
- KEY_COOLDOWN_S=25s
- config.py dsv4p_nv strip_params/inject (已验证最优)
- 不加新 FID (74f02205 是唯一 ACTIVE)
- dsv4p_nv 保留在 NVU_PEER_FB_SKIP_MODELS (peer 同 FID 同坏)
- dsv4p_nv 不加入 NVU_BIG_INPUT_MODELS (避免 cross-model breaker 污染)
