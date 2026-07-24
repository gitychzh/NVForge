# R2191 — hm2_cc2 NOP 巡检轮 114 (连续第 114 NOP)

> 全新 session 接棒. STATE.md 停 R2188, `git pull` 后 HEAD=92eae6b (R2190, 连续第 113 NOP).
> 以 git log + DB 重建, 本轮 hm2_cc2 续 R2191. 未 Read 任何 /tmp 文件.

## 数据 (HM2, 30min window ~13:00-13:30)

**nv_requests 30min**:
- 120 req / 119 OK(200) / 1 错(502) → **SR = 99.2%**
- by model: **glm5_2_nv 119/120 = 99.2%** (主力, 全本域流量; 唯一 1 错 stream_absolute_cap mid-stream 背景波)
- kimi_nv 0 req (过渡期收尾, 流量全汇 glm 连续多轮)
- claude-opus-4-8 0 req (本轮无 passthrough 流量)
- error_type (nv_requests 层): stream_absolute_cap × 1
- 无 content_filter / timeout / conn / 429 / all_tiers_exhausted (nv_requests 层)
- host_machine 全 HM2 本域

**nv_tier_attempts 30min (上游 NVCF 连接类, 非旋钮能治)**:
- pexec_success 98 / pexec_429 21 / pexec_empty_200 5 / pexec_SSLEOFError 2 / pexec_conn_RemoteDisconnected 2 / pexec_500 1
- pexec_429=21 (R2190=17 略升, 仍 NVCF 账户级配额非旋钮能治; KEY_COOLDOWN=60/MIN_OUTBOUND=10 已保守, 改大反触发更多 primary timeout 恶化)
- pexec_empty_200=5 (R2190=7 略降)

**cc4101 30min fallback (负向核心指标)**:
- **真 fallback = 0** (grep "FALLBACK|FALLBACK-OK|切到 ms_gw|PRIMARY-FAIL|SKIP-CIRCUIT|circuit|BREAKER" 全 0)
- **0 真中断** (比 R2190=1 更干净, 全部 nv_gw 内部 ms_fb 兜底, 0 冒 cc4101 层)

**nv_gw 内部 NV-MS-FB-BREAKER (R1719 设计)**:
- NV-MS-FB-BREAKER-OPEN **2 事件** (13:32:55 req=602e503e state=('OPEN',5,26); 13:33:10 req=14ac239b state=('OPEN',5,11))
- 远低于 R2190=24 (R2190 两波风暴 12:38+12:43-44, 本轮仅 2 单点, 活跃度大幅回落)
- 全自愈模式 (OPEN → ms_gw direct serve → 衰减 → CLOSED), 0 冒 cc 层 (cc4101 fallback=0 证实)
- NV-ANTH-BREAKER-FAIL **1 条** (nv_breaker=CLOSED 未真 OPEN, 设计行为, 对应 mid-stream soft-fail)

**参数误杀类 (全 0)** ✅:
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR / client_gone = 0

**BUG-A 499 盲点 (cc_requests 6h)**:
- client_gone_mid_stream = **48 / 6h** (R2190=50 略降, R2289 副作用 SDK 131s 客户端首字节墙结构性基线区间波动 42-52)
- stream_total_deadline = 2/6h
- 根因 = cc2 SDK ~131s 客户端首字节墙结构性限制, 非 nv_gw 旋钮能治, 已定性多轮, 属 CLAUDE.md BUG-A 待查项

**容器状态 (漂移信号核, docker inspect 实测)**:
- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], **default=glm5_2_nv** ← R2286 改默认 kimi_nv 但 nv_gw nv_default_model 仍 glm5_2_nv 过渡期双线并行)
- nv_gw RestartCount=0 StartedAt=**2026-07-23T18:05:17Z** (连续多轮 RC=0 未重建, 无漂移) ← 与 R2188-R2190 逐项一致
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)
- docker ps: nv_gw Up 12h / cc4101 Up 22h / ms_gw Up 2d / logs_db Up 7d
- env 关键参数与 R2190 逐项一致, **无参数漂移**

**R2192 三任务进度 (巡检轮必报)**:
- 任务1 (cc4101 透传 cache_control): ✅ 已落地 (cache_read 38.8% 历史验证, 持续生效)
- 任务2 (nv_gw 抓 zombie body dump probe): ✅ 已落地 (累计 47 sample, hypothesis A 强证伪). 本轮窗口 0 zombie, 未触发新增 dump
- 任务3 (路径B zombie 内部重试): ⏳ 部分 (双 message_start 约束未解, converter feed_chunk 守卫已核证, spec + 双路径骨架已就位 ~/cc_ps/cc2_repair_self/specs/, 待实施). 本轮 0 zombie 素材严重不足窗口 (需 ≥5 连续多轮才值得推进), 未实施. 是下一推进点.

## 决策: NOP 巡检不改代码

STATE 三触发改动阈值全不满足:
1. SR 99.2% > 85% ✅
2. cc4101 fallback 请求数 0 < 5 ✅ (且全救回, 0 真中断, 比 R2190=1 更干净)
3. 无新增错误类型 ✅ (NV-MS-FB-BREAKER OPEN 2 是 R2179-R2190 连续多轮已知设计行为, internal ms_fb 兜底 0 冒 cc 层)

四重佐证 nv_gw 稳:
1. nv_requests 99.2% SR (1 错全 stream_absolute_cap mid-stream 背景波, tier 错误全 NVCF 上游连接类无害)
2. 无参数误杀 (全 0)
3. breaker 不真停 OPEN (2 OPEN 事件 13:32-33 单点, 全自愈回 CLOSED, NV-ANTH-BREAKER-FAIL=1 未真 OPEN)
4. 参数无漂移 (容器未重建 env 与 R2190 逐项一致, nv_gw StartedAt 连续多轮稳定 07-23T18:05)

改了反而破坏稳定��.

## 验证

0 改动 0 restart 无需验证改动.
- curl /health ok (passthrough, nv_num_keys=5, default=glm5_2_nv)
- docker ps 全栈 Up (nv_gw Up 12h / cc4101 Up 22h / ms_gw Up 2d / logs_db Up 7d)
- 容器 RC=0 (nv_gw/cc4101/ms_gw 全 0)
- env 无漂移 (逐项比对 R2190 一致)

## 参数快照 (本轮确认无漂移, docker inspect 实测)

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

容器 (docker inspect 实测):
- nv_gw RestartCount=0 StartedAt=2026-07-23T18:05:17Z (连续多轮未重建, RC=0, env无漂移)
- cc4101 RestartCount=0 StartedAt=2026-07-23T07:38:11Z (RC=0)
- ms_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (RC=0)

HM2 only. 未碰 proxy/ms-gw/. 未 Read 任何 /tmp 文件.
