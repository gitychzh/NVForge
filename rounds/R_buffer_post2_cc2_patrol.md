# R-buffer-post2: R-buffer 部署后第二轮巡检 (2026-07-27 03:53 CST)

## 背景

新 session 接棒 STATE.md (停在 R2322, 但主仓 git HEAD 已到 R2391). 中间 R2322→R2391 的轮次
(R2326 / R-buffer / R-buffer-post1 / R2382~R2391 HM1 桥接) 本 session 不在场, 靠 git log + DB 重建认知.
本轮目标: 拉当前 30min 数据, 确认 R-buffer 机制持续有效, 判三阈值决定改不改.

## 数据 (03:33-03:53 CST = 19:33-19:53 UTC, 本轮实测)

### nv_gw 整体 30min
- nv_requests: 68×200 / 10×502 → SR=87.2% (78 total)
- errors: 8× zombie_empty_completion + 2× all_tiers_exhausted
- **cc4101 真 fallback = 0** (docker logs cc4101 --since 30m grep FALLBACK-OK = 0)
- nv_gw internal ms_fb: 当前 30min 窗口 grep MS_FALLBACK=0 (breaker 未 OPEN)

### 关键拆分: 10 个 502 全不是 cc2
| caller | mapped_model | 200 | 502 | 说明 |
|---|---|---|---|---|
| cc4101-primary | glm5_2_nv | 42 | 0 | **cc2 自己, 100% 成功** |
| unknown | kimi_nv | 28 | 10 | 别的 agent (agent_type=_nv), 走 passthrough 非 buffer |

- 10 个 502 明细: 全 `caller=unknown, mapped_model=kimi_nv, agent_type=_nv`, input 135-160K chars,
  集中在 19:33-19:49 UTC burst. **不是 cc2 流量, 是别的 agent 用 kimi_nv 撞 zombie/ATE.**
- kimi_nv 不是 cc2 默认 (cc2 默认 glm5_2_nv, NVU_BUFFER_CALLERS=cc4101-primary 只护 cc2).

### cc2 (cc4101-primary) 6h 全景
- 160×200 / 3× zombie_empty_completion / 1× buffer_exhausted → SR=160/164=97.6%
- buffer: 102× NV-BUFFER-SUCCESS (6h), 0 retry failure 在当前容器周期
- 3 zombie + 1 buffer_exhausted 全在上一个容器周期 (7-26 晚, 当前 nv_gw 容器 7-27 01:24 CST 启动,
  docker logs 搜不到这些 req, DB created_at 在容器启动前). 当前周期 cc2 链路 0 失败.

### buffer_exhausted 模式分析 (上一个周期 req=4c7c661c, 已查日志)
```
02:43:01 NV-GLM52-CHAIN-FALLBACK STAGE1_CHAIN_FAIL → ms_gw fallback OK 3937ms
02:43:05 NV-BUFFER-START attempt=1
02:43:35 NV-BUFFER-PING-FAIL "CC gone during ping: Broken pipe" → verdict=zombie_partial reason=client_gone_ping
02:43:35 attempt=2 → 同样 client_gone_ping @133s
02:44:07 attempt=3 → 同样 client_gone_ping @175s
02:44:49 NV-BUFFER-EXHAUSTED all 3 attempts failed
```
**关键**: 这 3 次 buffer 重试全败在 `client_gone_ping` (CC 客户端 broken pipe), **不是 NVCF zombie**.
揭示 buffer 模式理论风险: TTFB=流完成时间 (几十秒), CC SDK 若在 buffer 期间主动断 (broken pipe),
ping 写不进 socket → buffer 重试无效. 这是 CLAUDE.md BUG-A (cc2 SDK ~131s 客户端首字节墙) 的变体.
**当前周期未复现**, 属观察项, 不属改码项 (ping 机制本身正确, 问题是 CC 客户端断了).

## 容器状态 (无漂移)
- nv_gw StartedAt=2026-07-26T17:24:05Z (7-27 01:24 CST) RC=0 Up 2h, restarts=0
- cc4101 StartedAt=2026-07-23T07:38:11Z RC=0 Up 10h
- ms_gw Up 5d (重启热备就位)

## nv_gw env 快照 (docker exec 实测, R-buffer 旋钮已落地)
```
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180  TIER_COOLDOWN_S=180
KEY_COOLDOWN_S=60  MIN_OUTBOUND_INTERVAL_S=10  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
NVU_TIER_BUDGET_GLM5_2_NV=120  NVU_TIER_BUDGET_DSV4P_NV=180
NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_THRESHOLD=250000  NVU_BIG_INPUT_COOLDOWN_S=180  NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
NVU_BUFFER_CALLERS=cc4101-primary  NVU_BUFFER_MAX_RETRIES=3
NVU_BUFFER_TIMEOUT_STAIRS=150,200,200  NVU_BUFFER_PING_INTERVAL_S=30  NVU_BUFFER_TOTAL_DEADLINE_S=580
NVU_STREAM_FULL_BUFFER=0  KEY_AUTHFAIL_COOLDOWN_S=60
```
/health: `nv_default_model=glm5_2_nv` ✓ (三处一致: cc4101 PRIMARY_UPSTREAM_MODEL / nv_gw / config.py)

## R2192 三任务进度
- 任务1 (cc4101 透传 cache_control): ✅ 落地持续生效 (cache_read 历史验证 38.8%)
- 任务2 (nv_gw zombie body dump probe): ✅ 终判完成 (R-buffer-post1: 440 dump, 55 stream_zombie
  全 cm/oc/th=ABSENT, 推测A证伪). 本轮无新 zombie (cc2 当前周期 0 失败), 不再累积.
- 任务3 (路径B zombie 内部 key 重试): ⚠ **被 R-buffer 取代/部分取代**. R-buffer 的 buffer-then-flush
  + 同 key 重试 (stairs 150/200/200) 已覆盖 cc2 的 Form B zombie 根治场景, 比 CLAUDE.md 原任务3
  设计的 converter 内部重试更彻底 (buffer 在 converter 之前, 能废弃半截流重来).
  **R2192 任务3 spec 的 converter feed_chunk 守卫重试路径, 在 R-buffer 已落地后冗余度上升,
  暂搁置, 除非未来出现 buffer 覆盖不到的 zombie 路径 (如非 cc4101-primary caller).**

## 三阈值判定 → 冻结 (R-buffer-post2 NOP)
| 阈值 | 条件 | 实测 | 触发 |
|---|---|---|---|
| 1 | 30min cc2链路 SR<85% | cc2=100% (42/42) | 否 |
| 2 | cc4101 fb>5 且新错误类型 | 0, 无新类型 | 否 |
| 3 | 新错误类型 | 全 known (zombie/ATE, 且非cc2) | 否 |

nv_gw 整体 87.2% 偏低, 但根因是 kimi_nv/unknown agent 的 zombie+ATE (非旋钮治, NVCF 上游/账户配额),
非 cc2 链路问题. cc2 (cc4101-primary) 链路 100% 健康, R-buffer 完美工作. 无 config-tunable 改动
能在不引风险前提下降 kimi_nv/unknown 的 502 (那是别的 agent 的模型/tier 选择问题, 不是 HM2 nv_gw 旋钮).
**维持观测, 0 改动 0 restart.**

## 下一轮该做什么
1. 继续巡检. 盯 cc2 (cc4101-primary) 链路是否保持 100%, 若现 zombie/buffer_exhausted 复现, 看
   是 NVCF Form B (buffer 该兜但漏) 还是 client_gone_ping (CC SDK 断, 非 nv_gw 病).
2. 盯 buffer_exhausted 的 client_gone_ping 模式: 若持续高频, 说明 buffer TTFB 长 + CC SDK 早断
   的结构性矛盾显现, 需评估 NVU_BUFFER_TIMEOUT_STAIRS 首阶 150s 是否过长 (但太短又误杀正常长流,
   谨慎). 当前不治.
3. kimi_nv/unknown agent 的 502: 不是 cc2 责任, 但若连续多窗口污染 nv_gw 整体 SR, 可考虑给
   kimi_nv caller 也开 buffer (NVU_BUFFER_CALLERS 加 unknown? 但 unknown 是默认兜底标签, 需先查
   那个 agent 是谁). 暂不动.
4. 长驻机制: 每 30min touch ~/.claude/cc2.heartbeat (watchdog 15min); 每子任务刷 STATE;
   改 .py 触发 R-guard (py_compile+restart+health).
5. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 40007 (重启热备), 只改 HM2, 写入仓库, 尽量多走
   glm5_2_nv 少 fallback.

## 本轮动作
- 0 改动 / 0 restart / 0 .bak
- touch heartbeat
- 写 rounds/R_buffer_post2_cc2_patrol.md
- 更新 STATE.md (基线从 R2322 拉到 R-buffer-post2, 补齐 R2326/R-buffer/R-buffer-post1 认知)

HM2 only. 未 Read 任何 /tmp 文件. 未碰 40007/ms_gw 源码.
