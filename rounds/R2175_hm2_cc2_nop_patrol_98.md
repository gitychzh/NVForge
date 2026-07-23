# R2175 (hm2_cc2): NOP 巡检轮 98 — 稳态延续 + breaker 反复 OPEN 长尾振荡观察, 0 改动 0 restart

## 上下文
全新 session 接棒。STATE.md 头部停在 R2160 (滞后, hm2_cc2 线 git log 实际已到 R2174).
git pull 后按 `git log --grep hm2_cc2` 确认 hm2_cc2 线最新 = R2174 (commit 385a015),
本轮续 R2175, 连续第 98 NOP. 主仓 HEAD 241e8af 是 hm2_oc2 线 (另一条 HM2 本域线, 独立续号),
非本线, 不影响 hm2_cc2 轮号. 铁律: 只改 HM2 不改 HM1.

旧 rounds/R2175_hm2_cc2_nop_patrol.md 是上一 session 残留草稿 (nv_gw StartedAt=07-21,
dsv4p_nv 4错, 与当前不符), 未 commit, 本轮用真实数据覆写.

## 数据 (HM2, 30min window)
- nv_requests: 75 req / 69 OK(200) / 6 错(502) → **SR = 92.0%** (69/75)
- by model:
  - **glm5_2_nv: 55 OK / 2 错 → 96.5%** (2 错: 1 zombie_empty_completion + 1 stream_absolute_cap, 均 mid-stream 背景波类, 本域主链路稳)
  - **kimi_nv: 13 OK / 4 错 → 76.5%** (4 错全 all_tiers_exhausted, R2286 过渡期阵痛延续, NVCF 上游连接类非旋钮能治)
  - dsv4p_nv: 1 OK / 0 错
- error_type 分类: 4 all_tiers_exhausted(kimi) + 1 stream_absolute_cap(glm5_2_nv) + 1 zombie_empty_completion(glm5_2_nv)
- 无 content_filter / timeout / conn / 429 (nv_requests 侧)
- host_machine 全 HM2 本域 (opc2sname)

### ⚠ 新观察信号: breaker 反复 OPEN 长尾振荡 (非新错误类型, 但值得盯)
2h nv_gw breaker 时间线 (docker logs nv_gw --since 2h):
- 19:33-19:37: NV-MS-FB-BREAKER-OPEN ×4 (glm5_2_nv, state=('OPEN',5,29/21/15/16)) — R2170 风暴余波
- 19:50: NV-ANTH-BREAKER-FAIL zombie (glm5_2_nv, state=('CLOSED',1,0)) — 重新 CLOSED 计数清零
- 20:00: NV-ANTH-BREAKER-FAIL cap (glm5_2_nv, state=('CLOSED',4,0))
- 21:01: NV-ANTH-BREAKER-FAIL zombie (glm5_2_nv, state=('OPEN',5,29), req=d0d6198a) — 计数到 5 OPEN
- 21:03: NV-MS-FB-BREAKER-OPEN (glm5_2_nv, state=('OPEN',5,23), req=b4a39c2c) — 又 OPEN 一次
- **21:09+: 已自愈 CLOSED** (NV-MS-FB-SERVED state=CLOSED, NV-MS-FB-ATTEMPT breaker=CLOSED 正常兜底)

判定: breaker 在 2h 内反复 OPEN 5 次 (19:33×4 + 21:03×1) + ANTH-BREAKER 21:01 OPEN 1 次,
但**全部快速自愈 → CLOSED**, 当前 (21:09+) breaker state=CLOSED. 这是 R2170 风暴的**长尾振荡**,
非新系统性恶化 (模式同 R2170, OPEN→CLOSED 自愈循环). 但反复 OPEN 5 次逼近 STATE "下一轮"阈值
"单轮 +5 或连续 2-3 轮上升需评估"的边界, 下轮继续盯.

注意: NV-MS-FB-BREAKER-OPEN 是 nv_gw **内部** ms_gw 直走兜底 (tier 间), ≠ cc4101 fallback.
本轮 cc4101 fallback 仅 1 条 (见下).

### kimi_nv 429 上游限流 (R2286 过渡期已知)
nv_tier_attempts 30min: pexec_429 ×24 (kimi tier 层 NVCF 限流, 集中 12:46-13:10 午后高峰,
最近 30min 已稀疏). 429 → tier 全失败 → all_tiers_exhausted. 全 NVCF 上游连接类, 非旋钮能治,
R2286 改默认模型过渡期阵痛延续.

## cc4101 30min fallback (负向核心指标)
- **fallback = 1** (req=b10007fe): glm5_2_nv primary header/ttfb timeout 60s (60062ms) →
  cc4101 PRIMARY-FAIL-SKIP-CIRCUIT (60062ms < chain budget 120s, cc4101 抢先 fallback 未计 circuit)
  → ms_gw glm5_2_ms 救回 (FALLBACK-OK 6790ms). **0 真中断**, 单点非系统性.
- 模式同 R2162 的单点 fallback=1 (大请求撞 NVCF 慢节点 ttfb 超 60s 墙), 非新恶化.
- 与 R2174 (fallback=0) 比 +1, 但单点救回 0 真中断, 仍 <5 阈值.

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **28 / 6h** (与 R2174=29 基本持平, R2289 副作用受益持续)
- timeout = 164/6h (cc4101 自身非本域); server_5xx=6; stream_total_deadline=1
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

## 2h 趋势 (背景波 + 过渡期)
- glm5_2_nv: 236 OK / 4 错 → **98.3%** (本域主链路 2h 极稳, 4 错低位持续)
- kimi_nv: 77 OK / 28 错 → 73.3% (R2286 过渡期振荡, 上游 429/连接类)
- dsv4p_nv: 1/1 = 100%

## 容器 / 参数 (无漂移, docker inspect 实测)
- nv_gw /health: ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (Up 22h, 连续多轮 RC=0 未重建, 与 R2174 逐项一致)
- cc4101 Up 6 hours (RestartCount=0); ms_gw Up 2 days
- env 关键参数与 R2174 快照逐项一致, **无参数漂移**:
  MIN_OUTBOUND_INTERVAL_S=10 / KEY_COOLDOWN_S=60 / UPSTREAM_TIMEOUT=90 /
  TIER_TIMEOUT_BUDGET_S=180 / TIER_COOLDOWN_S=180 / NVU_FORCE_STREAM_UPGRADE=0 /
  NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_BIG_INPUT_FAIL_N=1 / NVU_STREAM_ABSOLUTE_CAP_S=150

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪).
  本轮窗口 glm5_2_nv 1 zombie (req=d0d6198a) 属 nv_gw 检测点, 未触发新增 dump (单点波动)
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk
  守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施).
  本轮 glm5_2_nv zombie=1 素材不足窗口 (需 ≥5 才值得推进), 未实施. 是下一推进点.
  注: 本轮 glm5_2_nv zombie (req=d0d6198a) 正是 to_anth 路径 (cc2 自身) 场景,
  但单 sample 不足以验证 converter 守卫 + 实施 keyretry.

## 决策: NOP 巡检, 0 改动 0 restart
STATE "下一轮"三触发改动阈值 vs 当前:
| 指标 | 当前 30min | 阈值 | 判定 |
|---|---|---|---|
| SR | 92.0% (glm5_2_nv 96.5%) | 跌破 85% | 在阈值之上 ✅ |
| cc4101 fallback | 1 条 (单点救回 0 真中断) | >5 | 在阈值之下 ✅ |
| 新错误类型 | 0 (cap+zombie+ATE 全历史已现) | zombie上升/BREAKER真触发 | 无 ✅ |

三条件全不满足 → 数据不支撑调参 → 冻结, NOP 巡检不改代码.

四重佐证 nv_gw 稳:
1. 6 错全上游无害类 (glm5_2_nv 1cap+1zombie mid-stream背景波; kimi 4ATE 过渡期上游429类)
2. 无参数误杀 (全 0)
3. breaker 反复 OPEN 但全自愈 CLOSED (当前 state=CLOSED, R2170 长尾振荡非系统性)
4. 参数无漂移 (容器未重建 env 与 R2174 逐项一致)

⚠ 边界信号: breaker 2h 反复 OPEN 5 次 (虽全自愈), 逼近"连续 2-3 轮上升需评估"边界.
但当前 CLOSED + cc4101 fallback 仅 1 单点 + 0 真中断, 不触发改动. 下轮重点盯 breaker 是否
持续反复 OPEN 不自愈. 改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok (nv_num_keys=5, nvcf_pexec_models 正常).
docker ps 全 Up (nv_gw 22h / cc4101 6h / ms_gw 2d / logs_db 6d). 容器 RC=0 + env 无漂移.

## commit
本轮 R2175 hm2_cc2 NOP 巡检, 仅 rounds/R2175_*.md 记录 (覆写上一 session 残留草稿),
0 源码 0 env 改动 0 restart. HM2 only.
