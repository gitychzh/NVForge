# R2183 (hm2_cc2) — NOP 巡检轮 106

> 连续第 106 NOP. 三阈值全不满足 → 冻结. 0 改动 0 restart. HM2 only. 未 Read 任何 /tmp 文件.

## 数据 (HM2, 30min window, 04:27-04:57 CST 2026-07-24)

**nv_requests 30min**:
- 101 req / 全 200 → **SR = 100%** (主链路极稳, 比 R2182 98.0% 更干净, 零错误)
- by model: **glm5_2_nv 101/101 = 100%** (全本域流量); **kimi_nv 0 req** (R2286 过渡期收尾, 流量全汇 glm 稳定路径, 连续多轮)
- error_type: **0 rows** (30min 零错误, 连 R2182 的 2 个 stream_absolute_cap mid-stream 背景波都无)
- zombie_empty_completion: **0** (连续多轮归零)
- host_machine 全 HM2 本域

**cc4101 30min fallback (负向核心指标)**:
- grep 计数 = 1, 唯一 req **82ce0374** (与 R2182 同 req id, 窗口边缘旧事件 @04:27:01.8)
- 链路: primary(glm5_2_nv) header/ttfb timeout 60s → PRIMARY-FAIL-SKIP-CIRCUIT (60s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit) → fallback ms_gw glm5_2_ms → FALLBACK-OK 救回 3320ms
- **0 真中断**, <5 阈值, 与 R2182 (req 82ce0374) 同一旧事件滑入窗口, **非新发**

**nv_gw 内部 breaker**:
- **NV-ANTH-BREAKER-FAIL (R1719 设计, anthropic mid-stream 软挂)**: 30min **0 条** (比 R2181 的 2 条更干净, 与 R2182 一致, 健康未触发)
- **NV-MS-FB-BREAKER (nv→ms 内部 fb 兜底)**: 30min **2 次 OPEN 片段**:
  - 04:48:26-04:48:51 (~25s) 4 req state=('OPEN',5,N) cooldown 25→8→3→0 自愈 CLOSED
  - 04:56:06-04:56:31 (~25s) 8 req state=('OPEN',5,N) cooldown 25→24→21→14→13→11→0 自愈 CLOSED
  - 全自愈回 CLOSED, 期间 internal ms_fb 兜底全 OK, **0 冒到 cc4101 层**
  - 驱动根因: NVCF 上游 pexec_429=25 / pexec_504=4 / conn=6 → all_keys_exhausted → breaker OPEN 兜底
  - **延续 R2177 风暴后 R2178-R2182 稳定模式** (R2177=75 OPEN 风暴 → R2178=2 → R2179=1 → R2180/R2181=~40s), 设计行为非新增错误类型

**nv_tier_attempts 30min 错误**:
- pexec_success 74 / pexec_429 25 / pexec_conn_RemoteDisconnected 6 / pexec_504 4
- 全 NVCF 上游连接/配额类 (429=rate-limit, 504=gateway-timeout, conn=远端断连), **非旋钮能治** (KEY_COOLDOWN=60s/MIN_OUTBOUND=10s 已保守, 429 是 NVCF 账户级配额非 key pacing 可治)

**参数误杀类 (全 0)** ✅:
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

**BUG-A 499 盲点 (cc_requests 6h)**:
- client_gone_mid_stream = **42 / 6h** (与 R2180/R2181/R2182 基线一致, R2289 副作用受益持续)
- stream_total_deadline = 2; timeout 行无 (cc4101 自身非本域)
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮 (CLAUDE.md BUG-A 待查项)

**容器状态 (docker inspect 实测 JSON, 非旧 STATE 串错值)**:
- nv_gw: Status=running, StartedAt=**2026-07-23T18:05:17.525Z**, RestartCount=**0** (连续多轮稳定未重建, 与 R2182 逐项一致, **无漂移**)
- cc4101: StartedAt=2026-07-23T07:38:11.757Z, RestartCount=0 (与 R2182 一致)
- ms_gw: StartedAt=2026-07-21T12:50:09.819Z, RestartCount=0
- 注: `docker ps` 显示 nv_gw "Up 3 hours" 是显示取整误导 (07-23T18:05→now 04:57 实际 ~10h52m), 以 inspect JSON StartedAt+RC=0 为准, 无重启
- boot 日志: rr_counter 持久化正常 (nv_glm5_2=11603), 无崩溃重启痕迹
- env 关键参数与 R2182 逐项一致, **无参数漂移**

## 决策: NOP 巡检不改代码

STATE 三触发改动阈值全不满足:
1. 30min SR < 85%? → **100% NO**
2. cc4101 fallback 请求数 >5/30min 且新错误类型? → **1 (旧边缘事件 SKIP-CIRCUIT 救回) NOT >5, 无新错误 NO**
3. 新增错误类型 (zombie 比例持续上升 / NV-ANTH-BREAKER-FAIL 真 OPEN)? → **zombie=0, ANTH-BREAKER-FAIL=0, NV-MS-FB-BREAKER OPEN 是 R2178+ 稳定模式设计行为 NO**

四重佐证 nv_gw 稳:
1. 30min 零错误 (连 R2182 的 mid-stream 背景波都无, 更干净)
2. 无参数误杀 (全 0)
3. NV-ANTH-BREAKER-FAIL 不触发 (0 条), NV-MS-FB-BREAKER OPEN 自愈 (设计行为)
4. 参数无漂移 (容器 RC=0 未重建, env 与 R2182 逐项一致)

**为何不改旋钮治 429**: pexec_429=25 是 NVCF 账户级配额 rate-limit, KEY_COOLDOWN_S=60/MIN_OUTBOUND_INTERVAL_S=10 已保守 (10s 间隔, 5 key 轮转), 改大 cooldown/interval 只会增延迟 → 触发更多 primary 60s timeout (即 req 82ce0374 模式), 反而恶化. 无数据支撑的旋钮改动破坏稳定带.

## 验证

0 改动 0 restart 无需验证改动:
- curl /health ok (passthrough, nv_num_keys=5, default=glm5_2_nv, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv])
- docker ps 全栈 Up (nv_gw/cc4101/ms_gw/logs_db)
- docker inspect: nv_gw/cc4101/ms_gw RC=0 StartedAt 与 R2182 逐项一致 (无漂移)
- env 参数逐项比对无漂移

## R2192 三任务进度 (巡检轮必报)

- **任务1** (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- **任务2** (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪 — zombie body 不普遍含非标字段). 本轮 zombie=0 未触发新增 dump
- **任务3** (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec+双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 zombie=0 素材严重不足 (需 ≥5 才值得推进), 未实施. 是下一推进点.

## 下一轮建议

1. **继续巡检**. 盯 30min SR (本轮 100% 极佳), 保持 glm5_2_nv 全本域流量 + kimi_nv 0 req 过渡期收尾稳定路径.
2. **⚠ 新增 watch: pexec_429=25** (上轮 R2180/R2181 文本 "4293"/"4291" 推读为 429 计数 3/1, 本轮 25 显著升). 但 NV-MS-FB-BREAKER 已吸收 (internal ms_fb 全 OK 0 冒 cc 层, nv_requests 100% SR 不受影响). 若连续 2-3 轮 429 持续 ≥20 且 OPEN 片段增多/时长拉长 → 评估是否 NVCF 账户配额收紧, 届时再考虑 (非本轮). 单轮不行动.
3. **cc4101 fallback** 本轮=1 (旧边缘 req 82ce0374). 若下轮 fallback 滑出 30min 窗口归零更佳; 若见新 req id + PRIMARY+FALLBACK 双失败没救回, 或 fallback ≥5/30min (新 req id), 需评估.
4. **NV-ANTH-BREAKER-FAIL** 本轮 0 条健康. 若单轮 +5 或逼近 OPEN 阈值再评估. 注意 fallback_occurred=true (nv_gw 内部 NV-MS-FB tier 兜底) ≠ cc4101 fallback.
5. **触发改动三阈值** (全满足才动, 否则冻结): 30min SR 跌破 85% **或** cc4101 fallback >5/30min (新 req) **且** 出现新错误类型 (zombie 比例上升 / NV-ANTH-BREAKER-FAIL 真 OPEN).
6. **R2192 任务3** (撤 40007 前置核心): 当前双 message_start 约束未解, 需读 `~/cc_ps/cc2_repair_self/specs/R2192_task3_zombie_internal_keyretry_spec.md` + task3_skeleton_to_anth.py + task3_skeleton_passthrough.py. 素材窗口 (连续多轮 ≥5 zombie) 未现, 不实施. 三阈值冻结时不实施; 若下轮空闲且 zombie 素材充分窗口出现可主动推进 (grep -n 核实行号落盘前必须核实).
7. 主仓 R22XX (HM2->HM1) 只改 HM1 peer 不碰. 铁律: 只改 HM2.
8. 下一 session 接棒若 STATE 又被清: 用 `git log --oneline -8` + DB 重建, **绝不 Read /tmp** (上次 session 因反复 Read 不存在 /tmp 文件陷入 tool-use 死循环被 SDK 看门狗中断).
9. **容器漂移信号止住** (nv_gw StartedAt=07-23T18:05 RC=0 连续多轮未变 docker inspect 实测). 若下轮再变 + 参数漂移, 需查是谁改的.
10. **轮号体系**: R21XX (hm2_cc2/hm2_oc2) 是 HM2 本域我跟的线; R22XX (hm2_optimize_hm1) 只改 HM1 我不碰. hm2_cc2 与 hm2_oc2 各自续号.

## commit

0f70707..(本轮) R2183 NOP 巡检轮 106. 0 改动 0 restart. 待 commit + push.
