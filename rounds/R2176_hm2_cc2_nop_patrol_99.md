# R2176 hm2_cc2 NOP 巡检轮 99 (连续第 99 NOP)

> 全新 session 接棒. STATE.md 头部严重滞后 (停 R2160), git pull 后 hm2_cc2 线实际最新 = R2175
> (79fc79a, 连续第98 NOP). R2174 commit 注明 "上一session被SDK看门狗中断未commit, 补commit R2170
> 遗留轮文件". 本轮 hm2_cc2 续 R2176.
>
> ⚠ 本轮核心发现: **活跃 NV-MS-FB-BREAKER OPEN 风暴** (glm5_2_nv 5 keys NVCF 上游 SSLEOFError),
> 6h 累计 264 次 OPEN 振荡. 但根因非旋钮可治, 0 真中断 (ms_gw 热备全兜成功), 三阈值未触发 → 仍冻结 NOP.

## 数据 (HM2, 30min window)

**nv_requests 30min (by model+status)**:
- glm5_2_nv: 66×200 + 5×502 = 71 req, SR = **93.0%**
- kimi_nv: **0 req** (30min 窗口恰好未覆盖 kimi 流量; 6h 看 kimi 仍有流量但 15:00 后归零, 见下)
- dsv4p_nv: 0

**error_type 30min (nv_requests)**:
- stream_absolute_cap: 4 (mid-stream 背景波, glm5_2_nv, 历史已知类)
- zombie_empty_completion: 1
- 无 content_filter / timeout / conn / 429

**cc4101 30min fallback (负向核心指标)**:
- fallback = **2** (打破连续多轮=0; 2 条 glm5_2_nv ttfb 60s 超时 → ms_gw 救回)
- 2 条均 PRIMARY-FAIL-SKIP-CIRCUIT 模式 (primary timeout < chain budget 120s, cc4101 pre-empt nv_gw retry, 不计熔断)
- req id: a07a1a9e (00:57:27), 6d380d70 (01:15:28), 均 FALLBACK-OK 0 真中断
- 2 < 5 阈值, 单点非系统性

**⚠ 活跃 NV-MS-FB-BREAKER OPEN 风暴 (核心新发现, 本轮重点)**:
- docker 当前时间 01:22:00 CST
- 最近 10min breaker OPEN = **13**, NV-MS-FB-SERVED (ms_gw 兜底) = **35**
- 6h breaker OPEN 累计 = **264** (持续振荡非偶发)
- 时点分布: 23:49-23:57 密集段 + 01:17-01:21 密集段 = 反复 OPEN/HALF_OPEN/OPEN 振荡
- 最新 [01:21:57.9] 仍活跃: `NV-GLM52-CHAIN-FALLBACK` + `STAGE1_CHAIN_FAIL` + `all_keys_exhausted` → breaker=HALF_OPEN → ms_fb
- state=('OPEN', 5, 21/12/0/25/28/24): 第一参数 5=fail count, 第二参数=cooldown 剩余秒 (在 0-28 间跳=反复 OPEN)
- `NV-GLM52-CHAIN-SKIP-PEXEC2`: chain 第一轮全 key fail 后跳过 pexec 第二轮 (省 120s), 直接 all_keys_exhausted → ms_fb

**根因 (NVCF 上游 SSLEOFError 连接类, 非旋钮可治)**:
- `NV-GLM52-ERR` k3/k4 `SSLEOFError: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol`
- NVCF 上游 TLS 连接被中途断开 (非 429 配额, 非 nv_gw 配置问题)
- 影响 pexec_us_rr key (k3/k4 实测, chain 第一轮 5 keys 全 fail)
- ms_gw 走 glm5_2_ms 直连 glm (非 NVCF), 不受 SSLEOF 影响 → 兜底全成功 → 0 真中断

**glm5_2_nv 6h hourly SR 趋势**:
- 11:00 98.7% → 12:00 98.4% → 13:00 90.4% → 14:00 95.1% → 15:00 90.1% → 16:00 91.6% → 17:00 92.3%
- 13:00 起 SR 下台阶 (98→90 段), 与 SSLEOFError 风暴时段吻合, 但 ms_gw 兜底维持表面 SR>90%

**kimi_nv 流量真相 (R2286 过渡期)**:
- 6h kimi_nv 190×200 + 43×502 = 233 req, SR 81.5% (过渡期阵痛延续, ATE 主导)
- ⚠ **15:00 后 kimi_nv 流量归零** (16:00/17:00 全 glm5_2_nv) — cc4101 默认模型路由疑似在 15:00 切回 glm5_2_nv
- kimi 30min=0 非异常, 是路由切换 + 窗口巧合
- kimi chain 30min 无 exhausted (流量 0 无压力)

**BUG-A 499 盲点 (cc_requests 6h)**:
- client_gone_mid_stream = **41 / 6h** (R2175=29→上升, 但时点散布 11:00→00:00 每小时 1-5 个, 散布型非风暴簇)
- timeout=12, stream_total_deadline=2, 空(=200)750
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮 (CLAUDE.md BUG-A 待查项)
- 41 vs 29 是 6h 窗口覆盖时段差异 (大请求多时段 499 高), 非骤升

**容器状态 (漂移信号核, docker inspect 实测)**:
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 无漂移)
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- docker ps: cc4101 Up 10h / nv_gw Up 26h / ms_gw Up 2days / logs_db Up 7days
- env 关键参数与 R2175 逐项一致, **无参数漂移**

**参数误杀类 (全 0)** ✅:
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR = 0

**R2192 三任务进度 (巡检轮必报)**:
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪). 本轮窗口 kimi 1 zombie 但属 nv_gw 检测点未触发新增 dump
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, spec+双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 kimi 30min zombie 素材不足窗口(需 ≥5), 未实施

## 决策: NOP 巡检不改代码. 三触发改动阈值全不满足

1. 30min SR 93.0% (glm5_2_nv, 含 ms_gw 兜底) > 85% ✅
2. cc4101 fallback 请求数 2 < 5 ✅ (注意 nv_gw 内部 NV-MS-FB-BREAKER OPEN 走 ms_gw ≠ cc4101 fallback, 不触发该阈值)
3. 无新增错误类型 ✅ (SSLEOFError 是已知 NV-GLM52-ERR 类; stream_absolute_cap + zombie 历史已知)

## 为何 breaker 264 次 OPEN 仍冻结 (关键论证)

CLAUDE.md 说 "breaker 几乎不 OPEN 是目标", 但本轮 6h 264 次 OPEN 仍不改:

1. **根因明确非旋钮可治**: NVCF 上游 SSLEOFError (TLS 中途断开), 调 tier budget / breaker cooldown / key cooldown 都修不了被切断的 TLS 连接. 符合 CLAUDE.md "根因是 NVCF 上游非旋钮能治的不轻易改" 铁律.
2. **0 真中断**: ms_gw 走 glm5_2_ms 直连 glm 非 NVCF, 不受 SSLEOF 影响, 兜底全成功. 这正是 40007 热备设计的目的 (nv_gw 重启/上游挂的窗口期靠它兜).
3. **三阈值未触发**: 表面 SR 93% 未跌破 85% (ms_gw 兜底维持); cc4101 fallback 2<5; 无新错误类型.
4. **R2170 先例**: 类似 SSLEOF/connection 风暴自恢复过, 未改码.
5. **贸然调旋钮会破坏稳定带/反模式**:
   - 调短 breaker cooldown → HALF_OPEN 更快重试挂的 NVCF → 更振荡
   - 调长 breaker cooldown → 更久走 ms_gw → 像放弃 nv (违背 "让 nv 稳到不需 fallback" 目标)
   - 调高 breaker 阈值 → "假装不 OPEN" 反模式 (CLAUDE.md 明确禁止: 把死循环请回来)

## 四重佐证 nv_gw 稳定带未崩 (带病运行但未断)

1. ms_gw 兜底全成功 0 真中断 (热备设计正发挥作用)
2. 无参数误杀 (全 0), env 无漂移, 容器 RC=0 未重建
3. breaker 振荡是上游 SSLEOF 类非 nv_gw 自身故障 (NV-GLM52-ERR k3/k4 明确 NVCF 侧)
4. kimi_nv/dsv4p_nv 未受波及 (glm5_2_nv 单模型上游问题)

## 验证

0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z (连续多轮未重建) / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z.

## 下一轮该做什么

1. **⚠ 顶级跟踪: 活跃 breaker 风暴是否自恢复**. 本轮 6h 264 次 OPEN + 最近10min 13 次, 远超 "几乎不 OPEN". 下轮拉 30min breaker OPEN 计数:
   - 若归零或 <5/30min → SSLEOFError 风暴自恢复, 确认 R2170 类先例, 继续冻结
   - 若仍 ≥10/30min 且持续 2-3 轮 → 风暴未自恢复, 评估主动干预方向 (非 nv_gw 旋钮, 而是 cc4101 层把 glm5_2_nv 流量分散到 kimi_nv/dsv4p_nv 给挂的 NVCF keys 恢复窗口; 但 kimi 也在过渡期阵痛风险高, 需数据决策)
2. 盯 NVCF SSLEOFError 是否从 k3/k4 蔓延到更多 key. 若 5 keys 全持续 SSLEOF → NVCF 平台级故障, 可能需上报非本域能治.
3. 盯 ms_gw 兜底成功率. 当前 35/35 OK. 若 ms_gw 开始失败 → 热备也承压, 真危机.
4. cc4101 fallback=2 单点 (glm5_2_nv ttfb 60s 超时). <5 阈值不触发, 但若升到 ≥5 且新 req id → 评估.
5. kimi_nv 15:00 后归零信号: 下轮查 cc4101 默认模型路由是否真在 15:00 切回 glm5_2_nv (R2286 改默认 kimi 但路由可能回退). 非本域 nv_gw 能控, 记录待查.
6. 499=41/6h 散布型非风暴, BUG-A SDK ~131s 客户端墙结构性限制持续, 非本轮能治.
7. R2192 任务3 (路径B zombie 内部重试): 是撤 40007 前置核心. 当前双 message_start 约束未解, spec+骨架已就位. 本轮 kimi 30min zombie 素材不足(需≥5). 三阈值满足冻结时不实施; 若下轮出现 zombie 素材充分窗口(连续多轮 ≥5 zombie) 可主动推进 spec 复核 + 实施 (grep -n 核实行号, 落盘前必须核实, 改.py 必须 docker compose restart).
8. 主仓 R22XX (HM2->HM1) 是 HM1 peer 轮 (only HM1), HM2 不参与, 保持 HM2 稳态. 铁律: 只改 HM2 不改 HM1.
9. 下一 session 接棒若 STATE 又被清: 用 `git log --oneline -8 | grep hm2_cc2` + DB 重建, **绝不 Read /tmp** (上次 session 因反复 Read 不存在的 /tmp 文件陷入 tool-use 死循环被 SDK 看门狗中断).
10. **轮号体系**: hm2_cc2 线最新 R2175 (本轮 R2176), hm2_oc2 线已到 R2304 (另一 agent 跟). 两线独立续号. 接棒以 `git log | grep hm2_cc2` HEAD 为准, 别用 STATE 头部 (可能滞后).

## nv_gw 参数快照 (HM2, 本轮确认无漂移, docker inspect 实测)
```
MIN_OUTBOUND_INTERVAL_S=10
KEY_COOLDOWN_S=60
KEY_AUTHFAIL_COOLDOWN_S=60
NV_INTEGRATE_KEY_COOLDOWN_S=90
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
NVU_EMPTY_200_FASTBREAK=3
NVU_PEXEC_TIMEOUT_FASTBREAK=3
```
容器 (docker inspect 实测):
- nv_gw RestartCount=0 StartedAt=2026-07-22T15:10:34Z (连续多轮未重建, RC=0, env无漂移)
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
