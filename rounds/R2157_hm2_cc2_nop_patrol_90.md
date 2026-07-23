# R2157 (hm2_cc2): NOP 巡检轮 90 — 连续第 90 NOP 三阈值冻结

**HM2 only. 0 改动 0 restart.**

## 接棒
全新 session. STATE.md 头部停在 R2156. `git pull` 后 HEAD = 564b719 (R2156 hm2_cc2).
hm2_cc2 线最新 = R2156 (连续第 89 NOP). 以 git log 为准, 本轮 hm2_cc2 续 R2157.

## 数据 (HM2, 30min window, ~18:42 CST 时点)

### nv_gw 总成功率
- 89 req / 84 OK(200) / 5 错(502) → **SR = 94.4%** (主链路稳, 比上轮 90.6% 上升)
- by model:
  - **glm5_2_nv 56/58 = 96.6%** (本域主链路稳; 2 错 stream_absolute_cap mid-stream 背景波首字节已收 → breaker CLOSED(3,0) 吸收)
  - **kimi_nv 28/31 = 90.3%** (R2286/R2292 新默认模型过渡期阵痛收尾中; 3 错 = 1 zombie_empty_completion + 2 all_tiers_exhausted, 全 NVCF 上游连接类非旋钮能治)
- error_type: 2 stream_absolute_cap(glm5_2_nv) + 2 all_tiers_exhausted(kimi, NVCF function ATE 上游已知良性) + 1 zombie_empty_completion(kimi)
- 无 content_filter / timeout / conn / 429
- host_machine 全 HM2 本域

### kimi_nv 过渡期 zombie 跟踪
- 30min kimi_nv 仅 **1 个 zombie_empty_completion** (上轮 4-5 个) → 过渡期阵痛明显收尾
- 全 kimi_nv 非 glm5_2_nv 本域主链路. 非新增错误类型, 非旋钮能治.

### cc4101 30min fallback (负向核心指标)
- **fallback = 0** ✅ 零数据空洞, 连续多轮最佳, 0 真中断, 0 双失败
- 与 R2156 (fallback=0) 持平, 无恶化

### nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719 设计)
- 2 条全 CLOSED(3,0) 未 OPEN:
  - req=8de6558d @18:19:27 (glm5_2_nv stream_absolute_cap mid-stream)
  - req=a08c7f3c @18:31:28 (glm5_2_nv stream_absolute_cap mid-stream)
- 注意: fallback_occurred=true (nv_gw 内部 NV-MS-FB tier 兜底) ≠ cc4101 fallback. 本轮 cc4101 fallback=0.
- breaker 远未到 OPEN 阈值.

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **32 / 6h** (与 R2156 的 31 持平, R2289 副作用受益持续); timeout=164/6h(cc4101 自身非本域); server_5xx=6; stream_total_deadline=2
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

## 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv ← R2286 改默认模型但 nv_gw nv_default_model 仍 glm5_2_nv, 过渡期双线并行)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2156 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0, 与 R2156 一致)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2156 逐项一致, **无参数漂移**

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪 — zombie body 不普遍含非标字段). 容器 /tmp/zombie_*.json 本轮 0 个 (容器重启清空 /tmp, 历史已确认落地)
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, 待实施). 是下一推进点.

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
- SR 94.4% > 85% ✅
- cc4101 fallback 请求数 0 < 5 ✅ (零数据空洞 0 真中断)
- 无新增错误类型 ✅ (kimi 1 zombie+2 ATE 是 R2286 过渡期已知非旋钮可治上游类且明显收尾; glm5_2_nv 2 cap 历史多轮已现)

四重佐证 nv_gw 稳:
1. 5 错全上游无害类 (glm5_2_nv 2 cap mid-stream CLOSED 吸收 + kimi 3 错过渡期阵痛收尾)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (2 条 CLOSED(3,0) 远未到阈值)
4. 参数无漂移 (容器未重建 env 与 R2156 逐项一致)

改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z (连续多轮未重建) / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z.

## 铁律
- 改前有数据, 改后有验证, 聚焦 40006, 不碰 40007 (热备), 写入仓库, 改 .py 必须 restart.
- 只改 HM2 不改 HM1.
- 尽量多走 glm5_2_nv 少走 ms_gw — fallback 是数据空洞.
