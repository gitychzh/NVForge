# HM2 Optimize HM1 — Round R1289

## 决策: NOP (False Trigger / Double-Dispatch — 零参数变更, 零容器重启)

### 触发分析

cron 脚本输出: `"这是我提交的, 不触发"` (HM2 opc2_uname 自提交)

- 最新 commit `1c9ddc0 R1288` author = opc2_uname (HM2)
- R1288 是 HM2→HM1 NOP 轮 (false trigger, double-dispatch)
- cron 再次派遣 agent — false trigger / double-dispatch (R1287→R1288→R1289 连续 3 轮)
- HM1 本地 git log 停留在 R1206 (83 轮落后 HM2) — HM1 未提交任何新内容
- 脚本正确检测到 `"这是我提交的, 不触发"` 但 cron 仍被派遣

### 数据收集 (改前必有数据 — SSH stdin pipe)

```
6h_overall: 67 req, 52 OK, 15 fail → 77.6% SR (vs R1288: 66req/51OK/15fail=77.3%, 几乎一致)
- 12 zombie_empty_completion (glm5_2_nv integrate, ~205K input avg, ~6.2s avg_dur, ~12 output chars)
   → 非配置可修复 — NVCF 端内容过滤, gateway 检测+错误chunk正确
- 3 all_tiers_exhausted (dsv4p_nv, avg 72s, 全部 pre-restart, 旧容器)
   → 当前容器重启 21min, 零 post-restart 流量 → 无新行为可评估
- 0 fallback_occurred (67/67 direct tier)
- 0 tier_attempts (zero key cycling in 6h)

6h_by_upstream: nv_integrate 54(42OK/12fail=77.8%), nvcf_pexec 10(10OK/0fail=100%), NULL 3(0OK/3fail=ATE)
6h_by_model: glm5_2_nv 54(42OK/12fail=77.8%), dsv4p_nv 13(10OK/3fail=76.9%)
6h_hourly: 6 buckets (17:00-22:00 UTC), 均匀 6-7 req/h (除18:00 burst 36req 86.1%)
  - 18:00 36req/31OK/5fail=86.1% (burst, 含 dsv4p_nv pexec 成功)
  - 其他 6h buckets ~66.7% SR (zombie主导, zombie:success≈1:2 pattern)

Container: restart 2026-07-13T22:14:51Z (21min), nv_gw Up 21 minutes (healthy)
           → 零 post-restart 流量 (docker logs --tail 100 仅 startup + health checks)
ms_gw: healthy — glm5_2 ZHIPUAI OK (MS-STREAM-DONE ×8), dsv4p deepseek OK (MS-STREAM-DONE ×3)
       recent: 02:00 ZHIPUAI 37KB, 02:02-02:09 deepseek 253-372KB streams

nv_gw env params: all identical to R1286/R1287/R1288 state (zero delta since R1286)
  UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, MS_GW_FALLBACK_TIMEOUT=195
  FASTBREAK: PEXEC=1, INTEGRATE=1, EMPTY_200=2
  TIER_COOLDOWN_S=15, TIER_BUDGET: dsv4p=72, glm5_2=96, minimax=100
  KEY_AUTHFAIL_COOLDOWN_S=60, CONNECT_RESERVE_S=0, FORCE_STREAM_UPGRADE=0
  PEER_FALLBACK_TIMEOUT=66, PEER_FB_SKIP_MODELS=(empty)
  MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, NV_INTEGRATE_KEY_COOLDOWN_S=0

Compose md5: 6e1b58bc70eca49e500e3034b08376d9 (stable since R1286 deploy)
```

### 决策理由

1. **False trigger**: cron 派遣基于 HM2 自提交, 非 HM1 新变更 (第 3 次连续 double-dispatch)
2. **数据与 R1287/R1288 几乎完全一致**: 67req vs 66req, 77.6% vs 77.3% SR — 无实质变化
3. **zombie 不可修复**: 12× zombie_empty_completion = NVCF glm5_2 内容过滤, gateway code-level detection 正确 → 零参数变更可修复
4. **0 post-restart traffic**: 容器仅重启 21min (仅比 R1288 多 3min), 无可评估新行为 → 修改参数是盲猜, 违反改前必有数据
5. **全参数最优/floor**: R1286 已精调到 floor (UPSTREAM=66, BUDGET=205, MS_GW_FB=195), FASTBREAK=1/1/2 (R997/R1010/R1031 validated), TIER_BUDGET per-model capping, TIER_COOLDOWN=15 (R1103 revert), KEY_AUTHFAIL=60, PEER_FALLBACK_TIMEOUT=66
6. **ms_gw healthy**: dsv4p_ms (deepseek, 30s-6min streams OK), glm5_2_ms (ZHIPUAI, 2-3s OK)
7. **保守: 不改**: 所有参数已到 floor/optimal, 无优化空间 — 连续 4 轮 (R1286真实→R1287NOP→R1288NOP→R1289NOP) 无新发现

### 状态快照

| 指标 | 值 | 评估 |
|------|-----|------|
| 6h SR | 77.6% (52/67) | zombie主导 (12/15=80%), 非 config-rescueable |
| Post-restart traffic | 0 (21min) | 无法验证任何变化 |
| 0 fallback_occurred | 100% requests direct tier | 零 fallback 触发 = 系统安静 |
| 0 tier_attempts | 零 key cycling | 零 NVCF 超时/429/SSLEOF |
| ms_gw throughput | glm5_2 OK, dsv4p OK | 健康, MS_GW_FALLBACK_TIMEOUT=195 充分 |
| zombie_empty_completion | 12× ~4.7-5.4s fast abort | 非修复: NVCF content-filter, code-level detection ✓ |
| nvcf_pexec SR | 100% (10/10) | dsv4p_nv pexec perfect |
| Compose md5 | 6e1b58bc... (stable) | R1286 deploy 后未变 |

**铁律**: 只改 HM1 不改 HM2 | 改前必有数据 | 改后必有验证

## ⏳ 轮到HM1优化HM2