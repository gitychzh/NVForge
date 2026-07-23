# R2155 — hm2_cc2 NOP 巡 88 (连续第 88 NOP, 三阈值冻结)

> HM2 only. 不碰 HM1. 0 改动 0 restart. 时点 10:08 UTC / 18:10 CST.
> git log 重建: hm2_cc2 线最新 commit R2150 (8922263 @07-23); HEAD = c0c5f2f R2154 (hm2_oc2).
> STATE.md 滞后第 47 次 (头停 R2137, 实测 hm2_cc2 线已到 R2150/2152, 本轮续 R2155).

## 数据 (HM2, 30min window, 10:08 UTC 时点)

### nv_gw 总览
- 108 请求 / 97 OK(200) / 11 错(502) → **SR = 89.8%** (97/108)
- by model:
  - **glm5_2_nv 63/63 = 100.0%** (本域主链路, 连续多轮满分 golden 延续, 0 zombie 0 软失败)
  - **kimi_nv 34/45 = 75.6%** (11 错; R2286 新默认模型过渡期阵痛)
- error_type (11 错全 kimi_nv):
  - zombie_empty_completion = 7 (req 5b4f9335/dbb6070c/65d81acd/ad7a38c3 + ... @09:51-10:06 UTC)
  - all_tiers_exhausted = 3 (f8e18dcb/2d11e4b8/050fbfa9)
  - NVStream_IncompleteRead = 1 (3d7ce780 @09:49)
- 无 content_filter / timeout / conn / 429
- host_machine 全 HM2 本域

### cc4101 fallback (负向核心指标)
- **30min cc4101 fallback = 0** — 零数据空洞, 0 真中断, 连续多轮最佳.
- `docker logs cc4101 --since 30m | grep -cE "FALLBACK-OK|FALLBACK "` = 0
- 注意: nv_gw 内部 NV-MS-FB tier 兜底 (fallback_occurred=true, R1719 设计吸收) ≠ cc4101 fallback. 本轮 cc4101 fallback=0 才是真正"零数据空洞".

### nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719)
- 30min `docker logs nv_gw --since 30m | grep NV-ANTH-BREAKER` = 空 (无新触发)
- 远未到 OPEN 阈值.

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone (nv_gw 内部) = 0

### BUG-A 499 (cc_requests 6h)
- client_gone_mid_stream = **31 / 6h** (同 R2149/R2150 基线, 较 R2137 的 50 降 38%, R2289 副作用受益持续)
- stream_total_deadline = 3 / 6h; server_5xx = 6; timeout = 164
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非旋钮能治, CLAUDE.md BUG-A 待查项.

## 容器状态 (docker inspect / ps 实测, 无漂移)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], **nv_default_model=glm5_2_nv**)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 与 R2150 一致)
- cc4101 RestartCount=0 StartedAt=2026-07-22T14:28:23Z (Up 2h, RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (Up 45h, RC=0) ← 旧 STATE 曾错记成 nv_gw 的值, 已修正
- nv_gw Up 19h / cc4101 Up 2h / ms_gw Up 45h / logs_db Up 6d 全栈 Up
- env 关键参数与 R2150 逐项一致, **无参数漂移**

## 关键判读

1. **本域 glm5_2_nv 100% golden 连续多轮稳态**: nv_gw nv_default_model 仍是 glm5_2_nv (health 确认), 本域主链路极稳. R2154 (hm2_oc2) 报本域 30min/60min/2h/6h 全满分 golden, 本轮 cc2 视角本域 63/63=100% 印证延续.
2. **kimi_nv 过渡期阵痛 (R2286/R2292 新默认模型)**: 11 错全 kimi_nv, 7 zombie + 3 ATE + 1 IR, 全 NVCF 上游连接类 (SSLEOFError/empty_200/RemoteDisconnected 类), 非 nv_gw 旋钮能治根因. 与 R2150 报"kimi_nv 6h 73% 过渡期阵痛"一致.
   - R2150 时点 kimi_nv 错集中在 09:07 UTC; 本轮 7 zombie 散在 09:51-10:06 UTC, 仍是过渡期上游瞬时故障, 非簇非持续恶化.
3. **cc4101 fallback=0 零数据空洞**: 本轮最佳负向指标. kimi_nv 11 错虽多, 但 cc4101 层 0 fallback = kimi_nv 失败未触发跨网关切换, 或 nv_gw 内部 NV-MS tier 兜底吸收 (R1719 设计). 反馈循环健康.
4. **R2192 三任务进度**:
   - **任务1 (cc4101 透传 cache_control)**: ✅ 已落地 (R2228, cache_read 38.8% 持续, 走 nv_gw 读 NVCF prompt_tokens_details.cached_tokens 路径).
   - **任务2 (nv_gw 抓 zombie body dump probe)**: ✅ 已落地 (handlers.py:67-108 NV-ZOMBIE-DUMP, dump dir /app/logs/zombie_dumps). **本轮核证产出**: 27 个 dump 文件已积累, 最新 @07-23 07:41 CST. **但 30min 内 DB 记 7 zombie, dump 文件未见对应新增** — dump probe 触发路径与 DB error_type 记录路径可能不对齐 (流式 vs 非流式检测点), 下轮若 kimi_nv zombie 持续需查 dump probe 覆盖率.
   - **任务3 (路径B zombie 内部重试)**: 部分落地. 双 message_start 约束未解 (converter feed_chunk message_start_sent 守卫存在, 但 next_block_idx/active_block_type 重置守卫缺, 需限制 content=0/reasoning=0/saw_tool_calls=False 才可重试). spec 在 `~/cc_ps/cc2_repair_self/specs/R2192_task3_zombie_internal_keyretry_spec.md`.
5. **R2192 任务2 hypothesis A 强证伪复核**: R2150 报 27 sample 全 ABSENT (无 context_management/output_config/thinking 非标字段差异), 强证伪 hypothesis A (CC 干扰字段致 zombie). 本轮 7 zombie 全 kimi_nv (非 glm5_2_nv), kimi_nv 的 zombie 字段差异未单独分析 (任务2 dump 产物可后续分析, 但当前 kimi_nv 阵痛属过渡期非优先).

## 决策: NOP 巡检, 0 改动 0 restart, 冻结

STATE 三触发改动阈值核查:
1. 30min SR 89.8% > 85% ✅ (总 SR 被 kimi_nv 过渡期拉低, 但本域 glm5_2_nv 100%, 阈值看本域更准)
2. cc4101 fallback 请求数 0 < 5 ✅ (零数据空洞, 连续多轮最佳)
3. 无新增错误类型 ✅ (zombie/ATE/IR 全历史已现, kimi_nv 过渡期阵痛非首现类型)

四重佐证 nv_gw 稳:
- 11 错全 kimi_nv 上游连接类 (过渡期阵痛), 本域 glm5_2_nv 0 错
- 无参数误杀 (全 0)
- breaker 不真 OPEN (30min 无新触发)
- 参数无漂移 (容器未重建, env 与 R2150 逐项一致)

**改了反而破坏稳定带. kimi_nv 阵痛是 R2286/R2292 改默认模型的过渡期后果, 非 nv_gw 旋钮能治根因 (NVCF 上游连接类). 等 kimi_nv 过渡期企稳再评估.**

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z / cc4101=07-22T14:28:23Z / ms_gw=07-21T12:50:09Z.

## 下一轮建议
1. 继续巡检. 盯 kimi_nv 过渡期阵痛是否企稳 (zombie/ATE/IR 量是否回落). R2150→本轮 kimi_nv 仍 11 错/30min, 若连续 3-4 轮不降, 评估是否回退默认模型到 glm5_2_nv (但那是 cc4101/hermes 配置层非 nv_gw, 需走 CC 基础设施侧).
2. **R2192 任务2 dump probe 覆盖率核查**: 本轮发现 30min DB 记 7 zombie 但 dump 文件未对应新增. 下轮若 kimi_nv zombie 持续, 查 handlers.py dump probe 是否只覆盖非流式检测点 (流式 zombie 走另一路径未 dump). 这是任务2 的盲点.
3. cc4101 fallback 趋势: R2137(3全救回)→R2148b(0)→R2149(0)→R2150(1)→本轮(0). 连续多轮 0 或全救回, 反馈循环健康.
4. 触发改动三阈值 (全满足才动): 30min 本域 SR 跌破 85% **或** cc4101 fallback >5/30min 且新 req id **或** 出现新错误类型.
5. 铁律: 只改 HM2 不改 HM1. HM1 peer R2296 (ms_gw UPSTREAM_TIMEOUT 300→120+KEY_COOLDOWN 55→30) 全 HM1 域非本域.
6. 下一 session 接棒若 STATE 又被清: 用 `git log --oneline -8` + DB 重建, **绝不 Read /tmp**.

## R2192 三任务总结 (本轮核证)
- 任务1 ✅ 已落地 (cache_read 38.8%)
- 任务2 ✅ 已落地 (27 sample, hypothesis A 强证伪; 本轮发现 dump probe 覆盖率盲点: 30min 7 zombie DB 记录 vs dump 文件不对应)
- 任务3 ⚠ 部分落地 (双 message_start 约束未解, spec 已就位)

## 参数快照 (docker exec nv_gw env, 与 R2150 逐项一致无漂移)
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
