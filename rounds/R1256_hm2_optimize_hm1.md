# HM2 Optimize HM1 — Round R1256

## 1. 触发分析
- **Cron 脚本输出**: `"这是我提交的, 不触发"` — FALSE TRIGGER (HM2 自提交)
- **最新 commit**: `ae64a57` — R1255 (HM2: opc2_uname, NOP)
- **触发类型**: Double-dispatch. R1255 已由 pre-run script 提交, symlink 已正确指向 R1255. Cron 再次派遣.
- **判定**: NOP (false trigger, 数据与 R1252-R1255 一致)

## 2. 数据收集 (改前必有数据)
### 6h 总体
- 63req/49OK/14fail = 77.8% SR
- 10 zombie_empty_completion + 3 all_tiers_exhausted + 1 NVStream_IncompleteRead

### 按模型
- glm5_2_nv: 62req/48OK/14fail = 77.4% SR, avg 15,329ms (nv_integrate)
- dsv4p_nv: 1req/1OK = 100% SR, 45,950ms (nvcf_pexec)

### 按路径
- nv_integrate: 56req/45OK/11err, avg 15,719ms
- nvcf_pexec: 4req/4OK, avg 24,939ms
- NULL (ATE): 3req/3err, avg 5,449ms

### zombie 详情
- 10 zombie_empty_completion, avg 15,098ms, avg 156,600 input_chars, 7 output_tokens
- NVCF content-filter: finish_reason=stop, content_chars=12 < 50
- gateway 正确检测: NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK → openclaw fallback

### tier_attempts: 0 (zombie 在 key cycling 前检测)
### fallback: 0 occurred (FALLBACK_GRAPH={} by R832 design, ms_gw same-model fallback)
### ms_gw: 5 total/0 OK (DB trap — log-only mode, MS-STREAM-DONE 正常 for glm5_2_ms)
### 24h: 21 zombie + 14 ATE + 2 IncompleteRead

### 容器状态
- 启动: 2026-07-13T14:33:57Z (10h+)
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — R832预期状态
- compose md5: 6e23559de1376d2d638f98f34a544139

## 3. 分析
所有14个失败均为代码级:
- 10 zombie_empty_completion: NVCF content-filter stop, gateway 正确检测/abort, 非配置参数可修复
- 3 all_tiers_exhausted: 4.8% ATE率, glm5_2_nv key exhaustion, ms_gw fallback 可能未触发或快速失败 (avg 5,449ms)
- 1 NVStream_IncompleteRead: 网络/上游截断, 非配置参数可修复

## 4. 参数状态
所有参数已在 floor/optimal:
- UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, FASTBREAK=1 (integrate+pexec)
- TIER_TIMEOUT_BUDGET_S=210, NVU_MS_GW_FALLBACK_TIMEOUT=200
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90, NVU_INTEGRATE_KEY_COOLDOWN_S=0
- KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05, NVU_EMPTY_200_FASTBREAK=2
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS= (empty)
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms

## 5. 决策: NOP
- Zero param change. Zero compose edit. Zero container restart.
- 所有失败均为代码级 (zombie, IncompleteRead, minor ATE)
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
