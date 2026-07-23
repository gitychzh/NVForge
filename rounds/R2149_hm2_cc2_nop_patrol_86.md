# R2149 — hm2 NOP 巡检轮 86 (连续第 86 NOP, 三阈值冻结)

> 时间: 2026-07-23 09:12 CST
> 上一轮: R2148b (commit 338e49c, SR 91.9%, glm5_2_nv 79/80=98.75%)
> 本轮: NOP 巡检, 0 改动 0 restart

## STATE.md 滞后修正

STATE.md 头部停在 R2137 (07:12 CST 旧 session 交接), git log 实测 HEAD = 74e0c14 (R2292).
hm2_cc2 线最新 = R2148b (338e49c @07-23). STATE 滞后第 41 次. 以 git log 为准, 本轮续 R2149.

## 数据 (HM2, 30min window, 09:12 CST 时点)

**nv_gw 30min (nv_requests)**:
- 112 请求 / 103 OK(200) / 9 错(502) → 总 SR = **92.0%**
- by model:
  - **glm5_2_nv (本域主链路): 65/66 = 98.5%** (极稳, 1 错 stream_absolute_cap mid-stream 背景波)
  - kimi_nv (R2286 新默认模型过渡期): 38/44 = 86.4% (6 错 = 3 ATE + 3 zombie)
  - dsv4p_nv: 0/2 = 0% (2 ATE, NVCF 74f02205 恶化延续非本域)

**error_type 分布**:
- all_tiers_exhausted: 5 (kimi_nv 3 + dsv4p 1 + 看整体)
- zombie_empty_completion: 3 (全 kimi_nv)
- stream_absolute_cap: 1 (glm5_2_nv)

**kimi_nv 错误请求明细** (rid / 时点 / error_type):
- bcb8d7df / 08:42 / zombie_empty_completion (tiers_tried=1)
- 3a4a6fb9 / 08:42 / zombie_empty_completion (tiers_tried=1)
- 69c7ca6e / 08:48 / all_tiers_exhausted
- 62c18bb1 / 08:51 / all_tiers_exhausted
- 31d2a9bd / 08:57 / all_tiers_exhausted
- f142b5d4 / 09:04 / zombie_empty_completion
- 86af52a7 / 09:08 / zombie_empty_completion

**tier 层错误 (nv_tier_attempts 30min)**:
- pexec_success: 64 (基线健康)
- pexec_SSLEOFError: 5
- pexec_empty_200: 5
- NVCFPexecRemoteDisconnected: 4
- pexec_conn_RemoteDisconnected: 3
→ kimi_nv 6 错全是 NVCF 上游连接类 (SSL EOF / empty 200 / remote disconnect), 非 nv_gw 旋钮能治根因.
   kimi_nv 是 R2286 (2026-07-23) 改的新默认模型, 过渡期阵痛, glm5_2_nv 本域未受波及.

## cc4101 fallback (负向核心指标)

- **30min fallback = 0** ✅ 零数据空洞, 0 真中断
- 连续多轮 fallback=0 / 全救回 最佳状态延续

## BUG-A 499 盲点 (cc_requests 6h)

- client_gone_mid_stream = **31 / 6h** (较 R2137 基线 50 降 38%, R2289 改默认模型 + 1M→120K settings 副作用受益持续)
- stream_total_deadline = 3/6h, server_5xx = 6/6h, timeout = 164/6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

## 容器状态 (漂移信号核)

- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
  - ⚠ 注意: /health 报 nv_default_model=glm5_2_nv, 但 R2292 commit 说 "hermes+openclaw 默认模型改 kimi_nv".
    nv_gw config 层 default 仍是 glm5_2_nv (本域主链路稳态锚), R2292 改的是 hermes/openclaw 层而非 nv_gw config.
    本轮 DB 实测 kimi_nv 38+6=44 req/30min 确有流量, 说明上层确有在路由 kimi_nv, 但 nv_gw default 锚未动.
- nv_gw RestartCount=0 StartedAt=2026-07-22T15:10:34Z (Up 18h, 连续多轮 RC=0 未重建, 无漂移)
- cc4101 Up About an hour (R2290 改 cc4101 源码所致重启非漂移, R2147 已记)
- ms_gw Up 44h, logs_db Up 6d 全栈 Up
- env 关键参数与 R2148b 逐项一致, **无参数漂移**

## R2192 三任务进度 (巡检轮必报)

- **任务1 (cc4101 透传 cache_control)**: ✅ 已落地 (R2228), cache_read 38.8% 持续验证. 本轮未单独验证命中率, 历史多轮已证.
- **任务2 (nv_gw 抓 zombie body dump probe)**: ✅ 已落地 (27 sample all_ABSENT, hypothesis A 强证伪). 本轮 kimi_nv 有 3 zombie 素材, 但 probe 已落地+证伪, 无需重复.
- **任务3 (路径B zombie 内部重试)**: ⏳ 部分. _ms_fallback_request 存在, 但 zombie 检测点 "200+message_start 已发→不能切 ms 重放" 双 message_start 约束未解. 需设计 converter feed_chunk 内部重试 (不双 message_start, 内容重复用户接受). 仍未做.

## 决策: NOP 巡检不改代码

STATE 三触发改动阈值全不满足:
- 30min 总 SR 92.0% > 85% ✅ (glm5_2_nv 本域 98.5% 极稳)
- cc4101 fallback 请求数 0 < 5 ✅ (零数据空洞连续多轮最佳)
- 无新增 nv_gw 旋钮能治的错误类型 ✅
  (kimi_nv 6 错全 NVCF 上游连接类 SSLEOFError/empty_200/RemoteDisconnected, 是 R2286 改默认模型过渡期阵痛非本域新错; glm5_2_nv 本域 1 错 stream_absolute_cap 历史多轮已现 mid-stream 背景波)

四重佐证 nv_gw 稳:
1. glm5_2_nv 本域 65/66=98.5% 极稳 (主链路满分稳态延续)
2. cc4101 fallback=0 零数据空洞 (连续多轮最佳)
3. 容器无漂移 (nv_gw Up 18h RC=0 连续未重建, env 与 R2148b 逐项一致)
4. 参数误杀类全 0 (无 75s_timeout/STREAM-STALL/BIG-INPUT/UPSTREAM-ERROR-SEEN/client_gone 误杀)

kimi_nv 6 错是 R2286 改默认模型过渡期阵痛, 非 nv_gw 旋钮能治根因 (NVCF 上游连接类), 改 nv_gw 旋钮无效反而破坏 glm5_2_nv 本域稳态. 冻结.

## 验证

0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
nv_gw StartedAt=2026-07-22T15:10:34Z (Up 18h, 连续多轮未重建). commit 后 push.

## 铁律遵守

- 改前有数据 ✅ (30min window + tier + fallback + 499 全拉)
- 改后有验证 ✅ (0 改动, 健康检查通过)
- 聚焦 40006 ✅ (不碰 ms_gw 源码)
- 写入仓库 ✅ (本轮文件 + commit push)
- 只改 HM2 不改 HM1 ✅
- R2291/R2292 (HM2->HM1 peer 轮) 不参与, 保持 HM2 稳态
