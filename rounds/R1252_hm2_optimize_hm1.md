# HM2 Optimize HM1 — Round R1252

## 类型：NOP (false trigger, 寄生虫+ATE+IncompleteRead, 79.2% SR all code-level)

## 触发分析

- cron 脚本输出: "这是我提交的, 不触发" — HM1 pull 了 HM2 的 R1251 自提交
- HM1 git HEAD: de04120 (R1206, 45 rounds behind) — 无 HM1-authored 新提交
- 判定: false trigger — HM1 未提交任何新内容；脚本检测到 HM2 自身 commit 被 HM1 pull

## 6h 数据 (HM1, 2026-07-13 23:50 UTC)

### 总体
- 101req/80OK/21fail = 79.2% SR
- 按模型:
  - glm5_2_nv: 97req/76OK/21fail = 78.4% SR
  - dsv4p_nv: 4req/4OK = 100% SR

### 延迟
- 成功: avg 20092ms, max 137213ms, min 3989ms
- glm5_2_nv OK: avg 19659ms, max 137213ms, min 3989ms
- dsv4p_nv OK: avg 28308ms, max 45950ms, min 17669ms

### 错误分类
- zombie_empty_completion: 17 (glm5_2_nv integrate, NVCF content-filter stop+12chars, input_chars 168-176K, avg 21704ms abort)
- all_tiers_exhausted: 3 (NULL upstream, 0 tier_attempts logged, avg 5449ms — fast-fail cooldown exhaustion)
- NVStream_IncompleteRead: 1 (glm5_2_nv integrate, 24019ms)

### Tier Attempts
- glm5_2_nv IntegrateTimeout: 2, avg 90804ms, max 91140ms

### Fallback
- fallback_actually_attempted=false: 98/98
- 0 fallback triggers — FALLBACK_GRAPH={} (R832 expected)
- ms_gw fallback 未触发 (无 ATE 触发 nv_gw→ms_gw 路径)

### ms_gw
- ms_requests 6h: ~6req (DB trap — ms_gw status 字段为 text 类型，不计为 200)
- ms_gw logs: MS-STREAM-DONE 正常，ZHIPUAI/GLM-5.2 后端工作正常 (23-49KB)
- ms_gw restarted at 18:04 UTC

### 容器
- nv_gw: Up ~1h (restarted 2026-07-13 14:33 UTC)
- ms_gw: Up 6h (restarted ~18:04 UTC)
- 所有容器 healthy

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
- MIN_OUTBOUND_INTERVAL_S=0
- NV_INTEGRATE_KEY_COOLDOWN_S=0
- NVU_CONNECT_RESERVE_S=0
- NVU_FORCE_STREAM_UPGRADE=0
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90
- NVU_STREAM_TOTAL_DEADLINE_S=42
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
- NVU_ZOMBIE_EMPTY_CONTENT_CHARS=50 (default)
- NVU_ZOMBIE_MIN_INPUT_CHARS=5000 (default)
- NV_INTEGRATE_MODELS=glm5_2_nv
- NV_KEY_INTEGRATE_KEYS=minimax_m3_nv:5

## 决策: NOP — 零参数变更

### 分析
1. **全部 21 个失败均为 code-level**：17 zombie_empty_completion (NVCF content-filter，网关正确检测+快速中止→error SSE chunk→openclaw fallback)，3 ATE (key cooldown 快速耗尽)，1 IncompleteRead (网络瞬断)。无一可通过 config 修复。
2. **所有参数均处于 floor/optimal**：无异常值，无优化空间。
3. **zombie 检测正确**：NVCF integrate 对 glm5_2_nv 大 context (168-176K chars) 返回 content-filter stop+12chars，网关实时检测 finish_reason=stop + content_chars < 50 + input_chars >= 5000 → 判定 zombie → 发送 content_filter error SSE chunk → openclaw 走 model-fallback 链。此行为是 NVCF 上游行为，非 config 可调。
4. **ms_gw 健康**：MS-STREAM-DONE 正常，ZHIPUAI/GLM-5.2 后端响应正常。nv_gw 不主动触发 ms_gw fallback（zombie 在 fallback 前由 stream abort 处理）。
5. **dsv4p_nv 100% SR** (4/4)，无流量问题。
6. **0 fallback triggers** — 预期行为（FALLBACK_GRAPH={}，同模型 ms_gw fallback 仅在 ATE 时触发，但 zombie 路径在 ATE 前由 stream abort 处理）。
7. **零优化空间** — 连续 7 轮 NOP (R1246-1252)，所有可调参数已达 floor，所有失败归因于 NVCF 上游/content-filter。

### 铁律
- 只改 HM1，不改 HM2 ✅
- 改前必有数据 ✅
- 无 config-fixable 瓶颈 → 零变更 ✅

## ⏳ 轮到HM1优化HM2