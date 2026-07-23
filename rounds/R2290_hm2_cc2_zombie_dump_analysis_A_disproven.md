# R2290 (cc2, HM2 only): R2192 任务2 完成确认 + zombie dump 25 样分析 → 推测 A 强力否定 (NOP 数据分析轮)

## 背景

全新 session 接棒. STATE.md 头部停在 R2137 (07-22 旧 session 交接), 但 `git pull` 后 HEAD =
58fd2f8 (R2289 cc2 默认模型改 kimi_nv, 07-23 15:10). STATE 严重滞后. 中间多轮由其他 session
完成, 关键演进: R2287 (glm5_2_nv→dsv4p_nv, 因 glm5.2 当日全 0% 挂窗) → R2289 (dsv4p_nv→kimi_nv,
因 dsv4p ATE 也高 + kimi 裸测 100%). 当前 cc2 默认模型 = **kimi_nv** (cc4101 PRIMARY_UPSTREAM_MODEL).

本轮目标: 接棒后第一件事是搞清楚 R2192 三任务当前进度 (CLAUDE.md 持久指令). 数据驱动查源码
发现 **任务2 早已落地** (handlers.py `_dump_zombie_body` 函数 + 两个 zombie 检测点接线, 注释
标 R2257 t2 wire), 且 /app/logs/zombie_dumps 已积累 **25 个 dump 文件**. 本轮做完整分析.

## 数据 (改前必有数据, HM2, 时点 07-23 ~15:20 CST)

### 30min nv_gw 成功率 by model (当前 kimi 为 cc2 默认)

| model | total | ok | SR | avg_ttfb | avg_dur |
|---|---|---|---|---|---|
| glm5_2_nv | 34 | 34 | **100.0%** | 46.9s | 57.1s |
| kimi_nv | 20 | 16 | **80.0%** | 27.3s | 31.9s (最快) |
| dsv4p_nv | 20 | 10 | 50.0% | 49.3s | 79.1s |

- 整体 30min SR = 60/74 = 81.1% (dsv4p ATE 拖累)
- **主链路视角**: glm5_2_nv 100% (恢复, 风暴窗已滑出 6h), kimi_nv 80% (新默认, 4 错 = 2 ATE + 2 zombie)

### 30min 错误分类

| error_type | count | model 归属 |
|---|---|---|
| all_tiers_exhausted (ATE) | 13 | dsv4p 11 + kimi 2 |
| zombie_empty_completion | 2 | kimi 2 (req f195eb16 @07:11, ec31798f @07:19) |

- 无 content_filter / timeout / conn / 429
- 2 kimi zombie: input=14272c, output_tokens=2012/1383 (有部分 flush), duration 28.4s/19.5s

### cc4101 fallback (负向核心指标)

- 30min: **2 次 PRIMARY-FAIL, 全 FALLBACK-OK 救回, 0 真中断**
  - req=6165ee5b [15:13:30] kimi_nv 502 after 71s → ms_gw glm5_2_ms 救回 36.9s
  - req=5e939080 [15:16:00] kimi_nv 502 after 71s → ms_gw glm5_2_ms 救回 7.6s
- 6h: 4 PRIMARY-FAIL / 2 FALLBACK-OK (全在 15:10 kimi 切换后, 即 30min 窗内; 风暴窗期的
  PRIMARY-FAIL 多为 SKIP-CIRCUIT 不走 ms fallback)
- fallback 请求数 2 < 5 阈值 ✅ (全救回 0 真中断)

### NV-ANTH-BREAKER-FAIL (30min)

- 0 条 (nv_gw 日志 grep "breaker-fail|NV-ANTH-BREAKER" = 0)
- nv_gw 内部有 NV-MS-FB-ATTEMPT/SERVED (nv_gw 自身 ms 兜底, R1719 设计, ≠ cc4101 fallback)

### BUG-A 499 (cc_requests 6h)

- client_gone_mid_stream = **32 / 6h** (较 R2137 STATE 的 50/6h **下降 36%**)
- 根因 = cc2 SDK ~131s 客户端首字节墙 (CLAUDE.md BUG-A 待查项, 非本域)
- 下降原因推测: R2289 默认模型改 kimi (128K ctx) + settings 回退到 120K, input 变小,
  auto-compact 触发频率下降 → 中途断流减少. **正反馈: kimi 切换附带减 499**.

### 容器状态 (docker inspect 实测, 无漂移)

- nv_gw /health ok (passthrough, nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv)
- nv_gw StartedAt=**2026-07-22T15:10:34Z** (连续多轮 RC=0 未重建, 与 R2137 一致无漂移)
- cc4101 StartedAt=2026-07-22T14:28:23Z (R2289 recreate 后)
- env 关键参数与历史逐项一致, **无参数漂移**

## R2192 三任务进度核查 (本轮核心交付)

### 任务1: cc4101 透传 cache_control → 已落地 (R2228/R2288 记录)
- 走 nv_gw 读 NVCF prompt_tokens_details.cached_tokens 路径, cc4101 passthrough 已透传
- cache_read 命中率 0%→38.8% (R2228 记录). 本轮未深查 cc4101 cache 日志 (grep 无输出,
  可能日志级别不够或字段未打). 下轮可补查 jsonl usage 的 cache_read_input_tokens.

### 任务2: nv_gw zombie body dump probe → **已完全落地 + 25 样分析完成**

**源码核证** (handlers.py):
- L67-110: `_dump_zombie_body(oai_body, request_model, metrics, trigger)` 函数完整实现
  - dump 到 `/app/logs/zombie_dumps/zombie_<ts>_<rid>_<trigger>.json` (bind-mount 卷, 容器重启不丢)
  - 记录 field_analysis: context_management / output_config / thinking / reasoning_effort 的 repr 或 "ABSENT"
  - try/except 包裹, dump 失败不破坏请求
- L531: 非流式 zombie 检测点接线 (`trigger="nonstream_zombie"`)
- L1533: 流式主循环 zombie 检测点接线 (`trigger="stream_zombie"`)
- 注释标 "R2257 t2 wire" (R2192 函数早已存在但从未被调用 = 死代码, R2257 接线激活)

**25 个 dump 文件分析** (`docker exec nv_gw python3` 聚合):

| 维度 | 结果 |
|---|---|
| 总文件数 | 25 |
| 模型分布 | glm5_2_nv 20 / dsv4p_nv 3 / kimi_nv 2 |
| field_analysis 模式 | **all_ABSENT: 25 (100%)** |
| 有任何非 ABSENT 字段的 dump | **0** |
| input_chars 范围 | 9519 - 109297, avg 23722 |

**关键结论: R2192 推测 A (CC 非标字段 context_management/output_config/thinking/reasoning_effort 干扰 NVCF 导致 zombie) 被强力否定.**

- 25 个 zombie dump 跨 3 个模型 (glm5_2_nv 20 / dsv4p 3 / kimi 2), 四个嫌疑字段**无一例外全 ABSENT**
- 即 oai_body (nv_gw 收到的, 经 cc4101 anth_to_openai 转换后) 里根本没有这些字段
- 可能解释: (a) cc4101 转换层已剥离; (b) CC SDK 对这些模型/请求类型本就不发; (c) 字段在
  anthropic 侧而非 openai 侧 (oai_body 是转换后的, 字段名可能变了). 无论哪种, **字段不存在于
  到达 nv_gw 的请求里 = 不可能是 zombie 元凶**.
- 倾向 R2192 推测 D (上游间歇性空响应 / 样本特征) 或其他根因 (NVCF kimi/dsv4p/glm5 function
  自身偶发空 completion), 非 cc4101 字段干扰.

**zombie profile (6h, by model)**:

| model | zombie_cnt | min_input | max_input | avg_input | avg_out_tok |
|---|---|---|---|---|---|
| glm5_2_nv | 5 | 11643 | 381426 | 102503 | 85 |
| dsv4p_nv | 3 | 14272 | 14272 | 14272 | 0 |
| kimi_nv | 2 | 14272 | 14272 | 14272 | 1698 |

- dsv4p zombie: input 恒 14272c, **0 output_tokens** (纯空, 最严重)
- kimi zombie: input 恒 14272c, 1698 output_tokens (有部分 flush, 可重试续)
- glm5_2 zombie: input 范围大 (11K-381K), 85 output_tokens

### 任务3: nv_gw 路径B zombie 内部重试 → 未做 (下轮候选)

- handlers.py 有 `_ms_fallback_request` (L1258 调用) + `_peek_retry_next_key` (L1137) 但都是
  ms_gw 兜底/next-key peek, **非 R2192 设计的 "同上游 NVCF 重发续流"**
- R2192 设计: zombie 检测点 (message_start 已发的路径 B) → 关当前 NVCF conn → 对 NVCF 重发
  原 oai_body (同 key 或下 key) → 拿新流续 feed 同一 converter (converter feed_chunk 有
  `if not self.message_start_sent` 守卫, 第二流不双 message_start) → flush 给 cc4101
- 双 message_start 约束未解 (任务3 核心难点), 需设计 converter 内部重试
- 本轮不做 (复杂, 需专轮规划 + 数据驱动设计)

## 决策: NOP 数据分析轮, 0 改动 0 restart

**不改代码的理由**:
1. R2192 任务2 的关键交付 (25 样分析 → 推测 A 否定) 本轮完成, 是重大认知更新, 值得单独立轮记录
2. 当前数据不触发改动三阈值:
   - 主链路 glm5_2_nv 30min 100% ✅ (虽非 cc2 默认, 仍是 nv_gw 可用 tier)
   - kimi_nv (新默认) 80%, 4 错全上游类 (2 ATE 上游 502 + 2 zombie 上游空响应), 非nv_gw旋钮能治根因
   - cc4101 fallback 2 < 5 ✅ (全救回 0 真中断)
   - 无新增错误类型 (zombie/ATE 历史多轮已现)
3. 任务3 (zombie 内部重试) 复杂, 不在本轮仓促上马, 留下轮专轮设计
4. kimi 502 是 NVCF 上游容量问题 (71s 后 502, 非 timeout), nv_gw 已 all_keys 重试 (ATE =
   全 key 都 502), 调 timeout/cooldown 治不了上游 502
5. 容器无漂移 (nv_gw StartedAt 连续多轮未变), env 无漂移

## 验证

0 改动 0 restart 无需验证改动. 基础健康确认:
- curl /health ok (passthrough, nv_default_model=glm5_2_nv, 3 models, 5 keys)
- docker ps 全栈 Up (nv_gw/cc4101/ms_gw/logs_db)
- nv_gw StartedAt=2026-07-22T15:10:34Z (docker inspect 实测, 连续多轮 RC=0 未重建)
- env 关键参数与历史逐项一致无漂移

## 下一轮建议

1. **R2192 任务3 设计轮** (最高优先, 撤 40007 核心): 基于"推测 A 已否定, 倾向 D 上游间歇性"
   的事实, 任务3 的价值 = zombie 发生时 nv_gw 内部对 NVCF 重发续流, 减少 cc4101 fallback.
   设计要点: converter feed_chunk 的 `message_start_sent` 守卫已存在, 需在 zombie 检测点
   (L1533 附近) 加 "关 conn → 重发 oai_body 到 NVCF → 续 feed converter" 逻辑, 重试上限 1-2 次.
   dsv4p zombie 0 output_tokens (纯空, 最适合重试); kimi zombie 1698 output_tokens (有 flush,
   重试会重复但可接受, R2192 已决策). 备份 .bak.R2291_t3.
2. **kimi 502 上游容量问题**: 71s 后 502 是 NVCF kimi function 过载, 非nv_gw能治. 若持续高频
   (>5/30min 且连续多轮), 需评估是否临时把 cc2 默认改回 glm5_2_nv (已恢复 100%) 或加 kimi 到
   NVU_MS_FALLBACK_MODELS (但 R2289 有意没加, 为让 cc2 看到真实 kimi 故障). 当前 2/30min 可接受.
3. **任务1 cache 持续验证**: 下轮补查 cc2 jsonl usage 的 cache_read_input_tokens, 确认
   命中率仍 >30% (R2228 记录 38.8%), 无退化.
4. **499 跟踪**: 32/6h 较 R2137 的 50 下降 36%, 推测是 kimi 切换 + settings 120K 的附带收益.
   持续跟踪是否维持低位.
5. **触发改动三阈值** (全满足才动): 30min 主链路 SR 跌破 85% **或** cc4101 fallback >5/30min
   (且新 req id 非旧滑入) **或** 出现新错误类型 (zombie 比例持续上升 / NV-ANTH-BREAKER-FAIL 真 OPEN).

## 参数表 (本轮无改动, 与 R2289 一致)

```
PRIMARY_UPSTREAM_MODEL=kimi_nv  (cc4101, R2289 改, cc2 默认模型)
nv_gw nv_default_model=glm5_2_nv  (nv_gw 自身默认 tier, 未改)
NVU_MS_FALLBACK_MODELS=glm5_2_nv  (kimi 不在, R2289 有意, 让 cc2 看真实 kimi 故障)
NVU_BIG_INPUT_MODELS=glm5_2_nv
MIN_OUTBOUND_INTERVAL_S=10
KEY_COOLDOWN_S=60
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
TIER_COOLDOWN_S=180
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
NVU_FORCE_STREAM_UPGRADE=0
```

## 关联

- R2192 三任务 (CLAUDE.md 持久指令): 任务1 ✅ (R2228/R2288) / 任务2 ✅ (R2257 接线 + 本轮 25 样分析, 推测 A 否定) / 任务3 ⏳ (下轮设计)
- R2289: cc2 默认模型 dsv4p_nv→kimi_nv + 1M settings 回退 120K (本轮接棒基线)
- R2287: cc2 默认模型 glm5_2_nv→dsv4p_nv (中间态, 因 glm5.2 当日全 0% 挂窗)
- R2191: 1M context (glm5.2 专用, R2289 已回退 120K 适配 kimi 128K ctx)
- ULTIMATE GOAL: 撤 40007 也能稳 — 任务3 完成是核心前置
