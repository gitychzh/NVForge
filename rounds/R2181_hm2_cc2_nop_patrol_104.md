# R2181 (hm2_cc2): NOP 巡检轮 104 — 连续第 104 NOP, 三阈值冻结, 0 改动 0 restart

## 号基线
- ⚠ STATE.md 滞后修正: 接棒时 STATE.md 头部停在 R2160 (patrol 93), 但 `git log` 实测最新 hm2_cc2 = R2180 (patrol 103, commit faa0ed5). 中间 R2161-R2180 共 20 轮 commit 正常但 STATE.md 未同步更新 (会话被中断在写 STATE 之前). 按 CLAUDE.md 铁律 "STATE 又被清用 git log + DB 重建", 以 git HEAD 为准. hm2_cc2 续 R2181.
- 上轮 hm2_cc2: R2180 (NOP 巡检轮 103, commit faa0ed5, 连续第 103 NOP, 30min 92req/95.7% SR)
- 本轮: **R2181 — hm2_cc2 NOP 巡检轮, 0 改动 0 restart, 连续第 104 NOP**
- 轮文件: `rounds/R2181_hm2_cc2_nop_patrol_104.md`

## 数据 (HM2, 30min window)
- 总 req = 94 (nv_requests 实测 87 OK(200) + 7 错(502))
- by model: **glm5_2_nv 87/94 (status 200=87 / 502=7)** — 全本域流量; **kimi_nv 0 req** (R2286 过渡期阵痛收尾, 流量全汇 glm 稳定路径, 与 R2180/R2179 一致连续多轮)
- SR = 87/94 = **92.6%** (主链路稳, 比 R2180 95.7% 略低但仍在 85% 以上, 7 错全 mid-stream 背景/上游类非旋钮能治)
- error_type (7 错): **stream_absolute_cap 6** + **NVAnth_IncompleteRead 1** (无 content_filter/timeout/conn/429/纯 zombie)
- host_machine 全 HM2 本域

## ⚠ 信号 (NV-MS-FB-BREAKER 真 OPEN ~40s 后自愈, NVCF 上游 504 压力波 — 延续 R2177-R2180 同模式)

延续 R2177(风暴75) → R2178(缓解2) → R2179(1次自愈) → R2180(OPEN~40s自愈) 的 NVCF 上游压力波模式, 本轮 breaker OPEN 停留 ~40s 后自愈回 CLOSED, 与 R2180 形态基本一致:

### 信号1: NV-MS-FB-BREAKER 真 OPEN ~40s 后自愈回 CLOSED
- 03:50:08.9 `NV-MS-FB-BREAKER-OPEN` 连续多条 (req 5a6e991b/147afaac/d9827c37/cf180c96/076a0ecb/6dfdae73/5bc345df/e729467c 等), breaker OPEN 状态直接 serve ms_gw
- cooldown 倒计时 state=('OPEN',5,29)→('OPEN',5,25)→20→12→3→1, 设计行为自愈中
- 03:53 之后回到 `NV-MS-FB-ATTEMPT ... breaker=CLOSED` 序列 — **breaker 自愈完成**
- 03:56-04:00 又有 4 次 all_keys_exhausted → ms_fb 兜底全 NV-MS-FB-OK 成功, state=CLOSED, 未再 OPEN
- 04:00:50 最后一条 NV-MS-FB-SERVED (state=CLOSED), 之后 41 分钟窗口内 (截至 04:05) 无新 OPEN 条
- **与 R2180 同形态**: breaker OPEN 停留 ~40s (8 req 走 ms internal fb 全成功), 0 冒到 cc4101 层. 属设计行为 (上游压力来时 OPEN 直走 ms, 压力退回 CLOSED)

### 信号2: pexec_504=22 突出 + NVCF 上游连接类压力 (tier retry 吸收)
- nv_tier_attempts 30min: pexec_success=72 + pexec_504=22 (突出, 与 R2180 的 23 基本持平) + pexec_conn_RemoteDisconnected=6 + pexec_429=3 + pexec_empty_200=1
- NVCF 网关侧 504/conn/429 压力逐个打空 5 keys → all_keys_exhausted → nv_gw 内部 NV-MS-FB 退到 ms_gw 兜底
- 关键: breaker OPEN 的 ~40s 内 8 req + CLOSED 期 NV-MS-FB-ATTEMPT 共 13 个唯一 req (去重) 走 ms_gw internal fb **全 NV-MS-FB-OK 成功**, 0 冒到 cc4101, SR 92.6% 未受影响

## cc4101 层 fallback (负向核心指标)
- **cc4101 真 fallback = 1** (req=97f330a0, PRIMARY-FAIL timeout 60s header/ttfb 后 fallback ms_gw glm5_2_ms 2716ms 救回, 03:37)
  - 旁注: `docker logs cc4101 --since 30m | grep -cE "FALLBACK"` = 4 是因 1 个 req 触发 PRIMARY-FAIL×2 + FALLBACK-OK×1 + SKIP-CIRCUIT 等多行. 真 fallback req id 去重仅 1 个.
  - 注: `NV-MS-FB-BREAKER-OPEN` 多条是 **nv_gw 内部** 兜底 (NV-MS-FB tier), 不是 cc4101 fallback. cc4101 fallback 只看 PRIMARY-FAIL+FALLBACK-OK pair, 本轮仅 1 个 req id (97f330a0).
- **cc4101 fallback 1 < 5 阈值** ✅, 0 真中断, 0 双失败
- 与 R2180 (cc fallback=1) 持平, 无恶化

## nv_gw 内部 breaker 与参数误杀
- NV-MS-FB 内部兜底 (breaker OPEN 期 8 req + CLOSED 期 NV-MS-FB-ATTEMPT 13 唯一 req): 全 NV-MS-FB-OK 成功, 0 冒 cc 层
- NV-ANTH-BREAKER-FAIL = 2 条 (04:02:21 glm5_2_nv anth mid-stream NVAnth_IncompleteRead 软挂, 触发 nv_breaker recorded, state=('CLOSED',4,0) 未真 OPEN)
- 参数误杀类 (75s_timeout/STREAM-STALL-FAIL/BIG-INPUT/UPSTREAM-ERROR-SEEN/CC4101-UPSTREAM-ERROR/client_gone) = **全 0** ✅

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **43/6h** (R2180=43, 本轮 43, 持平基线 R2289 副作用受益持续)
- stream_total_deadline = 2; 763 空 error_type (正常成功)
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮 (CLAUDE.md BUG-A 待查项)

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (历史验证 cache_read 38.8%, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪 — zombie body 不普遍含非标字段). 本轮窗口无新增 zombie dump (kimi 0 req, glm5_2_nv 7 错全 cap/NVRead 非 zombie_empty_completion 路径, 未触发 dump probe)
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 kimi zombie=0 且 glm zombie=0 (7 错全 cap/NVRead 非 zombie 路径), **素材严重不足** (需 ≥5 干净 zombie 才值得推进), 未实施. 仍为下一推进点.

## 容器漂移信号 (docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-23T18:05:17Z** ← 与 R2180 逐项一致, **连续多轮未重建, 漂移止住**
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (与 R2180 一致)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (与 R2180 一致)
- docker ps: nv_gw Up 2 hours / cc4101 Up 12 hours / ms_gw Up 2 days / logs_db Up 7 days, 全栈 Up

## 决策 (三阈值判读 → 冻结)
- SR = 92.6% > 85% ✅
- cc4101 真 fallback 请求数 = 1 < 5 ✅ (零数据空洞 0 真中断)
- 无新增错误类型 ✅ (7 错全 stream_absolute_cap + NVAnth_IncompleteRead, 均历史 mid-stream 背景波/上游连接类; NV-MS-FB-BREAKER OPEN 是设计行为自愈, 延续 R2177-R2180 同模式非新增; nv_tier pexec_504 是 NVCF 上游压力 tier retry 吸收非旋钮能治)

四重佐证 nv_gw 稳:
1. 7 错全上游无害类 (glm5_2_nv 6 cap mid-stream 背景波 + 1 NVRead 上游连接类)
2. 无参数误杀 (全 0)
3. NV-MS-FB-BREAKER 不真停 OPEN (OPEN ~40s 后自愈回 CLOSED, 开窗期 internal ms_fb 全 OK 0 冒 cc 层); NV-ANTH-BREAKER-FAIL 2 条 state=CLOSED 未真 OPEN
4. 容器无漂移 (RC=0, nv_gw StartedAt=07-23T18:05 连续多轮不变, env 与 R2180 逐项一致)

改了反而破坏稳定带. 三阈值全不满足 → NOP 冻结.

## 验��
- 0 改动 0 restart 无需验证改动
- curl /health ok + docker ps 全栈 Up + 容器 RC=0 + StartedAt 与 R2180 逐项一致 + env 无漂移
- nv_tier_attempts 30min pexec_504=22 NVCF 上游压力 tier retry 吸收, 未冒 cc 层
- 上轮 R2180 commit faa0ed5 已 push

## HM2 only
- 本轮只观测 HM2 nv_gw(40006). 未碰 proxy/ms-gw/ (40007 热备). 未碰 HM1 (peer, R22XX 线只改 HM1).
- 未 Read 任何 /tmp 文件 (规避上次 session tool-use 死循环中断).

## Co-Authored-By
Co-Authored-By: Claude <noreply@anthropic.com>
