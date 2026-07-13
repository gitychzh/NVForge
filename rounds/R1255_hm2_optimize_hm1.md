# HM2 Optimize HM1 — Round R1255

## 类型：NOP (false trigger, double-dispatch, data identical to R1254, all code-level failures)

## 触发分析

- 预运行脚本输出: `"这是我提交的, 不触发"` — 最新 commit author = opc2_uname (HM2)
- HM2 git HEAD: 4a2bef9 (R1254: HM2→HM1 — NOP)
- HM1 git HEAD: de04120 (R1206 — 49 rounds behind HM2)
- 确认: false trigger, double-dispatch of R1254
- Symlink 已指向 R1254，无需创建新 round 文件但 cron 仍派遣 → 创建 R1255

## 6h 数据 (HM1, 2026-07-14 ~00:30 UTC, fresh collect)

### 总体
- 79req/65OK/14fail = 82.3% SR (vs R1254: 86/71/15 = 82.6% — 基本一致)
- 按模型:
  - glm5_2_nv: 78req/64OK/14fail = 82.1% SR
  - dsv4p_nv: 1req/1OK = 100% SR

### 按路径
- nv_integrate: 72req/61OK/11fail, avg_ttfb=13078ms, avg_dur=14754ms, max_dur=45191ms
- nvcf_pexec: 4req/4OK/0fail, avg_ttfb=24938ms, avg_dur=24939ms, max_dur=45950ms
- (NULL upstream): 3req/0OK/3fail, avg_dur=5449ms

### 延迟分布 (成功请求)
- <5s: 1, 5-10s: 25, 10-15s: 18, 15-20s: 7, 20-25s: 5
- 25-30s: 1, 30-40s: 4, 40-50s: 4
- 全部在 50s 以内

### 错误分类
- zombie_empty_completion: 10 (glm5_2_nv integrate, NVCF content-filter stop+12chars, 1.7-17.7K chars input)
- all_tiers_exhausted: 3 (NULL upstream, 0 tier_attempts, avg 5449ms — pre-restart NVCF degradation)
- NVStream_IncompleteRead: 1 (glm5_2_nv integrate, 24019ms)

### Hourly SR
- 10:00 UTC: 21req/20OK/1fail = 95.2%
- 11:00 UTC: 8req/6OK/2fail = 75.0%
- 12:00 UTC: 27req/22OK/5fail = 81.5%
- 13:00 UTC: 6req/5OK/1fail = 83.3%
- 14:00 UTC: 8req/6OK/2fail = 75.0%
- 15:00 UTC: 6req/4OK/2fail = 66.7%
- 16:00 UTC: 3req/2OK/1fail = 66.7%

### 1h only
- 5req/3OK/2fail = 60.0% SR
- 2 zombie (14087ms, 27673ms)

### Tier Attempts
- **0 rows** — zombie detection 发生在 key 循环之前

### Fallback
- fallback_occurred=false: 79/79
- 0 fallback 触发

### 容器
- nv_gw: Up 2h (restarted 2026-07-13 14:33:57 UTC)
- ms_gw: Up (MS-STREAM-DONE 正常)
- compose md5: 6e23559de1376d2d638f98f34a544139 (与 R1254 相同)

### nv_gw 日志
- NV-ZOMBIE-EMPTY: 4 次检测 (最新: 00:04 UTC, 177300 chars, 12 chars content, 14087ms)
- NV-ZOMBIE-ERROR-CHUNK: 正确发送 content_filter error SSE chunk
- NV-REQ: glm5_2_nv start_tier=glm5_2_nv, stream=True, tier_chain=['glm5_2_nv'] (no fallback, 3model)
- 1 NV stream IncompleteRead (23:04 UTC, 24018ms)

## HM1 当前参数 (nv_gw env)

与 R1254 完全相同，compose md5 未变:
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=210, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_MS_GW_FALLBACK_TIMEOUT=200, NVU_PEER_FALLBACK_TIMEOUT=66, NVU_PEER_FB_SKIP_MODELS=(empty)
- MIN_OUTBOUND_INTERVAL_S=0, NV_INTEGRATE_KEY_COOLDOWN_S=0, NVU_CONNECT_RESERVE_S=0
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90, NVU_STREAM_TOTAL_DEADLINE_S=42
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=20, NVU_SSLEOF_RETRY_DELAY_S=1.0
- NV_INTEGRATE_MODELS=glm5_2_nv, NV_KEY_INTEGRATE_KEYS=minimax_m3_nv:5
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05, KEY_AUTHFAIL_COOLDOWN_S=60
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
- NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006, NVU_PEER_FALLBACK_ENABLED=1

## 决策: NOP — 零参数变更

### 分析
1. **全部 14 个失败均为 code-level**：
   - 10 zombie_empty_completion (71%): NVCF glm5_2_nv integrate content-filter stop+12chars。网关正确检测 zombie → 发送 content_filter error SSE chunk → openclaw 走 model-fallback。这是 code-level feature，不可 config 修复。
   - 3 all_tiers_exhausted (21%): 全部 NULL upstream + 0 tier_attempts，avg 5449ms。NVCF 函数退化（404/not found），不可 config 修复。
   - 1 NVStream_IncompleteRead (7%): TCP 流中断，不可 config 修复。

2. **数据与 R1254 基本一致**：79req/65OK/14fail (82.3%) vs R1254 86req/71OK/15fail (82.6%)。同一 compose md5，同一容器重启时间，同一错误模式。系统状态未变化。

3. **所有参数均处于 floor/optimal**：UPSTREAM=66 成功路径全部在 50s 内完成。FASTBREAK=1 已在地板。BUDGET=210 远大于实际需求。无 tunable knob 可以改善 zombie 或 NVCF 函数退化。

4. **ms_gw 健康**：MS-STREAM-DONE 正常，MS-OK-STREAM 正常，ZHIPUAI/GLM-5.2 后端响应正常。

5. **dsv4p_nv 100% SR** (1/1)，无流量问题。

6. **连续 10 轮 NOP (R1246-1255)**，所有可调参数已达 floor/optimal，所有失败归因于 NVCF 上游/content-filter/网络瞬断，非 config 可调。

### 铁律
- 只改 HM1，不改 HM2 ✅
- 改前必有数据 ✅
- 无 config-fixable 瓶颈 → 零变更 ✅
- 所有修改写入仓库 ✅

## ⏳ 轮到HM1优化HM2
