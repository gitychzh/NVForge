# R-buffer-post1: R-buffer 部署后首轮验证 (2026-07-27 02:35 CST)

## 背景

主仓自 R2322 (STATE 基线) 后推进到 R-buffer (2026-07-27 部署, 外部监督者).
R-buffer 是 R2192 任务3 的根治级超集实现 (store-and-forward + stream judge +
ping 保活 + 同 key 重试), 已部署 HM2 nv_gw. 本轮是 R-buffer 落地后首个 cc2 长驻
巡检轮, 专职验证 R-buffer 实际效果 + cc2 链路健康度. 0 改动 0 restart.

## 改前数据 (02:35 CST 拉 30min 窗口, R-buffer 已生效)

### cc4101-primary (cc2 自己) 链路 — 根治性稳定
| 指标 | 实测 | 判读 |
|---|---|---|
| nv_requests 30min | 18×200, 0×502 | SR=100% (cc2 链路) |
| error_type | (无, 全 200) | 0 zombie, 0 ATE |
| cc4101 真 fallback 30min | 0 | 不需要 ms_gw 兜底 |
| cc_requests 6h status | 188×200, 0×499 | **BUG-A (499) 历史首次 6h 归零** |
| R-buffer buffer 30min | 17 START / 17 SUCCESS / 0 RETRY / 0 FAILURE | attempt 1 全部成功 |

### R-buffer 运行日志 (cc4101-primary, 全 glm5_2_nv)
```
NV-BUFFER-START: caller=cc4101-primary max_retries=3 stairs=[150,200,200] ping=30s total_deadline=580s
NV-BUFFER-ATTEMPT: attempt=1/3 timeout=150s caller=cc4101-primary input=84648c thinking=True
NV-BUFFER-VERDICT: attempt=1 verdict=success_tool_call content=158c reasoning=0c tool(id=True,args=True) fr=tool_calls done=True buffered=4833b elapsed=30s
NV-BUFFER-FLUSH: flushing 4833b to CC, verdict=success_tool_call
NV-BUFFER-SUCCESS: flushed 4833b after 1 attempt(s), elapsed=30439ms
```
20×VERDICT + 20×SUCCESS (2h), 0 RETRY/FAILURE → R-buffer 完美 store-and-forward,
NVCF 当前不发 Form B 僵尸流. cc2 无感 (TTFB 从 ~2s 变 ~流完成时间, cc2 无人值守
不影响 UX).

### 非 cc2 链路 (caller=unknown/hermes, kimi_nv passthrough)
| 指标 | 实测 | 判读 |
|---|---|---|
| nv_requests 30min (kimi_nv) | 24×200 / 7×502 | SR=77.4% (非 cc2 链路) |
| 502 根因 | kimi_nv all_tiers_exhausted → peer HM1 fallback 25s timeout | NVCF 账户配额, 非旋钮治 |
| zombie dump 2h | 4 个, 全 kimi_nv passthrough | 非 cc4101-primary 路径 |

## 任务2 zombie body dump 分析 (R2192 推测 A 终判)

dump 累计 440 个 (/app/logs/zombie_dumps/), 按 trigger:
- 385 passthrough_stream_zombie (hermes/openclaw/opencode, 非 cc2)
- 55 stream_zombie (to_anth 路径, 含 cc4101-primary 可能)

55 个 stream_zombie (cc2 可能走的路径) model 分布: 50×glm5_2_nv / 3×dsv4p_nv /
2×kimi_nv. field_analysis 汇总 (采样):
```
11× glm5_2_nv input=11464 msgs=2 tools=0 cm=ABSENT oc=ABSENT th=ABSENT
 9× glm5_2_nv input=9519  msgs=2 tools=0 cm=ABSENT oc=ABSENT th=ABSENT
 4× glm5_2_nv input=11643 msgs=2 tools=0 cm=ABSENT oc=ABSENT th=ABSENT
 1× glm5_2_nv input=94322 msgs=16 tools=27 cm=ABSENT oc=ABSENT th=ABSENT
 ... (全 cm/oc/th = ABSENT)
```

### 结论: R2192 推测 A 彻底证伪

**55/55 stream_zombie body 的 context_management/output_config/thinking 字段全 ABSENT**.
CC 注入的非标字段在经 cc4101 转换层 (anthropic→openai) 后已被剥离/转换, 到 nv_gw
的 oai_body 是干净 openai 标准 body. "CC 非标字段干扰 NVCF 致 zombie" 假设不成立.

zombie 真根因更可能是推测 D (NVCF 偶发空响应, 小输入更易触发) — 但无论根因如何,
R-buffer 已在 nv_gw 端根治 zombie 对 cc2 的影响 (判定+重试). 任务2 probe 使命完成
(证伪 A), 可降级为被动积累.

## 三阈值判定 → 冻结 (R-buffer-post1 NOP)

| 阈值 | 条件 | 实测 (cc2 链路) | 触发 |
|---|---|---|---|
| 1 | 30min SR<85% | 100% (18/18) | 否 |
| 2 | cc4101 fb>5 且新错误类型 | 0, 无新类型 | 否 |
| 3 | 新错误类型 | 0 错误 | 否 |

cc2 (cc4101-primary→glm5_2_nv→R-buffer) 链路无懈可击. 剩余 zombie/502 全在 kimi_nv
passthrough 流 (非 cc2, 非 cc2 优化目标). 无 config-tunable 改动能进一步改善 cc2 链路
而不引风险. 维持观测.

## env 快照 (02:35 CST 实测, 无漂移)
```
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180  TIER_COOLDOWN_S=180
KEY_COOLDOWN_S=60  MIN_OUTBOUND_INTERVAL_S=10  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
NVU_TIER_BUDGET_GLM5_2_NV=120  NVU_TIER_BUDGET_DSV4P_NV=180
NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_THRESHOLD=250000  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_MODELS=glm5_2_nv  NVU_EMPTY_200_FASTBREAK=3
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv  KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BUFFER_CALLERS=cc4101-primary  NVU_BUFFER_MAX_RETRIES=3
NVU_BUFFER_TIMEOUT_STAIRS=150,200,200  NVU_BUFFER_PING_INTERVAL_S=30
NVU_BUFFER_TOTAL_DEADLINE_S=580
```
注意: HM1 桥接轮 R2383-R2388 改的 KEY_COOLDOWN_S (HM1=10) 对 HM2 无关, HM2 仍 60.
config.py MODEL_INPUT_TOKEN_SAFETY: glm5_2_nv=1048576(1M).

## 容器状态
- nv_gw StartedAt=2026-07-26T17:24:05Z (R-buffer 部署重启, Up ~7.5h) RC=0
- cc4101 Up 9h (3 days ago created) RC=0
- ms_gw Up 5 days (重启热备就位, 本轮 0 调用)

## R2192 三任务进度 (本轮更新)
- 任务1 (cc4101 透传 cache_control): ✅ 落地持续生效
- 任务2 (nv_gw zombie body dump probe): ✅ 完成. 累计 440 sample, 55 个 stream_zombie
  全 cm/oc/th=ABSENT, 推测 A 证伪. probe 降级为被动积累 (不删, 留作 D 根因长观测)
- 任务3 (路径B zombie 内部重试): ✅ 被 R-buffer 取代 (更完整: store-and-forward + judge
  + ping + 同 key 重试). R-buffer 已根治 cc2 链路 zombie, 30min cc4101-primary 0 zombie.

## 下一轮建议
1. **盯 R-buffer 失败/重试**: 当前 0 RETRY 0 FAILURE. 一旦出现 NV-BUFFER-FAILURE 或
   attempt≥2, 说明 NVCF 开始发 Form B 僵尸流, 抓 dump 看 oai_body 特征 (验证 D).
2. **盯 499 回归**: R-buffer 让 6h 499 归零 (历史首次). 一旦 499 回归 >5/6h, 说明
   R-buffer 的 ping 保活或 total_deadline 兜底失效, 优先查.
3. **kimi_nv passthrough zombie** (非 cc2): 5 个 dump 全 cm/oc/th=ABSENT. 若需进一步
   推进根因, 走 NVCF 侧 (非旋钮治), 或评估 R-buffer 是否扩展到其它 caller (谨慎,
   hermes/openclaw 流式 UX 对 TTFB 敏感, buffer store-and-forward 会增延迟).
4. 长驻机制: 每 30min touch heartbeat (watchdog 15min); 改.py 触发 R-guard.
5. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 40007 (重启热备), 只改 HM2, 写入仓库.
