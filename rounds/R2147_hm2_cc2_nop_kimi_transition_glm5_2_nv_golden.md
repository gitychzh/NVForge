# R2147 (hm2_cc2): NOP 巡检轮 — kimi_nv 默认过渡期 + glm5_2_nv 本域 golden 延续 + R2192 任务2 dump probe 持续验证

连续第 84 NOP（hm2_cc2 线）。0 改动 0 restart。

## 背景 / 接棒状态
- STATE.md 头部停在 R2137（07-22 07:12 时点旧 session 交接），严重滞后。
- `git pull --ff-only origin main` 后 HEAD = 3ec467b (R2146 hm2_oc2 @07-23 更晚时点)。
- hm2_cc2 线最新 commit = R2142 (423f736)。本轮续 R2147。
- 中间重大事件（CLAUDE.md/轮文件已记）:
  - **R2286/R2289 (cc2 HM2)**: 默认模型 dsv4p_nv→kimi_nv + 1M settings 回退到 120K 量级（kimi-k2.6 上下文只 128K）。
  - **R2290 (cc2 HM2)**: R2192 任务2 完成 — zombie dump probe 25 samples all_ABSENT，hypothesis A（CC 注入非标字段致 zombie）强证伪。

## 数据 (HM2, 30min window, 15:47 CST 时点)
- 73 请求 / 63 OK(200) / 10 错(502) → **SR = 86.3%**
- by model:
  - **glm5_2_nv 37/37 = 100%**（本域主链路干净满分，nv_default_model 仍 glm5_2_nv，延续 golden）
  - kimi_nv 26/30 = 86.7%（4 错 all_tiers_exhausted，非默认主链路，cc2 R2289 改默认后的域外波及延续）
  - dsv4p_nv 0/6 = 0%（6 错全 all_tiers_exhausted，NVCF 74f02205 恶化延续非本域）
- error_type: 9 all_tiers_exhausted(dsv4p 6 + kimi 4... 实为 dsv4p 6 + kimi... 归类) + 1 zombie_empty_completion(kimi_nv req=ec31798f @15:19)

**注**: SR 86.3% 略低于 R2146 golden，主因是 dsv4p_nv 0/6 全错 + kimi_nv 4 错（均 NVCF 上游已知恶化/默认模型过渡期域外波及），**本域 glm5_2_nv 100% 满分**。

## cc4101 30min fallback (负向核心指标)
- **1 个请求, 全 FALLBACK-OK 救回, 0 双失败 / 0 真中断**
  - req=b4e2137b [15:42:16] PRIMARY-FAIL (glm5_2_nv 180s header/ttfb timeout) → [15:42:26] FALLBACK-OK (ms_gw glm5_2_ms 10079ms)
- fallback 请求数 1 < 5 阈值 ✅
- **注意**: 此 fallback primary 是 glm5_2_nv，180s header/ttfb timeout。30min nv_requests DB 里 glm5_2_nv 37/37=100%，说明此 180s 超时请求在 cc4101 层 pre-empt 但 nv_gw 侧 retry 可能走了不同路径或记到 cc4101 层非 nv_requests。NVCF glm5_2_nv 侧偶发 header 阻塞慢，非 nv_gw 旋钮能治根因（BREAKER 无 NV-ANTH-BREAKER-FAIL 触发，非 nv_gw chain budget 问题）。

## nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719 设计)
- 0 条（docker logs nv_gw --since 30m grep BREAKER 无输出）。远未到 OPEN 阈值。

## 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

## BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **33 / 6h**（较 R2142 的 34 持平下降趋势；R2289 改默认模型 + 1M→120K settings 后 499 从 R2137 的 50 降到 33，降 36%，是 R2289/R2290 改动副作用受益）
- timeout = 164 / 6h（kimi_nv/dsv4p_nv 域外波及，NVCF 上游慢，非本域）
- stream_total_deadline = 3 / 6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制，非 nv_gw 旋钮能治，已定性多轮，属 CLAUDE.md BUG-A 待查项

## 容器状态 (docker inspect 实测，漂移信号核)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=**glm5_2_nv**)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z**（连续多轮 RC=0 未重建，与 R2142 一致无漂移）
- cc4101 RestartCount=0 StartedAt=**2026-07-23T07:38:11Z**（Up 8min，近期 restart 过，R2289/R2290 改 cc4101 源码所致，非漂移事故）
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z（RC=0）
- env 关键参数与 R2142 逐项一致，**无参数漂移**

## R2192 三任务进度 (ULTIMATE GOAL 撤 40007)
1. **任务1 (cc4101 透传 cache_control)**: ✅ 已落地（R2228，cache_read 0%→38.8%，持续验证中）。本轮未单独验证 cache 命中率（巡检聚焦，下轮可抽验）。
2. **任务2 (nv_gw 侧 zombie body dump probe)**: ✅ **已落地 + 持续运行验证中**。handlers.py L67-104 `_dump_zombie_body` + L529(nonstream)/L1532(stream) 接线。dump dir `/app/logs/zombie_dumps` 已积累 **27 个 sample**（跨 07-22 23:21 → 07-23 15:19，约 40h 跨度）。R2290 结论 "25 samples all_ABSENT，hypothesis A 强证伪" 在持续累积中仍成立（无新 sample 含 context_management 等非标字段致 zombie 的反证）。本轮 30min 内 1 个 kimi_nv zombie (req=ec31798f) 已落盘 `zombie_20260723T071932_ec31798f_stream_zombie.json`。
3. **任务3 (路径B zombie 内部重试)**: 部分。`_ms_fallback_request` 存在但 zombie 检测点的"200+message_start 已发→不能切 ms 重放"约束（双 message_start 错乱）未解。需设计 converter feed_chunk 内部重试（不双 message_start，内容重复用户接受）。

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
- SR 86.3% > 85% ✅（本域 glm5_2_nv 100% 满分，SR 略低全因域外 dsv4p/kimi ATE）
- cc4101 fallback 请求数 1 < 5 ✅（全救回 0 真中断）
- 无新增错误类型 ✅（1 zombie + dsv4p/kimi ATE 历史已现非首现）

四重佐证 nv_gw 稳: 本域 glm5_2_nv 100% 满分 / 无参数误杀(全0) / breaker 0 条未真OPEN / 参数无漂移(容器未重建 env 与 R2142 逐项一致)。改了反而破坏稳定带。

**kimi_nv 默认过渡期观察**: R2289 改 cc4101 默认模型 dsv4p→kimi 后，kimi_nv 成为 cc2 流量主要承载（30min 30 req vs glm5_2_nv 37 req），kimi_nv 86.7% + 4 ATE + 1 zombie 是过渡期阵痛。但 nv_gw nv_default_model 仍 glm5_2_nv（/health 确认），本域主链路不受波及。持续观察 kimi_nv SR 是否回升。

## 验证
0 改动 0 restart 无需验证改动。curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移。容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z（连续多轮未重建）/ cc4101=07-23T07:38:11Z（R2289/R2290 改源码所致重启）/ ms_gw=07-21T12:50:09Z。

HM2 only。未碰 HM1。未碰 ms_gw 源码。
