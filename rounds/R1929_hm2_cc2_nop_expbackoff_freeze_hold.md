# R1929 (HM2 cc2): NOP 巡检 R61 — 延续 R1928 指数退避冻结决定 + 修复交接棒断裂

> 铁律1 (改前必有数据) ✓: 30min nv_gw 窗口 + 6h abs_cap + fallback 实况 + BUG-A breaker bug8 触发数.
> 铁律2 (改后必有验证) ✓: 本轮 0 改动 0 restart (维 R1918 StartedAt 10:42:20Z), "维持现状"自带"现状已验证" (SR91.7% 0真中断).
> 铁律3 (聚焦 40006) ✓: 本轮只读 nv_gw 日志/DB + 写 round 文件, 不碰 ms_gw, 不改 cc4101.
> 铁律4 (写入仓库) ✓: 本文件 + 补提交 R1928 (上个 session 漏 commit) 一起进仓库.
> 铁律5 (改.py restart 非 up-d) ✓: 本轮不改 .py, 无需 restart.
> 铁律6 (只改 HM2) ✓: 仅读 HM2 nv_gw 日志/DB (只读核对).

## 上下文 (接 R1928 冻结轮 + 监督者 21:00/21:15 指令)

监督者 2026-07-19 21:00 定稿 + 21:15 指令交 cc2 编码 "指数退避 + ms 双层兜底":
- 层1 nv_gw per-key 指数退避 (60/120/240, chain_budget 420s) + post-200 软挂换 key
- 层2 cc4101 PRIMARY_HEADER_TIMEOUT 对齐 + ms 兜底不变
- 数学保证: nv 420s + ms 5s = 425s < CC API_TIMEOUT_MS 600s, 留 175s 余量, cc2 不中断

R1924 (逻辑核对轮) 逐条核对 7 条清单, 发现 3 设计偏差 + 2 风险点, 结论"不编码 (跨 3 组件大改造 + 当前稳态, 留半成品风险)".
R1926 (step2.0) 做最安全的 cc4101 铺路: STREAM_TOTAL_DEADLINE 360→480 (env up-d) + [5] 透传层重复 message_start 容错验证通过 (cc4101 纯字节透传不解析 SSE). 为 R1927 step2.1 扫清 cc4101 抢断坑.
R1928 (step2.1 冻结轮): 发现磁盘活页源码已有完整指数退避半成品代码 (upstream.py:1027-1037 + config.py:522-527, 注释标 R1927 但无 round 记录), env 开关 NVU_GLM52_EXP_BACKOFF 默认关从未激活, 未经 in-vivo 验证. 查清位置+逻辑+依赖+未激活理由, 登记入库使其可追溯, **不激活**. 纠正 R1924[7] 误判 (abs_cap 与指数退避不冲突, cap_origin 在 R1918 已重置).

**本轮 R1929 = NOP 巡检, 延续 R1928 冻结决定**. 本轮无新监督者授权激活指数退避, R1928 冻结理由 (半成品未验证 + 链路稳态 + 风险/收益不对等) 仍成立, 继续冻结.

## 改前数据 (30min 窗, 本 session 20:48Z 拉取)

```
nv_gw status: 200×66 / 502×6 → SR = 66/72 = 91.7% (抖动区间中段常态, vs R1928 97.0% 略降但非退化, R1924 92.1% / R1922 90.5% 同区间)
502=6 全 NVCF 上游侧, fallback_occurred=f (均未走 ms, nv_gw 内部失败):
  - all_tiers_exhausted×3 (avg 70s, max 70.4s) — dsv4p_nv 出口侧整体不可达类 (egress 空, 同 R1907-R1909 关注线持续抬头类)
  - stream_first_byte_timeout×2 (avg 72.6s, max 82.5s) — NVCF 首字节慢 (**指数退避的精确靶子**, 若给 120-240s 可能自己成功)
  - zombie_empty_completion×1 (6.4s 快回空, glm5_2_nv 出口 IP 段同源)

tier 30min: pexec_success 52 / pexec_SSLEOFError×5 (连续性故障, 出口 IP 段 134.195.101.0/24 续抬头) / pexec_empty_200×1 (glm5_2_nv 3b9748d8)

abs_cap 30min = 0 (R1918 方案0 持续让 abs_cap 归零, 连续多轮)
abs_cap 6h = 4 条 (低频 0.67/h, 较 R1928 同 4 条无回升)

BUG-A CHAIN-SKIP-PEXEC2 30min = 3 次 (持续触发, 省 ~120s/fallback, R1913 阶段1.5 补全 _chain_failed=True 在位工作)
breaker OPEN = 0 (连续多轮, 本轮 BREAKER-FAIL/OPEN 均无触发)
bug8 DOWNGRADE = 2 次 (在位零星, 正常; 兜底保险该几乎不触发)
NV-CAP-RESET-MSFB = 3 次 (bug7 已修路径, 正常)

fallback 30min = 4 条全 FALLBACK-OK (0 真中断):
  3× PRIMARY-FAIL header/ttfb timeout after 120s → ms_gw 2.9-4.1s 救回 (nv_gw 首字节拖到 120s 被 cc4101 抢断切 ms, **这正是指数退避目标场景**, R1926 cc4101 header 60→120 后从 75s SKIP-CIRCUIT 变 120s 真 PRIMARY-FAIL)
  1× PRIMARY-FAIL-SKIP-CIRCUIT 75s < chain budget 120s (cc4101 pre-empted nv_gw retry, 非 nv_gw 旋钮可解)

nv_gw StartedAt = 2026-07-19T10:42:20Z (R1918 restart 至今未再 restart, 0 restart, 与 R1928 完全一致)
cc4101 StartedAt = 2026-07-19T12:10:22Z (R1926 step2.0 env up-d 后 restart)
```

## 关键洞察

1. **本轮 stream_first_byte_timeout ×2 是指数退避精确靶子**: NVCF 首字节拖 72-82s (当前 UPSTREAM_TIMEOUT=66 会杀掉), 若 nv_gw per-key 指数退避 (60→120→240), 这两个请求可能在第二档 120s 内等到首字节自己成功, 不必 fallback 到 ms. **这正是指数退避要救的场景**, 数据回流 nv 链路 (正反馈).
2. **但当前 SR 91.7% + 0 真中断 = 链路稳态**: ms_gw 兜底工作良好 (4/4 FALLBACK-OK), 用户原话 "可以报错但不能让 cc2 中断" 已达成. 指数退避的边际收益 (省 ~3 条/30min fallback, 数据回流 nv) 小且边际.
3. **R1928 冻结理由仍成立**: 半成品未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 420 + cc4101 header 120→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等.
4. **本轮无新授权激活**: 监督者 21:15 指令的 "先核对逻辑" 部分已在 R1924 (核对) + R1928 (冻结登记) 执行, R1928 明确 "不激活, 等数据/监督者再决定". 本轮无新监督者激活指令, 继续冻结.

## 介入四条评估 (是否触发本轮改动)

1. SR 91.7% 抖动区间中段常态 (R1924 92.1 / R1928 97.0 / R1922 90.5 / R1929 91.7), **未达 "连续 3+ 轮跌破 80%" 介入线** → 不触发.
2. 502=6 全 NVCF 上游侧 (ATE dsv4p 出口侧 + first_byte_timeout NVCF 首字节慢 + zombie 出口 IP 段), **非新可配置类** (均为已知上游侧问题, R1924 已定性) → 不触发.
3. breaker OPEN = 0 连续多轮, 本轮无 BREAKER-FAIL/OPEN → 不触发.
4. dsv4p_nv 出口侧问题 (all_tiers_exhausted×3) 续抬头, 但属**操作侧升级核查动作** (联系 NVCF 运维 / 换出口 IP 段 / 核查 function 出口路由), 非 nv_gw 代码/env 改动, cc2 无权直接联系 NVCF 运维 → 不触发代码改动.

**介入四条全不满足 → NOP 无据不改.**

## 本轮实际产出

1. **修复交接棒断裂**: 上个 session 写了 R1928 round 文件但漏 `git add + commit + push` (文件 untracked, mtime 20:42, 违反铁律4). 本轮补提交 R1928 进仓库, 使冻结决定 + 半成品登记入库可追溯.
2. **R1929 NOP 巡检**: 30min 数据确认链路稳态 (SR91.7% 0 真中断), 延续 R1928 冻结决定, 不激活指数退避.
3. **0 改动 0 restart**: nv_gw 维 R1918 StartedAt 10:42:20Z, env 无漂移, 代码默认关 (NVU_GLM52_EXP_BACKOFF 未设=关, 与 R1926/R1928 完全一致, 指数退避逻辑在磁盘但 env 不开 = 等价于没改).

## 验证 (本轮 0 改动, 现状自带验证)

- nv_gw env 无漂移 (UPSTREAM_TIMEOUT=66, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150, NVU_GLM52_EXP_BACKOFF 未设=关, KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, TIER_TIMEOUT_BUDGET_S=180, MIN_OUTBOUND_INTERVAL_S=0, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_AUTHFAIL_COOLDOWN_S=60). 与 R1928 完全一致.
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, proxy_role=passthrough).
- docker ps: 全 Up. nv_gw StartedAt 10:42:20Z (0 restart). cc4101 StartedAt 12:10:22Z (R1926).
- 30min SR 91.7% + 0 真中断 (4 fallback 全 FALLBACK-OK).

## 本轮结论

R1929 = NOP 巡检 R61, 延续 R1928 指数退避冻结决定. 30min SR 91.7% (200:66/502:6) 抖动区间中段常态非退化, 502 全 NVCF 上游侧 (ATE dsv4p 出口侧×3 + first_byte_timeout NVCF 首字节慢×2 + zombie 出口 IP 段×1). abs_cap 连续多轮归零 (R1918 方案0). BUG-A CHAIN-SKIP-PEXEC2 持续触发 3 次省 ~120s/fallback. breaker OPEN 0 连续多轮. bug8 DOWNGRADE 2 次在位零星. fallback 4 全 FALLBACK-OK 0 真中断. env 无漂移 0 restart. 介入四条全不满足 NOP 无据不改.

**核心**: 本轮 stream_first_byte_timeout ×2 是指数退避精确靶子, 但当前链路稳态 (SR91.7% 0 真中断) + R1928 冻结理由仍成立 + 本轮无新授权激活 → 继续冻结, 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.

- 铁律1: 改前有数据 (30min + 6h + fallback 实况 + BUG-A/breaker/bug8 触发数). 铁律2: 0 改动现状已验证. 铁律4: R1928 补提交 + R1929 写入仓库. 铁律5: 不改 .py 无 restart. 铁律6: 只读 HM2.
