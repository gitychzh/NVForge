# R2186 (hm2_cc2): NOP 巡检轮 109 — 连续第109 NOP, 三阈值冻结

**日期**: 2026-07-24 00:19 UTC
**上一轮**: R2185 (commit af5801d, 连续第108 NOP)
**本轮**: 0 改动 0 restart, NOP 巡检轮
**HM2 only** | 未 Read 任何 /tmp 文件

## 数据 (HM2, 30min window)

### nv_requests 30min
- 108 OK(200) + 4 错(502) → **SR = 96.4%** (108/112)
- by model: **glm5_2_nv 108/112 = 96.4%** (全本域流量; kimi_nv 0req 过渡期收尾流量全汇 glm 稳定路径, 连续多轮)
- error_type (status!=200):
  - stream_absolute_cap = 3 (mid-stream 背景波, R2180-R2185 同模式已知)
  - all_tiers_exhausted = 1 (上游 NVCF tier 全 key 耗尽级联, 触发 internal ms_fb)

### nv_tier_attempts 30min (上游 NVCF 连接类, 非旋钮能治)
- pexec_success = 85
- pexec_429 = 6 (R2185=8 略降, NVCF 账户级配额非旋钮能治)
- pexec_conn_RemoteDisconnected = 3
- pexec_empty_200 = 2

### cc4101 fallback 30min (负向核心指标)
- grep 命中 7 条 (PRIMARY-FAIL + FALLBACK-OK), 真独立 fallback 请求 = **2**:
  - req **79e1bd59** 07:52:19 — primary 60s timeout (SKIP-CIRCUIT, 60s<chain budget 120s) → ms_gw 救回 2230ms
  - req **f66fa3e4** 08:18:21 — primary **180s** full chain budget timeout → ms_gw 救回 4226ms
- **0 真中断** (2 次 < 5 阈值, 全 FALLBACK-OK 救回)
- ⚠ watch: f66fa3e4 是 180s (full budget) 才 timeout, 比前几轮 60s SKIP-CIRCUIT 案例更慢, 单例窗口边缘, 救回未破阈值

### nv_gw 内部 NV-MS-FB-BREAKER (R1719 设计)
- 30min = **5 个 NV-MS-FB-ATTEMPT** 全 breaker=CLOSED (nv chain all_keys_exhausted for glm5_2_nv → internal ms_fb 兜底)
- 0 OPEN 风暴 (R2184 05:48 OPEN 风暴 9req / R2185 06:43 OPEN 风暴 22req — 本轮更干净)
- **NV-ANTH-BREAKER-FAIL 30min = 0 条** (健康)

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **44 / 6h** (与 R2185=42 基线持平, R2289 副作用 SDK 131s 客户端墙结构性持续受益)
- stream_total_deadline = 3 / 6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非 nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

### 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv ← R2286 改默认模型但 nv_gw nv_default_model 仍 glm5_2_nv, 过渡期双线并行)
- nv_gw RestartCount=0 StartedAt=**2026-07-23T18:05:17Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2179-R2185 逐项一致
- env 关键参数与 R2185 逐项一致, **无参数漂移**

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪). 本轮窗口 0 zombie, 未触发新增 dump
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 `~/cc_ps/cc2_repair_self/specs/`, 待实施). 本轮 0 zombie 素材严重不足 (需 ≥5 才值得推进), 未实施. 是下一推进点.

## 决策: NOP 巡检, 不改代码

三触发改动阈值全不满足:
1. SR 96.4% > 85% ✅
2. cc4101 fallback 请求数 2 < 5 ✅ 且全救回 (0 真中断)
3. 无新增错误类型 ✅ (stream_absolute_cap + all_tiers_exhausted 都是 R2179-R2185 同模式已知)

四重佐证 nv_gw 稳:
1. 4 错全 mid-stream 背景波 + NVCF 上游 tier 耗尽级联 (非网关病)
2. 无参数误杀 (全 0)
3. breaker 不真停 OPEN (5 个 ATTEMPT 全 CLOSED, NV-ANTH-BREAKER-FAIL=0)
4. 参数无漂移 (容器未重建, env 与 R2185 逐项一致)

改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + nv_gw RC=0 + env 无漂移.

## 下一轮建议
1. 继续巡检. 三阈值全不满足 → 继续冻结.
2. 盯 f66fa3e4 模式 (180s full budget timeout): 若下轮这类 180s timeout 案例持续出现且多, 评估是否上游 NVCF 某段时间变慢, 但单例未破阈值不动.
3. 盯 pexec_429 (本轮=6, R2185=8 略降, NVCF 账户级配额非旋钮能治). 若持续 ≥40/30min 连续多轮, 评估 KEY_COOLDOWN/MIN_OUTBOUND (历史已证改大反恶化, 谨慎).
4. 盯 NV-MS-FB-BREAKER (本轮 0 OPEN 风暴, 5 ATTEMPT 全 CLOSED, 比 R2184/R2185 干净). 若 OPEN 风暴频次/持续时间上升 (单轮 ≥3 次风暴或 OPEN 不自愈), 评估.
5. 触发改动三阈值 (全满足才动, 否则冻结): 30min SR 跌破 85% **或** cc4101 fallback 请求数 >5/30min **且** 出现新错误类型.
6. R2192 任务3 (路径B zombie 内部重试) 是撤 40007 前置核心. 当前 0 zombie 素材严重不足 (需 ≥5). 三阈值冻结时不实施; 若下轮空闲且出现 zombie 素材充分窗口 (连续多轮 ≥5 zombie) 可主动推进任务3 spec 复核 + 实施 (grep -n 核实行号, 落盘前必须核实).
7. 主仓 R22XX (HM2->HM1) 是 HM1 peer 轮 (only HM1, 如 R2310/R2311/R2312), HM2 不参与. 铁律: 只改 HM2 不改 HM1.
8. 接棒若 STATE 被清: 用 `git log --oneline -8` + DB 重建, **绝不 Read /tmp**.

## 参数快照 (HM2, 本轮确认无漂移)
```
MIN_OUTBOUND_INTERVAL_S=10
KEY_COOLDOWN_S=60
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
TIER_COOLDOWN_S=180
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_THRESHOLD=250000
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_MODELS=glm5_2_nv
KEY_AUTHFAIL_COOLDOWN_S=60
NV_INTEGRATE_KEY_COOLDOWN_S=90
```

容器 (docker inspect 实测):
- nv_gw RestartCount=0 StartedAt=2026-07-23T18:05:17Z (连续多轮未重建, RC=0, env无漂移)
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
