# HM2 Optimize HM1 — Round R1290

## 决策: NOP (False Trigger / Double-Dispatch — 零参数变更, 零容器重启)

### 触发分析

cron 脚本输出: `"这是我提交的, 不触发"` (HM2 opc2_uname 自提交)

- 最新 commit `d7b8324 R1289` author = opc2_uname (HM2)
- R1289 是 HM2→HM1 NOP 轮 (false trigger, double-dispatch)
- cron 再次派遣 agent — 第 4 次连续 double-dispatch (R1287→R1288→R1289→R1290)
- HM1 本地 git log 停留在 R1206 (84 轮落后 HM2) — HM1 未提交任何新内容
- 脚本正确检测到 `"这是我提交的, 不触发"` 但 cron 仍被派遣

### 数据收集 (改前必有数据 — SSH stdin pipe)

```
6h_overall: 67 req, 52 OK, 15 fail → 77.6% SR (与 R1287/R1288/R1289 完全一致)
- 12 zombie_empty_completion (glm5_2_nv integrate, ~52K input avg, ~6.2s avg_dur, ~6 output chars)
   → 非配置可修复 — NVCF 端内容过滤, gateway 检测+错误chunk正确
- 3 all_tiers_exhausted (dsv4p_nv, avg 72s, 全部 pre-restart at 18:01-18:08 UTC)
   → 当前容器重启 30min, post-restart 4 req → 3 OK (4782-5039ms) + 1 zombie (3130ms)
- 0 fallback_occurred (67/67 direct tier)
- 0 tier_attempts (zero key cycling in 6h)

6h_by_upstream: nv_integrate 54(42OK/12fail=77.8%), nvcf_pexec 10(10OK/0fail=100%), NULL 3(0OK/3fail=ATE)
6h_by_model: glm5_2_nv 54(42OK/12fail=77.8%), dsv4p_nv 13(10OK/3fail=76.9%)
6h_hourly: 6 buckets (17:00-22:00 UTC), 均匀 6-7 req/h (除 18:00 burst 36req 86.1% SR)
  - 18:00 36req/31OK/5fail=86.1% (burst, 含 3 ATE dsv4p_nv pre-restart)
  - 17:00 6req/4OK/2fail=66.7%, 19:00-22:00 各 6-7 req @ 66.7-71.4% SR
  - zombie:success pattern ≈ 1:2 (consistent across all buckets)

Post-restart (22:14 UTC → 22:44 UTC, 30min):
  - 4 req, 3 OK (4782-5039ms), 1 zombie (3130ms) → 75.0% SR
  - 3 success: glm5_2_nv integrate, avg 4905ms, 31-162 output tokens
  - 1 zombie: glm5_2_nv integrate, 3130ms, input=52025 tokens, output=6 tokens
  - 0 ATE, 0 ms_gw fallback, 0 tier cycling

Container: restart 2026-07-13T22:14:51Z (30min), nv_gw Up 30 minutes (healthy)
           → docker logs --tail 100 shows active traffic: 4× NV-INTEGRATE-SUCCESS k1-k4 (3-5s), 1× NV-ZOMBIE-EMPTY
ms_gw: healthy — glm5_2 ZHIPUAI OK (MS-STREAM-DONE ×2), dsv4p deepseek OK (MS-STREAM-DONE ×2)
       recent: 02:00-02:09 UTC ZHIPUAI 37KB, deepseek 253-372KB streams, 1 BrokenPipeError (client disconnect)

nv_gw env params: all identical to R1286/R1287/R1288/R1289 state (zero delta since R1286)
  UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, MS_GW_FALLBACK_TIMEOUT=195
  FASTBREAK: PEXEC=1, INTEGRATE=1, EMPTY_200=2
  TIER_COOLDOWN_S=15, TIER_BUDGET: dsv4p=72, glm5_2=96, minimax=100
  KEY_AUTHFAIL_COOLDOWN_S=60, CONNECT_RESERVE_S=0, FORCE_STREAM_UPGRADE=0
  PEER_FALLBACK_TIMEOUT=66, PEER_FB_SKIP_MODELS=(empty)
  MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, NV_INTEGRATE_KEY_COOLDOWN_S=0

Compose md5: 6e1b58bc70eca49e500e3034b08376d9 (stable since R1286 deploy)
```

### 决策理由

1. **False trigger**: cron 派遣基于 HM2 自提交, 非 HM1 新变更 (第 4 次连续 double-dispatch)
2. **数据与 R1287/R1288/R1289 几乎完全一致**: 67req vs 66req, 77.6% vs 77.3% SR — 无实质变化
3. **zombie 不可修复**: 12× zombie_empty_completion = NVCF glm5_2 内容过滤, gateway code-level detection 正确 → 零参数变更可修复
4. **Post-restart 仅 4 请求**: 3 OK + 1 zombie — 样本量太小, 无统计显著性, 无法评估任何参数变更效果
5. **全参数最优/floor**: R1286 已精调到 floor (UPSTREAM=66, BUDGET=205, MS_GW_FB=195), FASTBREAK=1/1/2 (R997/R1010/R1031 validated), TIER_BUDGET per-model capping, TIER_COOLDOWN=15 (R1103 revert), KEY_AUTHFAIL=60, PEER_FALLBACK_TIMEOUT=66
6. **ms_gw healthy**: dsv4p_ms (deepseek, 30s-6min streams OK), glm5_2_ms (ZHIPUAI, 2-3s OK)
7. **保守: 不改**: 所有参数已到 floor/optimal, 零优化空间 — 连续 5 轮 (R1286真实→R1287NOP→R1288NOP→R1289NOP→R1290NOP) 无新发现
8. **nvcf_pexec 完美**: 10/10=100% SR (dsv4p_nv), 零错误

### 状态快照

| 指标 | 值 | 评估 |
|------|-----|------|
| 6h SR | 77.6% (52/67) | zombie主导 (12/15=80%), 非 config-rescueable |
| Post-restart traffic | 4 req (30min) | 样本太小, 无法验证任何变化 |
| 0 fallback_occurred | 100% requests direct tier | 零 fallback 触发 = 系统安静 |
| 0 tier_attempts | 零 key cycling | 零 NVCF 超时/429/SSLEOF |
| ms_gw throughput | glm5_2 OK, dsv4p OK | 健康, MS_GW_FALLBACK_TIMEOUT=195 充分 |
| zombie_empty_completion | 12× ~3.1-12.4s abort | 非修复: NVCF content-filter, code-level detection ✓ |
| nvcf_pexec SR | 100% (10/10) | dsv4p_nv pexec perfect |
| Compose md5 | 6e1b58bc... (stable) | R1286 deploy 后未变, 连续 5 轮不变 |

**铁律**: 只改 HM1 不改 HM2 | 改前必有数据 | 改后必有验证

## ⏳ 轮到HM1优化HM2