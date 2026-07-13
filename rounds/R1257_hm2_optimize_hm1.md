# HM2 Optimize HM1 — Round R1257

## 1. 触发分析
- **Cron 脚本输出**: `"这是我提交的, 不触发"` — FALSE TRIGGER (HM1 自提交 R1256)
- **最新 commit**: `46acf77` — R1256 (HM2: opc2_uname, NOP)
- **触发类型**: Double-dispatch. R1256 已由 HM2 提交, symlink 已正确指向 R1256. Cron 再次派遣.
- **判定**: NOP (false trigger, 数据与 R1256 一致)

## 2. 数据收集 (改前必有数据)
### 6h 总体
- 61req/47OK/14fail = 77.0% SR
- 10 zombie_empty_completion + 3 all_tiers_exhausted + 1 NVStream_IncompleteRead

### 按路径
- nv_integrate: 54req/43OK/11err, avg 15,859ms
- nvcf_pexec: 4req/4OK, avg 24,939ms
- NULL (ATE): 3req/3err, avg 5,449ms

### zombie 详情
- 10 zombie_empty_completion, all glm5_2_nv integrate, all fallback_occurred=f
- avg duration 15,098ms (range 4,778–37,413ms), avg input 156,600 chars
- NVCF content_filter: finish_reason=stop, content_chars=12 < 50
- gateway 正确检测: NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK → openclaw fallback
- 每~30min 一个 zombie (z-ai/glm-5.2 integrate 模式慢性缺陷)

### ATE 详情
- 3 all_tiers_exhausted, avg 5,449ms (快速 ATE, 非超时)
- 特点: tiers_tried_count=1, fallback_occurred=f — 快速耗尽, 疑似 404 NONCYCLE 路径

### IncompleteRead
- 1 NVStream_IncompleteRead: 24,018ms, 1,204 bytes read

### ms_gw
- MS-STREAM-DONE 正常 for glm5_2_ms (log-only mode, DB 无 ms_requests 数据)

### 容器状态
- 启动: 2026-07-13T14:33:57Z (10h+)
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — R832预期状态
- compose md5: 6e23559de1376d2d638f98f34a544139

## 3. 分析
所有14个失败均为代码级:
- 10 zombie_empty_completion: NVCF content-filter stop, gateway 正确检测/abort, 非配置参数可修复
- 3 all_tiers_exhausted: 4.9% ATE率, 快速失败 (avg 5.4s), fallback_occurred=f — 疑似 404 NONCYCLE 或 NVCF 侧快速拒绝, 非配置参数可修复
- 1 NVStream_IncompleteRead: 网络/上游截断, 非配置参数可修复

nv_gw 日志确认: 全部 integrate 请求成功(9.2s–44.5s), zombie 均发生在流式完成后检测到 content_filter 截断. 无 NV-ATE 触发(仅 zombie 和 IncompleteRead 的 ERR 标记). 无 peer-fb 或 ms_gw 内部 fallback 触发.

## 4. 参数状态
所有参数已在 floor/optimal:
- UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, FASTBREAK=1 (integrate), FASTBREAK=2 (empty_200, pexec)
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
- 所有失败均为代码级 (zombie NVCF content_filter, 快速 ATE, IncompleteRead)
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2