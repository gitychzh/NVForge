# R2182 (hm2_cc2): NOP 巡检轮 105 连续第105 NOP 三阈值冻结

> 0 改动 0 restart. HM2 only. 未 Read 任何 /tmp 文件. 三阈值全不满足 → 冻结.
> 全新 session 接棒 (STATE.md 滞后停在 R2160, 实际 git HEAD=R2306, hm2_cc2 线最新=R2181).

## 数据 (HM2, 30min window)

### nv_gw 30min 成功率 + 错误分类
- 102 req / 100 OK(200) / 2 错(502) → **SR = 98.0%**
- by model: **glm5_2_nv 100/102 = 98.0%** (全本域流量; kimi_nv 0 req 过渡期收尾流量全汇 glm 稳定路径, 连续多轮)
- error_type: **2 stream_absolute_cap** (mid-stream 背景波, 历史多轮已现上游连接类, 非旋钮能治)
- 无 content_filter / timeout / conn / 429 / all_tiers_exhausted / zombie / ATE

### cc4101 30min fallback (负向核心指标)
- **fallback = 1** (req=82ce0374, primary timeout 60067ms → ms_gw 救回 3320ms)
- < 5 阈值 ✅, 0 真中断, 救回 < 链 budget 120s
- cc4101 日志: PRIMARY-FAIL-SKIP-CIRCUIT (60s < 120s budget, cc4101 pre-empted nv_gw retry, NOT counted toward circuit) — 设计行为

### nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719 设计)
- 30min nv_gw 日志 grep BREAKER/ANTH-BREAKER = **0 条** (CLOSED 健康, 比上轮 R2181 2条更干净)
- nv_tier_attempts 30min 错误: pexec_success 89 / pexec_429 16 / pexec_conn_RemoteDisconnected 8 / pexec_504 7 / pexec_empty_200 2
  - 全 NVCF 上游连接类 (429/conn/504), tier retry 吸收, 非旋钮能治
  - 注意 fallback_occurred (nv_gw 内部 NV-MS-FB tier 兜底) ≠ cc4101 fallback. 本轮 cc4101 fallback=1.

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **42 / 6h** (与基线 R2289 副作用受益持续, 结构性限制)
- stream_total_deadline = 2 / 6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非 nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

### 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], **default=glm5_2_nv**)
- nv_gw RestartCount=0 StartedAt=**2026-07-23T18:05:17Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2181 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2181 逐项一致, **无参数漂移**

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪 — zombie body 不普遍含非标字段). 本轮窗口 kimi 0 req 无 zombie 素材
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 kimi zombie=0 素材严重不足 (需 ≥5 才值得推进), 未实施. 是下一推进点.

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
1. SR 98.0% > 85% ✅
2. cc4101 fallback 请求数 1 < 5 ✅ (0 真中断, 救回 < budget)
3. 无新增错误类型 ✅ (2 stream_absolute_cap 历史多轮已知 mid-stream 背景波)

四重佐证 nv_gw 稳:
1. 2 错全上游无害类 (glm5_2_nv 2 cap mid-stream 背景波)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (30min 0 条, CLOSED 健康)
4. 参数无漂移 (容器未重建 env 与 R2181 逐项一致)

改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=07-23T18:05:17Z (连续多轮未重建) / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z.

Co-Authored-By: Claude <noreply@anthropic.com>
