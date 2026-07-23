# R2185 — hm2_cc2 NOP 巡检轮 108 (连续第 108 NOP)

> 全新 session 接棒. STATE.md 头部停在 R2184 (本轮基线对齐). `git pull --ff-only` HEAD=e6b1964
> (R2310, HM1 peer 轮, 不参与). hm2_cc2 线最新 = R2184 (commit 45aae3d). 本轮 hm2_cc2 续 R2185.
> 铁律遵守: 未 Read 任何 /tmp 文件; 改前拉 30min 数据; 本轮 0 改动 0 restart 无需改后验证.

## 数据 (HM2, 30min window, 拉取时刻 07:00 CST = 23:00 UTC)

### nv_requests 30min (主链路 SR)
- 总 83 req / 78 × 200 / 5 × 502 → **SR = 93.99%** (> 85% ✅)
- by model: glm5_2_nv 78/82 (78 OK + 4 stream_absolute_cap), dsv4p_nv 0/2 (1 all_tiers_exhausted)
  - 注: glm5_2_nv 是当前本域唯一活跃主力模型 (kimi_nv 过渡期收尾流量全汇 glm 连续多轮)
- error_type (30min, 非 200): stream_absolute_cap=4 / all_tiers_exhausted=1

### nv_tier_attempts 30min (上游 NVCF 连接类, 非旋钮能治)
- pexec_success=26 / pexec_429=8 / pexec_empty_200=2 / pexec_conn_RemoteDisconnected=1
- pexec_429=8 (R2184=17 略降, NVCF 账户级配额非旋钮能治, KEY_COOLDOWN=60/MIN_OUTBOUND=10 已保守)

### 10min burst (最近窗口, 前期 burst 已过)
- 33 req / 32 × 200 / 1 × 502 (stream_absolute_cap) → **SR = 96.97%**
- 早期 burst (22:34-22:58 UTC 4× stream_absolute_cap) 已过, 当前窗口更干净

### stream_absolute_cap 6h 趋势 (确认是背景波非新模式)
- 17:00h=18 → 18:00h=11 → 19:00h=7 → 20:00h=3 → 21:00h=7 → 22:00h=4
- 持续下降趋势的 mid-stream 背景波 (R2180-R2184 同模式), 非新增错误类型

### cc4101 30min fallback (负向核心指标)
- **真 fallback = 1** (req 32942e6f, 06:42:40 PRIMARY-FAIL primary glm5_2_nv timeout 60066ms
  < chain budget 120s, SKIP-CIRCUIT → ms_gw 救回 FALLBACK-OK 2333ms)
- **0 真中断** (1 次 < 5 阈值, 全救回, 与 R2182-R2184 同窗口边缘模式), 无恶化
- FALLBACK-FAIL = 0

### nv_gw 内部 NV-MS-FB-BREAKER (R1719 设计)
- 06:43-06:50 连续 22 条 NV-MS-FB-BREAKER-OPEN (state=('OPEN',5,26)→('OPEN',5,2) 衰减),
  skipping nv chain serving ms_gw directly
- NVCF 上游 pexec_429/empty_200 级联 → breaker OPEN → internal ms_fb 兜底 → 自愈 CLOSED
- 这是 R2179-R2184 连续多轮同模式设计行为, 0 冒 cc 层 (nv_requests SR 不受影响)
- **NV-ANTH-BREAKER-FAIL 30min = 0 条** (健康, 与 R2182-R2184 一致)

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **42 / 6h** (与 R2183/R2184=42 基线持平, R2289 副作用受益持续)
- stream_total_deadline = 3/6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非 nv_gw 旋钮能治, 已定性多轮
  (属 CLAUDE.md BUG-A 待查项: SDK 客户端墙可调否, 未破)

### R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 历史验证 38.8%, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪).
  本轮窗口 0 zombie (30min) / 6h=7, 未触发新增 dump
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk
  守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施).
  本轮 30min 0 zombie 素材严重不足窗口 (需 ≥5 才值得推进), 未实施. 是下一推进点.

### 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv],
  default=glm5_2_nv ← R2286 改默认模型但 nv_gw nv_default_model 仍 glm5_2_nv, 过渡期双线并行)
- nv_gw RestartCount=0 StartedAt=**2026-07-23T18:05:17Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2179-R2184 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2184 逐项一致, **无参数漂移** (NVU_TIER_BUDGET_GLM5_2_NV=120 / UPSTREAM_TIMEOUT=90 /
  TIER_TIMEOUT_BUDGET_S=180 / MIN_OUTBOUND_INTERVAL_S=10 / KEY_COOLDOWN_S=60 /
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150 / NVU_BIG_INPUT_THRESHOLD=250000)

## 决策: NOP 巡检不改代码

STATE 三触发改动阈值全不满足:
1. SR 93.99% > 85% ✅ (10min burst 96.97%, 早期 burst 已过)
2. cc4101 fallback 请求数 1 < 5 ✅ 且全救回 (0 真中断)
3. 无新增错误类型 ✅ (stream_absolute_cap 是 R2180-R2184 连续多轮已知 mid-stream 背景波;
   NV-MS-FB-BREAKER OPEN 是 R2179-R2184 连续多轮已知设计行为, internal ms_fb 兜底 0 冒 cc 层)

四重佐证 nv_gw 稳:
1. 仅 5 错 (nv_requests 层 SR 93.99%, tier 层错误全 NVCF 上游连接类无害)
2. 无参数误杀 (全 0)
3. breaker 不真停 OPEN (06:43-06:50 OPEN 22 req 衰减后自愈回 CLOSED, NV-ANTH-BREAKER-FAIL=0)
4. 参数无漂移 (容器未重建 env 与 R2184 逐项一致)

改了反而破坏稳定带.

## 验证

0 改动 0 restart 无需验证改动.
- curl /health: ok (passthrough, nv_num_keys=5, default=glm5_2_nv)
- docker ps: 全栈 Up (nv_gw Up 5h / cc4101 Up 15h / ms_gw Up 2d / logs_db Up 7d)
- 容器 RC=0 全部, env 无漂移 (docker inspect 实测 StartedAt 与 R2184 逐项一致)
- 本轮 commit push 后完成.

## 下一步建议

1. 继续巡检. 当前 nv_gw 稳 (连续多轮 SR>93%, 三阈值全不满足). 继续冻结.
2. 盯 stream_absolute_cap: 本轮 30min=4 (6h 趋势 18→11→7→3→7→4 持续下降 mid-stream 背景波).
   若下轮升到 ≥10/30min 连续多轮且非背景波模式, 需评估.
3. 盯 NV-MS-FB-BREAKER: 本轮 06:43-06:50 OPEN 22 req 衰减后自愈 (R2179-R2184 同模式).
   若下轮 OPEN 风暴频次/持续时间显著上升 (如单轮 ≥3 次风暴或 OPEN 不自愈), 需评估.
4. 盯 pexec_429: 本轮=8 (R2184=17 略降, NVCF 账户级配额非旋钮能治). 若持续 ≥40/30min
   连续多轮, 评估 KEY_COOLDOWN/MIN_OUTBOUND (历史已证改大反触发更多 primary timeout 恶化).
5. 触发改动三阈值 (全满足才动, 否则冻结): 30min SR 跌破 85% **或** cc4101 fallback >5/30min
   **且** 出现新错误类型 (zombie 比例持续上升 / NV-ANTH-BREAKER-FAIL 真 OPEN / NV-MS-FB-BREAKER OPEN 不自愈).
6. R2192 任务3 (路径B zombie 内部重试) 是撤 40007 前置核心. 当前双 message_start 约束未解,
   需读 `~/cc_ps/cc2_repair_self/specs/R2192_task3_zombie_internal_keyretry_spec.md` +
   task3_skeleton_to_anth.py + task3_skeleton_passthrough.py 设计实施. 本轮 30min 0 zombie
   素材严重不足 (需 ≥5 才值得推进). 三阈值满足冻结时不实施; 若下轮空闲且出现 zombie 素材
   充分窗口 (连续多轮 ≥5 zombie) 可主动推进任务3 spec 复核 + 实施 (grep -n 核实行号, 落盘前必须核实).
7. 主仓 R22XX (HM2->HM1) 是 HM1 peer 轮 (only HM1, 如 R2308/R2309/R2310 ms_gw 改动),
   HM2 不参与, 保持 HM2 稳态. 铁律: 只改 HM2 不改 HM1.
8. 下一 session 接棒若 STATE 又被清: 用 `git log --oneline -8` + DB 重建, **绝不 Read /tmp**
   (上次 session 因反复 Read 不存在的 /tmp 文件陷入 tool-use 死循环被 SDK 看门狗中断).
9. 数据库列名: nv_requests 列是 `request_model` (不是 model), `status` 是 integer (200/502, 不是 'success').
10. 轮号体系: R21XX (hm2_cc2/hm2_oc2) 是 HM2 本域我跟的线; R22XX (hm2_optimize_hm1) 只改 HM1 我不碰.
    接棒以 HEAD 为准. hm2_cc2 与 hm2_oc2 是两条独立线, 各自续号 (本轮 hm2_cc2=R2185).

HM2 only. 未 Read 任何 /tmp 文件. 0 改动 0 restart.
