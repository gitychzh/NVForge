# HM2 Optimize HM1 — Round R1254

## 类型：NOP (zombie code-level, pre-restart ATE, IncompleteRead, 82.6% SR — all code-level failures)

## 触发分析

- HM1 cron 脚本检测到 HM1 提交了新 commit (R1253) → 触发 HM2 执行优化
- HM1 git HEAD: 0795902 (R1253: HM2→HM1 — NOP)

## 6h 数据 (HM1, 2026-07-14 ~00:20 UTC)

### 总体
- 86req/71OK/15fail = 82.6% SR (↑ 从 R1253 的 77.4% — 窗口前移，zombie 从 17 降至 11)
- 按模型:
  - glm5_2_nv: 85req/70OK/15fail = 82.4% SR
  - dsv4p_nv: 1req/1OK = 100% SR

### 按路径
- nv_integrate: 79req/67OK/12fail, avg_ttfb=13109ms, avg_dur=14901ms, max_dur=45191ms
- nvcf_pexec: 4req/4OK/0fail, avg_ttfb=24938ms, avg_dur=24939ms, max_dur=45950ms
- (NULL upstream): 3req/0OK/3fail, avg_dur=5449ms

### 延迟
- 成功请求 duration 分布:
  - <5s: 2, 5-10s: 25, 10-15s: 19, 15-20s: 8, 20-25s: 6
  - 25-30s: 2, 30-35s: 3, 35-40s: 2, 40-50s: 4
- 成功请求全部在 50s 以内，无异常延迟

### 错误分类
- zombie_empty_completion: 11 (glm5_2_nv integrate, NVCF content-filter stop+12chars, 11-28s range)
- all_tiers_exhausted: 3 (NULL upstream, 0 tier_attempts, avg 5449ms — pre-restart NVCF degradation)
- NVStream_IncompleteRead: 1 (glm5_2_nv integrate, 24019ms)

### Post-restart only (2026-07-13 14:33:57+ UTC)
- 11req/7OK/4fail = 63.6% SR (与 R1253 完全相同)
- 3 zombie_empty_completion (11244ms, 14087ms, 27673ms)
- 1 NVStream_IncompleteRead (24019ms)
- 0 all_tiers_exhausted — 确认 pre-restart 3 ATE 是旧容器状态

### 1h only (2026-07-14 00:05+ UTC)
- 6req/4OK/2fail = 66.7% SR
- 2 zombie (14087ms, 27673ms)

### Tier Attempts
- **0 rows** — zombie detection 发生在 key 循环之前（单 key 即中止），nv_tier_attempts 无记录
- 此行为符合 R1107 预期：zombie_empty_completion 是单 key 快速中止，不触发 key 循环

### Fallback
- fallback_occurred=false: 86/86
- fallback_actually_attempted=false: 86/86
- 0 fallback 触发 — FALLBACK_GRAPH={} (R832 预期)
- ms_gw fallback 未触发: zombie 路径在 stream abort 处理，在 ATE 之前
- ms_gw 日志: MS-STREAM-DONE 正常，MS-OK-STREAM 正常，ZHIPUAI/GLM-5.2 后端响应正常

### Hourly SR
- 10:00 UTC: 28req/26OK/2fail = 92.9%
- 11:00 UTC: 8req/6OK/2fail = 75.0%
- 12:00 UTC: 27req/22OK/5fail = 81.5%
- 13:00 UTC: 6req/5OK/1fail = 83.3%
- 14:00 UTC: 8req/6OK/2fail = 75.0%
- 15:00 UTC: 6req/4OK/2fail = 66.7%
- 16:00 UTC: 3req/2OK/1fail = 66.7%

### 容器
- nv_gw: Up 2h (restarted 2026-07-13 14:33:57 UTC)
- ms_gw: Up (MS-STREAM-DONE 正常)
- nv_gw compose md5: 6e23559de1376d2d638f98f34a544139 (与 R1253 相同)
- 所有容器 healthy

## HM1 当前参数 (nv_gw env)

与 R1253 完全相同，compose md5 未变：

- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=210
- TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=72
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_MS_GW_FALLBACK_TIMEOUT=200
- NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS=(empty)
- MIN_OUTBOUND_INTERVAL_S=0
- NV_INTEGRATE_KEY_COOLDOWN_S=0
- NVU_CONNECT_RESERVE_S=0
- NVU_FORCE_STREAM_UPGRADE=0
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90
- NVU_STREAM_TOTAL_DEADLINE_S=42
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
- NVU_SSLEOF_RETRY_DELAY_S=1.0
- NV_INTEGRATE_MODELS=glm5_2_nv
- NV_KEY_INTEGRATE_KEYS=minimax_m3_nv:5
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- FALLBACK_HEALTH_THRESHOLD=0.05 (dead param — R919)
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
- NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
- NVU_PEER_FALLBACK_ENABLED=1

## 决策: NOP — 零参数变更

### 分析
1. **全部 15 个失败均为 code-level**：
   - 11 zombie_empty_completion (73%): NVCF glm5_2_nv integrate 对大 context (109-177K chars) 返回 content-filter stop+12chars。网关正确检测 finish_reason=stop + content_chars < 50 + input_chars >= 5000 → 判定 zombie → 发送 content_filter error SSE chunk → openclaw 走 model-fallback。11-28s 快速中止优于旧 96s hang。**R1107 确认：code-level feature，不可 config 修复**。
   - 3 all_tiers_exhausted (20%): 全部 pre-restart (12:33-12:39 UTC)，upstream_type=NULL，0 tier_attempts，avg 5449ms。Post-restart 零 ATE。**R1241 模式的 404/not found NVCF 函数退化，不可 config 修复**。
   - 1 NVStream_IncompleteRead (7%): 24,019ms。TCP 层面流中断，不可 config 修复。

2. **所有参数均处于 floor/optimal**：无异常值，无优化空间。UPSTREAM=66 成功路径全部在 50s 内完成，未绑定。BUDGET=210 远大于实际需求。FASTBREAK=1 已在地板。NVU_MS_GW_FALLBACK_TIMEOUT=200 已慷慨。

3. **zombie 检测正确工作**：网关实时检测 zombie → 发送 error SSE chunk → openclaw 触发 model-fallback 链。这是符合预期的行为路径，NVCF 上游 content-filter 行为不可通过 config 调整。

4. **ms_gw 健康**：MS-STREAM-DONE 正常，MS-OK-STREAM 正常，ZHIPUAI/GLM-5.2 后端响应正常。nv_gw 不主动触发 ms_gw fallback 因为 zombie 路径在 stream abort 阶段处理，不会进入 ATE→ms_gw 路径。

5. **dsv4p_nv 100% SR** (1/1)，无流量问题。

6. **0 fallback triggers** — 预期行为（FALLBACK_GRAPH={}，NV-MS-FB 仅在 ATE 时触发，但 zombie 在 ATE 前由 stream abort 处理）。

7. **连续 9 轮 NOP (R1246-1254)**，所有可调参数已达 floor/optimal，所有失败归因于 NVCF 上游/content-filter/网络瞬断，非 config 可调。

8. **6h SR 82.6% vs R1253 77.4%**：纯粹是窗口前移效果 — zombie 计数从 17 降至 11（窗口中 zombie 密度变化）。Post-restart SR 63.6% 与 R1253 完全相同，证实系统状态未变。

### 铁律
- 只改 HM1，不改 HM2 ✅
- 改前必有数据 ✅
- 无 config-fixable 瓶颈 → 零变更 ✅
- 所有修改写入仓库 ✅

## ⏳ 轮到HM1优化HM2