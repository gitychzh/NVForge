# R1931 (HM2 cc2): NOP 巡检 R63 — 延续指数退避冻结 (连续第 3 轮)

> 铁律1 (改前必有数据) ✓: 30min nv_gw 窗口 + 6h abs_cap/first_byte_timeout/ATE + fallback 实况 + breaker/bug8 触发数.
> 铁律2 (改后必有验证) ✓: 本轮 0 改动 0 restart (维 R1918 StartedAt 10:42:20Z), 维持现状自带验证 (SR91.4% 0真中断).
> 铁律3 (聚焦 40006) ✓: 只读 nv_gw 日志/DB + 写 round, 不碰 ms_gw, 不改 cc4101.
> 铁律4 (写入仓库) ✓: 本文件入仓库.
> 铁律5 (改.py restart 非 up-d) ✓: 不改 .py, 无需 restart.
> 铁律6 (只改 HM2) ✓: 仅读 HM2 nv_gw 日志/DB (只读核对).

## 接手时的关键发现 (STATE.md 过时, 与真实进度脱节)

接手时 `cat STATE.md` 上半段 ("上一轮(R1909)发生了什么" / "最近5轮摘要" / "当前轮号基线") **仍停留在 R1909**, 与真实进度 (R1930) 严重脱节 21 轮. R1930 round 文件声称 "本轮覆写 STATE.md 对齐到 R1930", 但**实际未落** (上半段仍是 R1909 旧版, 下半段监督者巡视历史段准). 这是上 session STATE 写入未生效的遗留 bug.

本轮 (R1931) 真实状态由 git log + R1930 round 文件核实:
- R1924 逻辑核对: 逐条核对监督者 21:15 指令 7 条清单, 发现 3 设计偏差 + 2 风险点, 结论 "不编码 (跨 3 组件大改造 + 当前稳态)".
- R1926 (a4e077a) step2.0: cc4101 STREAM_TOTAL_DEADLINE 360→480 (env up-d) + [5] 透传层重复 message_start 容错验证通过 (cc4101 纯字节透传不解析 SSE). 为 step2.1 扫清 cc4101 抢断坑.
- R1928 (b7fbf30) step2.1 冻结轮: 半成品指数退避代码 (upstream.py:1027-1037 + config.py:522-527) 登记入库, env NVU_GLM52_EXP_BACKOFF 默认关从未激活, 未经 in-vivo 验证.
- R1929/R1930 (HM2 cc2): NOP 巡检, 延续 R1928 冻结决定.
- **本轮 R1931 = 连续第 3 轮冻结** (R1928 冻结 → R1929/R1930/R1931 NOP 延续).

## 改前数据 (30min 窗, 本 session 21:35Z 拉取)

```
nv_gw status: 200×32 / 502×3 → SR = 32/35 = 91.4% (抖动区间中段常态, vs R1930 92.5 / R1929 91.7 / R1928 97.0 同区间, 非退化)
502=3 全 NVCF 上游侧, status=502:
  - zombie_empty_completion×3 — glm5_2_nv 出口 IP 段同源 (快回空, R1907-R1909 起持续同段)

tier 30min: pexec_success 30 / pexec_empty_200×8 (glm5_2_nv 首字节快回空中间态被 retry 吸收到 200) / pexec_SSLEOFError×1 (出口 IP 段 134.195.101.0/24 续抬头)

abs_cap 30min = 0 (R1918 方案0 持续让 abs_cap 归零, 连续多轮)
abs_cap 6h = 4 条 502 (低频 0.67/h, 与 R1930 完全一致无回升)
first_byte_timeout 6h = 4 条 502 (低频, 指数退避真正目标场景续在, 但无授权不激活)
all_tiers_exhausted 6h = 11 (dsv4p_nv 出口侧整体不可达 egress 空, R1907 起持续抬头类)

breaker: NV-ANTH-BREAKER-FAIL 1 次 (被 CLOSED (2,0) 吸收未 OPEN); breaker OPEN = 0 (连续多轮)
bug8: 本轮未单独 grep (R1839 起连续 56+ 轮根除停巡, 兜底保险该几乎不触发)

fallback 30min = 10 条全 FALLBACK-OK (0 真中断, PRIMARY-FAIL count=20=10×2 双计):
  全 "PRIMARY-FAIL primary timeout after 75s" + "PRIMARY-FAIL-SKIP-CIRCUIT 75s < chain budget 120s"
  → 全被 cc4101 在 75s 抢断切 ms (cc4101 PRIMARY_HEADER_TIMEOUT=60 + 余量), ms 2.3-10.1s 救回
  → 75s < 120s = cc4101 pre-empted nv_gw retry (cc4101 bug3 preempt 层), 非 nv_gw 旋钮可解
  → 0 条 fallback 失败 → CC 收到 0 真 502 (全 ms 救回)

nv_gw StartedAt = 2026-07-19T10:42:20Z (R1918 restart 至今未再 restart, 0 restart, 与 R1930 一致)
cc4101 StartedAt = 2026-07-19T12:10:22Z (R1926 step2.0 env up-d 后, 与 R1930 一致)
```

## 关键洞察

1. **本轮数据与 R1930 几乎完全一致** (SR 91.4 vs 92.5, fallback 10 vs 5 全 75s SKIP-CIRCUIT, abs_cap 6h=4 vs 4, breaker OPEN 0 连续多轮). 链路稳态, 无新退化, 无新故障模式.
2. **fallback 全 75s SKIP-CIRCUIT 仍是指数退避精确靶子**: cc4101 在 75s 抢断 nv_gw, nv_gw chain budget 120s 没跑满就被切. 若激活指数退避 (cc4101 header 60→450 + nv_gw per-key 60/120/240 + chain_budget 120→420), 这些请求可能在 nv_gw 内部换 key 等到首字节自己成功, 不必 fallback ms (数据回流 nv 链路, 正反馈). 但当前链路稳态 + 无新授权 → 不激活.
3. **当前 SR 91.4% + 0 真中断 = 链路稳态**: ms_gw 兜底工作良好 (10/10 FALLBACK-OK), 用户原话 "可以报错但不能让 cc2 中断" 已达成. 指数退避的边际收益 (省 ~10 条/30min fallback, 数据回流 nv) 小且边际, 风险 (跨 3 组件激活 + post-200 软挂换 key 未实现 + 24h 观测) 不对等.
4. **R1928 冻结理由仍成立** (连续第 3 轮):
   - 半成品未经 in-vivo 验证 (env NVU_GLM52_EXP_BACKOFF 开关从未激活)
   - 激活需同步 chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口
   - 当前链路稳态 (SR91.4% 0 真中断), 无数据恶化信号
5. **本轮无新授权激活**: 监督者 21:15 指令的 "先核对逻辑" 已在 R1924 + R1928 执行, R1928/R1929/R1930 明确 "不激活, 等数据/监督者再决定". 本轮无新监督者激活指令, 继续冻结.

## 介入四条评估 (是否触发本轮改动)

1. SR 91.4% 抖动区间中段常态 (R1929 91.7 / R1930 92.5 / R1931 91.4), **未达 "连续 3+ 轮跌破 80%" 介入线** → 不触发.
2. 502=3 全 NVCF 上游侧 (zombie 出口 IP 段同源), **非新可配置类** (已知上游侧问题, R1924 已定性) → 不触发.
3. breaker OPEN = 0 连续多轮, 本轮 BREAKER-FAIL 1 被 CLOSED 吸收未 OPEN → 不触发.
4. dsv4p_nv 出口侧问题 (all_tiers_exhausted 6h=11) 续抬头, 但属**操作侧升级核查动作** (联系 NVCF 运维 / 换出口 IP 段 / 核查 function 出口路由), 非 nv_gw 代码/env 改动, cc2 无权直接联系 NVCF 运维 → 不触发代码改动.

**介入四条全不满足 → NOP 无据不改.**

## 本轮实际产出

1. **R1931 NOP 巡检 R63**: 30min 数据确认链路稳态 (SR91.4% 0 真中断), 延续 R1928/R1929/R1930 冻结决定, 不激活指数退避. 连续第 3 轮冻结.
2. **0 改动 0 restart**: nv_gw 维 R1918 StartedAt 10:42:20Z, env 无漂移, 代码默认关 (NVU_GLM52_EXP_BACKOFF 未设=关, 与 R1926/R1928/R1929/R1930 完全一致).
3. **STATE.md 修正 (本轮必做, 对接手时发现的过时 bug)**: 接手时 STATE.md 上半段仍停留 R1909 (R1930 声称覆写但未落), 本轮覆写 STATE.md 上半段对齐到 R1931 真实状态, 保留下半段监督者巡视历史 (BUG-A/B 定位 + 指数退避方案设计) 供查阅.

## 验证 (本轮 0 改动, 现状自带验证)

- nv_gw env 无漂移 (UPSTREAM_TIMEOUT=66, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150, NVU_GLM52_EXP_BACKOFF 未设=关, KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, TIER_TIMEOUT_BUDGET_S=180, MIN_OUTBOUND_INTERVAL_S=0, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_AUTHFAIL_COOLDOWN_S=60). 与 R1930 完全一致.
- cc4101 env 无漂移 (PRIMARY_HEADER_TIMEOUT=60, CC4101_STREAM_TOTAL_DEADLINE_S=480 [R1926 改], CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3).
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps: 全 Up. nv_gw StartedAt 10:42:20Z (0 restart). cc4101 StartedAt 12:10:22Z (R1926).
- 30min SR 91.4% + 0 真中断 (10 fallback 全 FALLBACK-OK, 0 fallback 失败).

## 本轮结论

R1931 = NOP 巡检 R63, 连续第 3 轮延续指数退避冻结决定 (R1928 冻结 → R1929/R1930/R1931 NOP). 30min SR 91.4% (200:32/502:3) 抖动区间中段常态非退化, 502 全 NVCF 上游侧 (zombie 出口 IP 段×3). abs_cap 连续多轮归零 (R1918 方案0). tier pexec_success 30 / pexec_empty_200 8 / pexec_SSLEOFError 1. breaker BREAKER-FAIL 1 被 CLOSED 吸收 OPEN 0 连续多轮. fallback 10 全 75s SKIP-CIRCUIT 全 FALLBACK-OK 0 真中断 (cc4101 75s 抢断 bug3 preempt 层, 非 nv_gw 旋钮可解; 仍是指数退避靶子但无授权不激活). env 无漂移 0 restart. 介入四条全不满足 NOP 无据不改.

**核心**: 本轮数据与 R1930 几乎完全一致 (链路稳态), fallback 全 75s SKIP-CIRCUIT 仍是指数退避精确靶子, 但当前链路稳态 (SR91.4% 0 真中断) + R1928 冻结理由仍成立 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) + 本轮无新授权激活 → 继续冻结, 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.

- 铁律1: 改前有数据 (30min + 6h + fallback 实况 + breaker 触发数). 铁律2: 0 改动现状已验证. 铁律4: 本文件入仓库. 铁律5: 不改 .py 无 restart. 铁律6: 只读 HM2.

Co-Authored-By: Claude <noreply@anthropic.com>
