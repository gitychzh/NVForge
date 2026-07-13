# HM2 Optimize HM1 — Round R1251

## 类型：NOP (false trigger, 已有数据无优化空间)

## 触发分析

- cron 脚本输出: "这是我提交的, 不触发" — 自提交误触发
- HM2 latest commit: a233350 (R1250, opc2_uname)
- HM1 git log: R1206 (45 rounds behind), last HM1-authored commit: 7625e14 (R818, 2026-07-08)
- 判定: false trigger — HM1 未提交任何新内容

## 6h 数据 (HM1, 2026-07-13 15:35 UTC)

### 总体
- 104req/83OK/21fail = 79.8% SR
- nv_integrate: 92req/75OK/17fail (81.5% SR), avg_dur 18415ms, max 86107ms
- nvcf_pexec: 9req/8OK/1fail (88.9% SR), avg_dur 45961ms, max 137213ms
- NULL (ATE): 3req/0OK/3fail

### 按模型
- glm5_2_nv: 100req/79OK/21fail = 79.0% SR, avg_dur 20109ms, max 137213ms
- dsv4p_nv: 4req/4OK = 100% SR, avg_dur 28308ms

### 错误分类
- zombie_empty_completion: 17 (glm5_2_nv integrate, NVCF content-filter stop+12chars, input_chars 168-175K, 3-28s abort)
- all_tiers_exhausted: 3 (NULL upstream, ATE)
- NVStream_IncompleteRead: 1 (glm5_2_nv integrate, 24019ms)

### Fallback
- fallback_occurred=false: 104/104 (0 fallback triggered)
- FALLBACK_GRAPH={} (expected post-R832)
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — expected

### ms_gw
- ms_requests 6h: 6req/0OK (DB trap — status='200'=0)
- ms_gw logs: MS-STREAM-DONE working (ZHIPUAI/GLM-5.2, 23703-49080b)
- ms_gw config: EMPTY_200_FASTBREAK_THRESHOLD=3 (floor), MIN_OUTBOUND_INTERVAL_S=1.0 (floor), all optimal

### Tier Attempts
- glm5_2_nv IntegrateTimeout: 2, avg 90804ms, max 91140ms

### Hourly SR
| Hour | Total | OK | Fail | SR% |
|------|-------|----|------|-----|
| 09:00 | 7 | 7 | 0 | 100.0 |
| 10:00 | 42 | 33 | 9 | 78.6 |
| 11:00 | 8 | 6 | 2 | 75.0 |
| 12:00 | 27 | 22 | 5 | 81.5 |
| 13:00 | 6 | 5 | 1 | 83.3 |
| 14:00 | 8 | 6 | 2 | 75.0 |
| 15:00 | 6 | 4 | 2 | 66.7 |

### Container
- Restarted: 2026-07-13 14:33 UTC (~1h ago)
- compose md5: 6e23559de1376d2d638f98f34a544139 (unchanged from prior rounds)

## HM1 当前参数 (nv_gw env)
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=210
- TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=72
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_MS_GW_FALLBACK_TIMEOUT=200
- NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS=(empty)
- FALLBACK_HEALTH_THRESHOLD=0.05 (dead param)
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- MIN_OUTBOUND_INTERVAL_S=0
- NV_INTEGRATE_KEY_COOLDOWN_S=0
- NVU_CONNECT_RESERVE_S=0
- NVU_FORCE_STREAM_UPGRADE=0
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66

## 决策: NOP — 零参数变更

### 分析
1. **全部 21 个失败均为 code-level**：17 zombie_empty_completion (NVCF content-filter，网关正确检测+快速中止)，3 ATE (NVCF 上游)，1 IncompleteRead (网络瞬断)。无一可通过 config 修复。
2. **所有参数均处于 floor/optimal**：UPSTREAM=66, BUDGET=210, FASTBREAK=1/2, COOLDOWN=15/25, 无不合理值。
3. **ms_gw 健康**：MS-STREAM-DONE 正常，EMPTY_200_FASTBREAK_THRESHOLD=3 (floor)。ms_requests DB 6req/0OK 是已知 DB trap（ms_gw 不写 DB）。
4. **dsv4p_nv 100% SR** (4/4)，无流量问题。
5. **compose md5 未变**，无容器重启触发的配置变更。
6. **0 fallback triggers** — FALLBACK_GRAPH={} 是 R832 设计预期，ms_gw 同模型 fallback 未触发（无 ATE 触发 ms_gw 路径）。
7. **零优化空间** — 所有可调参数已达 floor，所有失败归因于 NVCF 上游/content-filter。

### 铁律
- 只改 HM1，不改 HM2 ✅
- 改前必有数据 ✅
- 无 config-fixable 瓶颈 → 零变更 ✅

## ⏳ 轮到HM1优化HM2
