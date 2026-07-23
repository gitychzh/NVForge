# R2180 (hm2_cc2): NOP 巡检轮 103 — 连续第 103 NOP, 三阈值冻结, 0 改动 0 restart

## 号基线
- ⚠ STATE.md 滞后修正: 接棒时 STATE.md 头部停在 R2160 (patrol 93), 但 `git log` 实测最新 hm2_cc2 = R2179 (patrol 102, commit 5d90723). 中间 R2161-R2178 共 18 轮 commit 正常但 STATE.md 未同步更新 (会话被中断在写 STATE 之前). 按 CLAUDE.md 铁律 "STATE 又被清用 git log + DB 重建", 以 git HEAD 为准. hm2_cc2 续 R2180.
- 上轮 hm2_cc2: R2179 (NOP 巡检轮 102, commit 5d90723, 连续第 102 NOP, 30min 111req/95.5% SR)
- 本轮: **R2180 — hm2_cc2 NOP 巡检轮, 0 改动 0 restart, 连续第 103 NOP**
- 轮文件: `rounds/R2180_hm2_cc2_nop_patrol_103.md`

## 数据 (HM2, 30min window)
- 总 req = 92 (nv_requests 实测 88 OK(200) + 4 错(502))
- by model: **glm5_2_nv 88/92 (status 200=88 / 502=4)** — 全本域流量; **kimi_nv 0 req** (R2286 过渡期阵痛收尾, 流量全汇 glm 稳定路径, 与 R2179 一致连续多轮)
- SR = 88/92 = **95.7%** (主链路稳, 比 R2179 95.5% 略升)
- error_type (4 错): **stream_absolute_cap 4** (无 content_filter/timeout/conn/429/zombie)
- host_machine 全 HM2 本域

## ⚠ 本轮新信号 (NV-MS-FB-BREAKER 真 OPEN ~40s 后自愈, NVCF 上游 504 压力波)

延续 R2177(风暴75) → R2178(缓解2) → R2179(1次OPEN自愈) 的 NVCF 上游压力波模式, 本轮 breaker OPEN 停留更长 (~40s) 但仍自愈回 CLOSED:

### 信号1: NV-MS-FB-BREAKER 真 OPEN ~40s 后自愈回 CLOSED
- 03:50:08.9 `NV-ANTH-BREAKER-FAIL` (glm5_2_nv anth mid-stream stream_absolute_cap 软挂) → nv_breaker recorded, state=('OPEN', 5, 29)
- 03:50:08.9 起 `NV-MS-FB-BREAKER-OPEN` 连续 8 条 (req 9f50b257/5a6e991b/d9827c37/cf180c96/076a0ecb/6dfdae73/5bc345df/e729467c), breaker 在 OPEN 状态直接 serve ms_gw
- cooldown 倒计时 29→25→20→12→3→1 (state=('OPEN',5,29)→('OPEN',5,1)), 设计行为自愈中
- 03:53:00 回到 `NV-MS-FB-ATTEMPT ... breaker=CLOSED` — **breaker 自愈完成, 当前未停 OPEN**
- 比 R2179 (1 次 OPEN 瞬间自愈) 停留更长 (~40s, 8 req 走 ms), 但仍属设计行为 (上游压力来时 OPEN 直走 ms, 压力退回 CLOSED). 0 冒到 cc4101 层真中断.

### 信号2: pexec_504=23 突出 + NVCF 上游连接类压力 (tier retry 吸收)
- nv_tier_attempts 30min: pexec_504=23 (突出, 比 R2179 的 19 略升) + pexec_conn_RemoteDisconnected=7 + pexec_429=3 + pexec_success=71
- NVCF 网关侧 504/conn/429 压力逐个打空 5 keys → all_keys_exhausted → nv_gw 内部 NV-MS-FB 退到 ms_gw 兜底
- 关键: breaker OPEN 的 ~40s 内 8 req 走 ms_gw internal fb **全 NV-MS-FB-OK 成功**, 0 冒到 cc4101, SR 95.7% 未受影响

## cc4101 层 fallback (负向核心指标)
- **cc4101 真 fallback = 1** (req=97f330a0, PRIMARY-FAIL timeout 60s header/ttfb 后 fallback ms_gw glm5_2_ms 2716ms 救回, 03:37)
  - 注: `NV-MS-FB-BREAKER-OPEN` 的 8 条是 **nv_gw 内部** 兜底 (NV-MS-FB tier), 不是 cc4101 fallback. cc4101 fallback 只看 PRIMARY-FAIL+FALLBACK-OK pair, 本轮仅 1 个 req id.
- **cc4101 fallback 1 < 5 阈值** ✅, 0 真中断, 0 双失败
- 与 R2179 (cc fallback=1) 持平, 无恶化

## nv_gw 内部 breaker 与参数误杀
- NV-MS-FB 内部兜底 (breaker OPEN 期 8 req + CLOSED 期 NV-MS-FB-ATTEMPT): 全 NV-MS-FB-OK 成功, 0 冒 cc 层
- NV-ANTH-BREAKER-FAIL = 1 条 (03:50:08 glm5_2_nv anth mid-stream stream_absolute_cap 软挂, 触发 nv_breaker OPEN, 后自愈回 CLOSED)
- 参数误杀类 (75s_timeout/STREAM-STALL-FAIL/BIG-INPUT/UPSTREAM-ERROR-SEEN/CC4101-UPSTREAM-ERROR/client_gone) = **全 0** ✅

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **43/6h** (R2179=44, 本轮 43, 持平基线 R2289 副作用受益持续)
- stream_total_deadline = 2; 763 空 error_type (正常成功)
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮 (CLAUDE.md BUG-A 待查项)

## 容器漂移信号 (docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-23T18:05:17Z** ← 与 R2179 逐项一致, **连续多轮未重建, 漂移止住** (STATE.md 旧值 07-22T15:10 已被 R2177 覆盖, 勿用)
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0, 与 R2179 一致)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2179 逐项一致, 无参数漂移 (参数快照见下)

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪). 本轮 kimi=0 req, glm5_2_nv 0 zombie (4 错全 stream_absolute_cap 非 zombie), 未触发新增 dump, 符合窗口
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, spec+骨架已就位 `~/cc_ps/cc2_repair_self/specs/`, 待实施). 本轮 zombie=0 素材严重不足 (需 ≥5), 未实施

## 决策: NOP 冻结 0 改动
STATE 三触发改动阈值全不满足:
- SR 95.7% > 85% ✅
- cc4101 真 fallback = 1 < 5 ✅ (0 真中断)
- 无新增错误类型 ✅ (4 cap mid-stream 背景波全系历史已知类; NV-MS-FB-BREAKER 真 OPEN ~40s 后自愈属设计行为非新增错误类型, breaker 仍正常消化上游压力)

四重佐证 nv_gw 稳:
1. 4 错全上游无害类 (4 stream_absolute_cap mid-stream 背景波, 0 zombie)
2. 无参数误杀 (全 0)
3. NV-MS-FB breaker 真 OPEN ~40s 后自愈回 CLOSED (设计行为); NV-ANTH-BREAKER-FAIL 1 条触发 OPEN 后自愈未停 OPEN
4. 参数无漂移 (nv_gw StartedAt=07-23T18:05 连续多轮未变, env 与 R2179 逐项一致)

新信号 (pexec_504=23 + breaker OPEN ~40s + 8 req 走 internal ms_fb) 均 NVCF 上游连接类压力, nv_gw 自愈链路正常消化 (internal fb 全成功 0 冒到 cc 层, SR 95.7%, 0 真中断). HM1 peer 已在 R2306/R2307 调 tier budget/stream deadline 应对同源 NVCF 上游压力 (HM1 线, 铁律不改 HM1). hm2_cc2 这边 SR 仍高 + 自愈正常 + nv chain 恢复健康 (03:53 peek healthy 95s/130s ttfb), 没到动 budget 的程度, 冻结观察等压力自然收. 改反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移. 容器 StartedAt 实测: nv_gw=07-23T18:05:17Z (连续多轮未重建) / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z. 03:53 nv_gw 末尾日志 NV-GLM52-SUCCESS + NV-PEEK-OK healthy ttfb 95661ms/130825ms, nv 链恢复健康服务正常.

## HM2 only / 未 Read 任何 /tmp 文件
本轮严格遵守中断告警铁律, 未 Read 任何 /tmp 下文件, 所有临时数据走 docker exec / DB 查询 / docker logs 获取. STATE.md 滞后修正以 git log + DB 重建, 绝不 Read /tmp.

## nv_gw 参数快照 (HM2, 本轮实测无漂移)
```
MIN_OUTBOUND_INTERVAL_S=10
KEY_COOLDOWN_S=60
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
TIER_COOLDOWN_S=180
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
NVU_FORCE_STREAM_UPGRADE=0
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_THRESHOLD=250000
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_MODELS=glm5_2_nv
KEY_AUTHFAIL_COOLDOWN_S=60
NV_INTEGRATE_KEY_COOLDOWN_S=90
```

Co-Authored-By: Claude <noreply@anthropic.com>
