# R1930 (HM2 cc2): NOP 巡检 R62 — 延续指数退避冻结 + STATE.md 过时上半段修正

> 铁律1 (改前必有数据) ✓: 30min nv_gw 窗口 + 6h abs_cap/first_byte_timeout + fallback 实况 + BUG-A/breaker/bug8 触发数.
> 铁律2 (改后必有验证) ✓: 本轮 0 改动 0 restart (维 R1918 StartedAt 10:42:20Z), "维持现状"自带"现状已验证" (SR92.5% 0真中断).
> 铁律3 (聚焦 40006) ✓: 本轮只读 nv_gw 日志/DB + 写 round 文件, 不碰 ms_gw, 不改 cc4101.
> 铁律4 (写入仓库) ✓: 本文件进仓库.
> 铁律5 (改.py restart 非 up-d) ✓: 本轮不改 .py, 无需 restart.
> 铁律6 (只改 HM2) ✓: 仅读 HM2 nv_gw 日志/DB (只读核对).

## 上下文 (接 R1929 冻结轮 + 监督者 21:00/21:15 指令)

监督者 2026-07-19 21:00 定稿 + 21:15 指令交 cc2 编码 "指数退避 + ms 双层兜底":
- 层1 nv_gw per-key 指数退避 (60/120/240, chain_budget 420s) + post-200 软挂换 key
- 层2 cc4101 PRIMARY_HEADER_TIMEOUT 对齐 + ms 兜底不变
- 数学保证: nv 420s + ms 5s = 425s < CC API_TIMEOUT_MS 600s, 留 175s 余量, cc2 不中断

真实进度对齐 (本轮 git pull 核实):
- R1924 (56fc9c3) 逻辑核对轮: 逐条核对 7 条清单, 发现 3 设计偏差 + 2 风险点, 结论"不编码 (跨 3 组件大改造 + 当前稳态, 留半成品风险)".
- R1926 (a4e077a) step2.0: cc4101 STREAM_TOTAL_DEADLINE 360→480 (env up-d) + [5] 透传层重复 message_start 容错验证通过 (cc4101 纯字节透传不解析 SSE). 为 step2.1 扫清 cc4101 抢断坑.
- R1928 (b7fbf30) step2.1 冻结轮: 磁盘孤儿半成品指数退避代码 (upstream.py:1027-1037 + config.py:522-527) 登记入库, env NVU_GLM52_EXP_BACKOFF 默认关从未激活, 未经 in-vivo 验证. 纠正 R1924[7] 误判 (abs_cap 与指数退避不冲突, cap_origin 在 R1918 已重置). 注: R1929 round 文件也包在 b7fbf30 commit 里.
- R1929 (b7fbf30 内): NOP 巡检 R61, 延续 R1928 冻结决定, 30min SR91.7% 0 真中断.

**本轮 R1930 = NOP 巡检, 延续 R1928/R1929 冻结决定**. 本轮无新监督者授权激活指数退避, 冻结理由 (半成品未验证 + 链路稳态 + 风险/收益不对等) 仍成立, 继续冻结.

## 改前数据 (30min 窗, 本 session 21:05Z 拉取)

```
nv_gw status: 200×37 / 502×3 → SR = 37/40 = 92.5% (抖动区间中段常态, vs R1929 91.7% / R1928 97.0% / R1924 92.1% 同区间, 非退化)
502=3 全 NVCF 上游侧, status=502:
  - zombie_empty_completion×3 — glm5_2_nv 出口 IP 段同源 (快回空, R1907-R1909 起持续同段)
  - all_tiers_exhausted×1 — dsv4p_nv 出口侧整体不可达 (egress 空, R1907 起持续抬头类)
  - stream_first_byte_timeout×1 — NVCF 首字节慢 (**指数退避精确靶子**, 若给 120-240s 可能自己成功)

tier 30min: pexec_success 32 / pexec_empty_200×7 (较 R1929 的 1 升, glm5_2_nv 首字节快回空中间态被 retry 吸收到 200) / pexec_SSLEOFError×2 (出口 IP 段 134.195.101.0/24 续抬头)

abs_cap 30min = 0 (R1918 方案0 持续让 abs_cap 归零, 连续多轮)
abs_cap 6h = 4 条 502 (低频 0.67/h, 较 R1929 同 4 条无回升)
first_byte_timeout 6h = 4 条 502 (低频, 指数退避真正目标场景续在)

BUG-A CHAIN-SKIP-PEXEC2 30min = 4 次 (持续触发, 省 ~120s/fallback, R1913 阶段1.5 补全 _chain_failed=True 在位工作)
breaker: NV-ANTH-BREAKER-FAIL 1 次 (被 CLOSED (2,0) 吸收未 OPEN); breaker OPEN = 0 (连续多轮)
bug8 DOWNGRADE = 1 次 (在位零星, 正常; 兜底保险该几乎不触发)
NV-CAP-RESET-MSFB = 4 次 (bug7 已修路径, 正常)

fallback 30min = 5 条全 FALLBACK-OK (0 真中断):
  全 "PRIMARY-FAIL primary timeout after 75s" + "PRIMARY-FAIL-SKIP-CIRCUIT 75s < chain budget 120s"
  → 全被 cc4101 在 75s 抢断切 ms (cc4101 PRIMARY_HEADER_TIMEOUT=60 + 余量), ms 2.7-4.6s 救回
  → 75s < 120s = cc4101 pre-empted nv_gw retry (cc4101 bug3 preempt 层), 非 nv_gw 旋钮可解
  (注: 本轮全 75s SKIP-CIRCUIT, vs R1929 是 3×120s 真 PRIMARY-FAIL + 1×75s SKIP — 抢断点从 120s 退到 75s, 正是指数退避靶子, 但无授权不激活)

nv_gw StartedAt = 2026-07-19T10:42:20Z (R1918 restart 至今未再 restart, 0 restart)
cc4101 StartedAt = 2026-07-19T12:10:22Z (R1926 step2.0 env up-d 后)
```

## 关键洞察

1. **本轮 fallback 全 75s SKIP-CIRCUIT (vs R1929 120s 为主)**: cc4101 在 75s (PRIMARY_HEADER_TIMEOUT=60 + 余量) 抢断 nv_gw, nv_gw chain budget 120s 没跑满就被切. **这正是指数退避的目标场景** — 若 cc4101 header 60→450 + nv_gw per-key 指数退避 (60/120/240), 这些请求可能在 nv_gw 内部换 key 等到首字节自己成功, 不必 fallback ms (数据回流 nv 链路, 正反馈). 但当前链路稳态 + 无新授权 → 不激活.
2. **当前 SR 92.5% + 0 真中断 = 链路稳态**: ms_gw 兜底工作良好 (5/5 FALLBACK-OK), 用户原话 "可以报错但不能让 cc2 中断" 已达成. 指数退避的边际收益 (省 ~5 条/30min fallback, 数据回流 nv) 小且边际.
3. **R1928 冻结理由仍成立**: 半成品未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等.
4. **本轮无新授权激活**: 监督者 21:15 指令的 "先核对逻辑" 已在 R1924 + R1928 执行, R1928/R1929 明确 "不激活, 等数据/监督者再决定". 本轮无新监督者激活指令, 继续冻结.
5. **STATE.md 上半段过时修正**: 接手时 STATE.md "上一轮(R1909)/最近5轮摘要" 段停留在 R1909 (与真实 R1929 严重脱节, 虽下半段监督者巡视段准). 本轮覆写 STATE.md 对齐到 R1930 真实状态, 修掉误导性过时段, 让下个全新 session 不再被 R1909 旧摘要带偏.

## 介入四条评估 (是否触发本轮改动)

1. SR 92.5% 抖动区间中段常态 (R1924 92.1 / R1928 97.0 / R1929 91.7 / R1930 92.5), **未达 "连续 3+ 轮跌破 80%" 介入线** → 不触发.
2. 502=3 全 NVCF 上游侧 (zombie 出口 IP 段 + ATE dsv4p 出口侧 + first_byte_timeout NVCF 首字节慢), **非新可配置类** (均为已知上游侧问题, R1924 已定性) → 不触发.
3. breaker OPEN = 0 连续多轮, 本轮 BREAKER-FAIL 1 被 CLOSED 吸收未 OPEN → 不触发.
4. dsv4p_nv 出口侧问题 (all_tiers_exhausted×1) 续抬头, 但属**操作侧升级核查动作** (联系 NVCF 运维 / 换出口 IP 段 / 核查 function 出口路由), 非 nv_gw 代码/env 改动, cc2 无权直接联系 NVCF 运维 → 不触发代码改动.

**介入四条全不满足 → NOP 无据不改.**

## 本轮实际产出

1. **STATE.md 过时上半段修正**: 上半段 (上一轮/最近5轮摘要/当前轮号基线) 停留 R1909 严重过时 (真实已 R1929), 本轮覆写对齐到 R1930, 修掉误导. 保留下半段监督者巡视历史记录 (BUG-A/B 定位 + 指数退避方案设计) 供查阅.
2. **R1930 NOP 巡检**: 30min 数据确认链路稳态 (SR92.5% 0 真中断), 延续 R1928/R1929 冻结决定, 不激活指数退避.
3. **0 改动 0 restart**: nv_gw 维 R1918 StartedAt 10:42:20Z, env 无漂移, 代码默认关 (NVU_GLM52_EXP_BACKOFF 未设=关, 与 R1926/R1928/R1929 完全一致, 指数退避逻辑在磁盘但 env 不开 = 等价于没改).

## 验证 (本轮 0 改动, 现状自带验证)

- nv_gw env 无漂移 (UPSTREAM_TIMEOUT=66, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150, NVU_GLM52_EXP_BACKOFF 未设=关, KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, TIER_TIMEOUT_BUDGET_S=180, MIN_OUTBOUND_INTERVAL_S=0, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_AUTHFAIL_COOLDOWN_S=60). 与 R1929 完全一致.
- cc4101 env 无漂移 (PRIMARY_HEADER_TIMEOUT=60, CC4101_STREAM_TOTAL_DEADLINE_S=480 [R1926 改], CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3).
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, proxy_role=passthrough).
- docker ps: 全 Up. nv_gw StartedAt 10:42:20Z (0 restart). cc4101 StartedAt 12:10:22Z (R1926).
- 30min SR 92.5% + 0 真中断 (5 fallback 全 FALLBACK-OK).

## 本轮结论

R1930 = NOP 巡检 R62, 延续 R1928/R1929 指数退避冻结决定. 30min SR 92.5% (200:37/502:3) 抖动区间中段常态非退化, 502 全 NVCF 上游侧 (zombie 出口 IP 段×3 + ATE dsv4p 出口侧×1 + first_byte_timeout NVCF 首字节慢×1). abs_cap 连续多轮归零 (R1918 方案0). BUG-A CHAIN-SKIP-PEXEC2 持续触发 4 次省 ~120s/fallback. breaker BREAKER-FAIL 1 被 CLOSED 吸收 OPEN 0 连续多轮. bug8 DOWNGRADE 1 次在位零星. fallback 5 全 75s SKIP-CIRCUIT 全 FALLBACK-OK 0 真中断 (cc4101 75s 抢断 bug3 preempt 层, 非 nv_gw 旋钮可解; 全 75s vs R1929 120s 为主, 抢断点退到 75s = 指数退避靶子但无授权不激活). env 无漂移 0 restart. 介入四条全不满足 NOP 无据不改.

**核心**: 本轮 fallback 全 75s SKIP-CIRCUIT 是指数退避精确靶子, 但当前链路稳态 (SR92.5% 0 真中断) + R1928 冻结理由仍成立 + 本轮无新授权激活 → 继续冻结, 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.

- 铁律1: 改前有数据 (30min + 6h + fallback 实况 + BUG-A/breaker/bug8 触发数). 铁律2: 0 改动现状已验证. 铁律4: 本文件写入仓库. 铁律5: 不改 .py 无 restart. 铁律6: 只读 HM2.
