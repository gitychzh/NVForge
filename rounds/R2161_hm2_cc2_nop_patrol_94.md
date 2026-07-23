# R2161 (hm2_cc2): NOP 巡检轮 94 — 三阈值冻结, 0 改动 0 restart

## 数据 (HM2, 30min window, 改前必有数据)

### nv_gw 30min by model/status
- **glm5_2_nv**: 62 OK / 63 total → **98.4%** (1 错 = zombie_empty_completion)
- **kimi_nv**: 13 OK / 20 total → **65.0%** (7 错 = 6 ATE + 1 zombie)
- 合计: 75 OK / 84 total → **SR 89.3%**

### error_type 30min
- glm5_2_nv: 1 zombie_empty_completion
- kimi_nv: 6 all_tiers_exhausted + 1 zombie_empty_completion
- 无 content_filter / timeout / conn / 429 (429 在 tier 层不在 nv_requests 层)
- host_machine 全 HM2 本域

### kimi_nv 6h hourly 趋势 (判断单点 vs 趋势)
| 时点 | total | ok | SR |
|------|-------|----|----|
| 07:00 | 38 | 31 | 81.6% |
| 08:00 | 28 | 23 | 82.1% |
| 09:00 | 71 | 46 | 64.8% (谷) |
| 10:00 | 60 | 52 | 86.7% (恢复) |
| 11:00 | 21 | 13 | 61.9% (当前小样本) |

**结论**: kimi_nv **振荡型非单调恶化** — 09:00 谷 64.8% 恢复到 10:00 86.7%, 当前 11:00 又谷(小样本 21 req). 是 R2286 改默认模型过渡期已知特征, 非趋势性恶化. 与 STATE "若 kimi zombie/ATE 回升 ≥5/30min 且连续 2-3 轮才评估" 对比: 本轮单窗口 7 错是单点, 非连续多轮.

### kimi_nv 6h error_type
- all_tiers_exhausted 28 / zombie_empty_completion 23 / NVStream_IncompleteRead 1 / stream_absolute_cap 1
- 全 NVCF 上游连接类, 非旋钮能治

### glm5_2_nv 6h (对照, 本域主链路)
- 647 OK / 659 total → **98.2%** 极稳 (配置的 nv_default_model, 主链路稳态)

### cc4101 30min fallback (负向核心指标)
- **fallback = 0** ✅ 零数据空洞, 0 真中断, 0 双失败, 连续多轮最佳延续

### nv_gw BREAKER-FAIL 30min (R1719 设计)
- nv_gw 日志 grep BREAKER/ANTH-BREAKER = **1 条** (远未到 OPEN 阈值)
- nv_tier_attempts 30min: pexec_success 50 / pexec_429 5 / NVCFPexecRemoteDisconnected 2 / empty_200 2 / pexec_empty_200 2 — 全 NVCF 上游连接类

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **28 / 6h** (vs R2160=29, 基本持平, R2289 副作用受益持续)
- timeout = 164/6h (cc4101 自身非本域)
- server_5xx = 6 / stream_total_deadline = 1
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非 nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

### 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], **default=glm5_2_nv**)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2160 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0, 与 R2160 一致)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2160 逐项一致, **无参数漂移**
- docker ps 全栈 Up (nv_gw 20h / cc4101 4h / ms_gw 47h / logs_db 6d)

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪 — zombie body 不普遍含非标字段). 本轮 30min kimi 1 zombie 属单点, 未触发新增 dump
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 30min kimi zombie=1, 6h kimi zombie=23 但分散非连续多轮 ≥5 窗口, 素材不充分, 未实施. 是下一推进点.

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值**全不满足**:
1. SR 89.3% > 85% ✅ (kimi 单独 65% 但被 glm5_2_nv 98.4% 拉起, 总体稳)
2. cc4101 fallback 请求数 0 < 5 ✅ (零数据空洞 0 真中断)
3. 无新增错误类型 ✅ (glm5_2_nv 1 zombie 历史多轮已现; kimi 6 ATE + 1 zombie 是 R2286 过渡期已知非旋钮可治上游类, 振荡非持续上升)

四重佐证 nv_gw 稳:
1. 9 错全上游无害类 (glm5_2_nv 1 zombie + kimi 6 ATE + 1 zombie, 全 NVCF 上游连接类)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (30min 1 条, 远未 OPEN 阈值)
4. 参数无漂移 (容器未重建, env 与 R2160 逐项一致)

改了反而破坏稳定带. kimi_nv 过渡期振荡是 NVCF 上游问题, 改 nv_gw 旋钮治不了反而可能误伤 glm5_2_nv 主链路.

## 验证
0 改动 0 restart 无需验证改动.
- curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移
- 容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z

## 本轮摘要
R2161 hm2_cc2 NOP 巡检轮 94, 连续第 94 NOP, 0 改动 0 restart. 30min 84req/89.3% SR (glm5_2_nv 62/63=98.4% 极稳 1错zombie; kimi_nv 13/20=65.0% R2286过渡期振荡 7错=6ATE+1zombie 非趋势 6h hourly 62-87%振荡型). cc4101 fallback=0 零数据空洞连续多轮最佳. NV-ANTH-BREAKER-FAIL 30min 1条远未OPEN. 参数误杀全0. 499=28/6h同基线R2289副作用受益持续. 容器无漂移(nv_gw StartedAt=07-22T15:10:34Z RC=0连续多轮)+env无漂移. R2192三任务: 任务1/2已落地 任务3部分kimi zombie素材不足未实施. 三阈值全不满足→冻结. HM2 only.
