# R2184 — hm2_cc2 NOP 巡检轮 (连续第 107 NOP)

> 三阈值冻结, 0 改动 0 restart. STATE.md 滞后修正(接棒时停在 R2160, 实际 git log 到 R2183 hm2_cc2 线, 以 git log + DB 重建).

## 数据 (HM2, 30min window, 05:48~06:18 CST 附近)

- **137 req / 100% SR** (200=137, 非200=0) — 主链路极稳, 比 R2183 的 101req/100% 流量更密
- by model: **glm5_2_nv 137/137 = 100%** (全本域流量, kimi_nv 0req 过渡期收尾流量全汇 glm 稳定路径连续多轮)
- error_type: 无非200错误 (nv_requests 层 0 错)
- 无 content_filter / timeout / conn / 429 / all_tiers_exhausted (在 nv_requests 层)
- host_machine 全 HM2 本域

### nv_tier_attempts 30min 错误 (上游 NVCF 连接类, 非旋钮能治)
- pexec_success 124 / pexec_429 17 / pexec_empty_200 2 / pexec_SSLEOFError 1 / pexec_conn_RemoteDisconnected 1
- pexec_429=17 (R2183 watch 项 25 → 本轮 17, 略降, NVCF 账户级配额非旋钮能治 KEY_COOLDOWN=60/MIN_OUTBOUND=10 已保守, 改大反触发更多 primary timeout 恶化)

## cc4101 30min fallback (负向核心指标)
- **真 fallback = 2** (req bbaa8a9f 05:51 + b367b814 06:11)
- 2 次全 PRIMARY-FAIL-SKIP-CIRCUIT (primary 60s timeout < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit) → ms_gw 救回 (2431ms / 1984ms)
- **0 真中断** (2 次 < 5 阈值, 全救回, 与 R2182/R2183 同 req 模式窗口边缘旧事件级)
- 持平 R2183 (fallback=1) 量级, 无恶化

## nv_gw 内部 NV-MS-FB-BREAKER (R1719 设计)
- 05:48 连续 9 req NV-MS-FB-BREAKER-OPEN (state ('OPEN',5,23)→('OPEN',5,0) 衰减), skipping nv chain serving ms_gw directly
- **06:03 后自愈回 CLOSED** (NV-MS-FB-ATTEMPT breaker=CLOSED), 4 次 all_keys_exhausted → internal ms_fb 兜底全 OK (NV-MS-FB-SERVED state=CLOSED)
- 这是 R2179-R2183 同模式设计行为 (NVCF 上游 pexec_429/empty_200 级联 → breaker OPEN → internal ms_fb 兜底 → 自愈 CLOSED), 0 冒 cc 层 (nv_requests 100% SR 不受影响)
- **NV-ANTH-BREAKER-FAIL 30min = 0 条** (健康, 与 R2182/R2183 一致)

## 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = 42 / 6h (与 R2183=42 基线持平, R2289 副作用受益持续)
- stream_total_deadline = 2 / 6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

## 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], **default=glm5_2_nv** ← R2286 改默认模型但 nv_gw nv_default_model 仍 glm5_2_nv, 过渡期双线并行)
- nv_gw RestartCount=0 StartedAt=**2026-07-23T18:05:17Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2179-R2183 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2183 逐项一致, **无参数漂移**

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪). 本轮窗口 0 zombie, 未触发新增 dump
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 0 zombie 素材严重不足窗口 (需 ≥5 才值得推进), 未实施. 是下一推进点.

## 决策: NOP 巡检不改代码. STATE 三触发改动阈值全不满足:
1. SR 100% > 85% ✅
2. cc4101 fallback 请求数 2 < 5 ✅ 且全救回 (0 真中断)
3. 无新增错误类型 ✅ (NV-MS-FB-BREAKER OPEN 是 R2179-R2183 连续多轮已知设计行为, internal ms_fb 兜底 0 冒 cc 层, 非"新增错误类型")

四重佐证 nv_gw 稳:
1. 0 错 (nv_requests 层 100% SR, tier 层错误全 NVCF 上游连接类无害)
2. 无参数误杀 (全 0)
3. breaker 不真停 OPEN (05:48 OPEN 风暴 9req 后 06:03 自愈回 CLOSED, NV-ANTH-BREAKER-FAIL=0)
4. 参数无漂移 (容器未重建 env 与 R2183 逐项一致)

改了反而破坏稳定带.

## 验证: 0 改动 0 restart 无需验证改动
- curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移
- 容器 StartedAt (docker inspect 实测): nv_gw=07-23T18:05:17Z (连续多轮未重建) / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z

HM2 only. 未 Read 任何 /tmp 文件 (上轮中断告警铁律遵守).

Co-Authored-By: Claude <noreply@anthropic.com>
