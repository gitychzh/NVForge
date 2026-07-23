# R2158 (hm2_cc2) — NOP 巡检轮 91 连续第91 NOP

- 日期: 2026-07-23
- 主机: HM2 only (不碰 HM1, 铁律)
- 类型: NOP 巡检轮, 0 改动 0 restart
- 前轮: R2157 (commit 91981ee, 第90 NOP, 30min 89req/94.4% SR, fallback=0)

## 数据 (HM2, 30min window, ~18:47 CST / 10:47 UTC 时点)

### 30min 总览
- 93 req / 89 OK(200) / 4 错(502) → **SR = 95.7%** (比上轮 94.4% 上升)
- by model:
  - **glm5_2_nv 67/69 = 97.1%** (本域主链路极稳; 2 错 stream_absolute_cap mid-stream 背景波首字节已收)
  - **kimi_nv 22/24 = 91.7%** (R2286/R2292 新默认模型过渡期阵痛收尾中; 2 错 = 2 all_tiers_exhausted, NVCF 上游连接类非旋钮能治)
- error_type: 2 stream_absolute_cap(glm5_2_nv) + 2 all_tiers_exhausted(kimi, NVCF function ATE 上游已知良性)
- 无 content_filter / timeout / conn / 429 / zombie_empty_completion
- host_machine 全 HM2 本域

### ⚠ kimi_nv 过渡期 zombie 跟踪信号
- 30min kimi_nv **0 zombie** (上轮 1 个, 上上轮 4-5 个) → 过渡期阵痛进一步收尾, 趋近结束
- 2 错全 ATE (NVCF function 上游连接类), 非新增错误类型, 非旋钮能治

### cc4101 30min fallback (负向核心指标)
- **fallback = 0** ✅ 零数据空洞, 连续多轮最佳, 0 真中断, 0 双失败
- 与 R2157 (fallback=0) 持平, 无恶化

### nv_gw 内部 NV-ANTH-BREAKER-FAIL (R1719 设计)
- 30min DB 记录的 2 个 glm5_2_nv stream_absolute_cap (req=8de6558d @10:19 UTC, a08c7f3c @10:31 UTC) 均为 mid-stream 背景波首字节已收类
- nv_gw 日志确认对应 state=('CLOSED', 3, 0) 未 OPEN (从 R2157 延续, 容器本地 CST 时间戳 18:19/18:31 与同一批请求对应)
- breaker 远未到 OPEN 阈值
- 注意: fallback_occurred=true (nv_gw 内部 NV-MS-FB tier 兜底) ≠ cc4101 fallback. 本轮 cc4101 fallback=0.

### 参数误杀类 (全 0) ✅
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

### BUG-A 499 盲点 (cc_requests 6h)
- client_gone_mid_stream = **31 / 6h** (与 R2155/R2156 持平, R2289 副作用受益持续)
- timeout=164/6h (cc4101 自身非本域); server_5xx=6; stream_total_deadline=1
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非 nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

## 容器状态 (漂移信号核, docker inspect 实测)
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2157 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0, 与 R2157 一致)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- env 关键参数与 R2157 逐项一致, **无参数漂移**

## R2192 三任务进度 (巡检轮必报)
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (27 sample, hypothesis A 强证伪 — zombie body 不普遍含非标字段). 容器 /tmp/zombie_*.json 本轮窗口内 0 个 zombie 无新增素材
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, 待实施). 本轮 kimi zombie=0 素材不足窗口, 未实施

## 决策: NOP 巡检冻结, 不改代码
三触发改动阈值全不满足:
- SR 95.7% > 85% ✅
- cc4101 fallback 请求数 0 < 5 ✅ (零数据空洞 0 真中断)
- 无新增错误类型 ✅ (glm5_2_nv 2 cap 历史多轮已现的中流背景波; kimi 2 ATE 是 R2286 过渡期已知非旋钮可治上游类且 zombie 已归零收尾明显)

四重佐证 nv_gw 稳:
1. 4 错全上游无害类 (glm5_2_nv 2 cap mid-stream 背景 + kimi 2 ATE 过渡期阵痛收尾)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (2 条 CLOSED(3,0) 远未到阈值)
4. 参数无漂移 (容器未重建 env 与 R2157 逐项一致)

改了反而破坏稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 + env 无漂移.
容器 StartedAt (docker inspect 实测): nv_gw=07-22T15:10:34Z (连续多轮未重建) / cc4101=07-23T07:38:11Z / ms_gw=07-21T12:50:09Z.

## HM2 only
