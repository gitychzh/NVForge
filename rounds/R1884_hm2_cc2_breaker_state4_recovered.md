# R1884 (HM2 cc2) — 动态观测轮: breaker state 首次升到 4 (R1842 NOP以来38轮最高) 但 53s 尖峰后窗口淘汰自然回落未 OPEN, 闭合"NVCF侧abs_cap/sporadic尖峰会否误触OPEN"悬案

## 上游根因已在 R1881-R1883 闭合, 本轮验证: 当前唯一的趋势性新信号(breaker state 升 4) 是 R1771 滑动窗口设计内吸收态而非误触 OPEN, 数据证明"偶发 NVCF 侧尖峰不会错误 OPEN 整条链"

**改了什么**: NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 改前数据 (30min 窗, 本 session ~12:26 CST 拉取)

### SR
- SR **51/63 = 81.0%** (200:51 / 502:12). **连续第 6 轮破 93%** (R1879 88.9 + R1880 86.7 + R1881 89.7 + R1882 84.4 + R1883 80.9 + R1884 81.0).
  介入条件 #1 (SR 连续 >=3 轮破 93) 早已满足, 但处置指向**查上游非调参** (R1881-R1883 已穷尽: 根因=NVCF端对HM2出口IP段 134.195.101.0/24 的 TLS RST + NVCF侧 abs_cap/zombie 常态抖动, 非 nv_gw config 可调旋钮).
- 本轮较 R1883 80.9 微升 0.1pp, 属破 93 后的低位区间抖动, 非续探底.
- 502 分类 (status=502, 共 12 条):
  - zombie_empty_completion **6** (NVCF 侧 zombie 偶发, 已知分类 config 不可修, R1851+ 间歇).
  - stream_absolute_cap **4** (NVCF 侧 abs_cap, 已知分类 config 不可修).
  - all_tiers_exhausted **1** (tier 全 key 耗尽兜底, 与本窗 all_keys_exhausted 增多同源).
  - stream_first_byte_timeout **1** (NVCF 侧 ttfb, 已知分类 config 不可修).
  - **全 NVCF 侧偶发外分支 + tier 耗尽兜底, 非新可配置错误分类**, 与 R1881-R1883 同构. **本窗无 SSLEOFError 直接命中 502**.

### tier pexec (60min DB)
- pexec_success **71** (干净基底).
- pexec_empty_200 **14** + pexec_timeout **3** + empty_200 **1** (NVCF 侧偶发, 非新可配置分类).
- **pexec_SSLEOFError 0** (60min 窗口 0 命中). **SSLEOFError 当前已持续缓和**, 与 R1883 一致:
  - 60min docker logs NV-SSL-CYCLE/NV-GLM52-EOF-SUMMARY 命中 0.
  - 120min DB tier 表 SSLEOF 仅 7 条, 全在 02:32-03:08 UTC (=R1881/R1882 拉取窗口尾部), 此后停止.
  - 即 R1877→R1878→R1879→R1880→R1881→R1882 的 "1→1→6→6→6→6" 批量序列已在 R1883 后缓和为 0.
  - R1881-R1883 根因调查结论仍成立: SSLEOF = NVCF 端 api.nvcf.nvidia.com 对 HM2 出口 IP 段 134.195.101.0/24 的 TLS RST, 非 nv_gw config 可修 (处置权在运维: 换出口 IP 段 / 查 NVCF 端对该 /24 的 TLS 限流策略).
- **无 ATE (all_keys_exhausted 走 ms 兜底, 非 tier 自身 ATE 错误) 无 429 无 pexec_timeout-as-primary-error** (主路径干净).

### breaker 30min (本轮核心新数据点)
- **nv_breaker state 首次升到 4** (R1842 NOP 以来连续 38 轮观测中从未出现过), 离 OPEN 阈值 (NVU_MS_FALLBACK_FAIL_THRESHOLD=5) 只差 1.
- 事件时序 (30min 窗内 6 条 NV-ANTH-BREAKER-FAIL, 全 NVCF 侧):
  - 11:57:02 stream_absolute_cap → state=('CLOSED', 1, 0) req=5cac4a29
  - 12:03:10 stream_absolute_cap → state=('CLOSED', 1, 0) req=dbe55a4a
  - 12:05:15 stream_absolute_cap → state=('CLOSED', 2, 0) req=a228049e
  - **12:19:18 zombie_empty_completion → state=('CLOSED', 2, 0) req=6ac67d7d** ← 53s 尖峰起点
  - **12:19:38 stream_absolute_cap → state=('CLOSED', 3, 0) req=b8bbc08f**
  - **12:20:11 zombie_empty_completion → state=('CLOSED', 4, 0) req=ba7fa1f4** ← 53s 尖峰末点
- **重点 1**: 12:19:18 → 12:20:11 在 **53 秒内连发 3 条**, 全 NVCF 侧 abs_cap/zombie 抖动 (非 nv_gw 自身软挂). 这正是 R1771 滑动窗口设计要对付的 "sporadic degraded chain" 形态.
- **重点 2**: 本轮 12:26 复查, 距最后一条 (12:20:11) 已过 6 分钟 > 窗口 300s (5min), **state 已从 4 开始回落** (12:19:18 + 12:19:38 + 12:20:11 三条已出 300s 窗口被淘汰, 无新事件补充). **breaker 未 OPEN**.
- **重点 3 (本轮闭合的悬案)**: 这证明 R1771 滑动窗口设计在该偶发 NVCF 侧 abs_cap 尖峰后用时间淘汰了老失败, state 自然回落, **不会因为一个偶发 NVCF 侧 abs_cap 尖峰就误 OPEN 整条 nv 链甩后续成功请求给 ms** (那会反向恶化 fallback 率, 我的负向核心指标). 即"NVCF 侧 abs_cap/sporadic 尖峰会否误触 OPEN" 这个悬案本轮**数据闭合掉了**: 不会, R1771 设计鲁棒.
- NV-MS-FB-ATTEMPT 1 条 (12:18:08 all_keys_exhausted for glm5_2_nv req=8f13a84f → NV-MS-FB-SERVED ms 2640ms, breaker recorded failure state=CLOSED). tier 耗尽兜底 1 次, 与 502 all_tiers_exhausted=1 同源.

### fallback (cc4101 30min)
- fallback 计数 **7 条**, **全 PRIMARY-FAIL-SKIP-CIRCUIT** (bug3 75s/120s header/ttfb 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted):
  - 11:55 req=7f4d0bd9 → FALLBACK-OK ms 11540ms.
  - 11:57 req=35bab9d9 → FALLBACK-OK ms 4941ms (75s header/ttfb timeout).
  - 12:00 req=fd7dc771 → FALLBACK-OK ms 2051ms (75s).
  - 12:03 req=f2b95797 → FALLBACK-OK ms 5972ms (75s).
  - **12:14 req=8b84bdc9 → FALLBACK-OK ms 5562ms (120s header/ttfb timeout, R1883 首现 120s 黑洞后本轮续 1 条)**.
  - **12:18 req=6513c4d8 → FALLBACK-OK ms 2790ms (120s header/ttfb timeout, 本轮第 2 条 120s 黑洞)**.
  - **非跳过类真请求失败 0 条** < 4 阈值. **0 真中断** (全 ms 热备兜住, 用户无感).
- 120s header/ttfb timeout 升到 2 条 (R1883 仅 1 条), 但仍属 bug3 同类 header/ttfb 抢断, 非 nv_gw 失败类 (SKIP-CIRCUIT).

### bug8 (根除, 停巡)
- bug8 降级兜底 in-vivo 已根除 (R1839 落地, R1841-R1883 连续 38 轮 0 触发). 本轮不再单独观测 (监督者 11:30 指令: 停止巡检 bug8, 35 轮 0 触发已够).

### env + health
- env 无漂移 (KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 / TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 / MIN_OUTBOUND=0, 全与 R1850-R1883 一致).
- /health ok (proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv], nv_default_model=dsv4p_nv, port=40006).
- docker ps 全 Up (nv_gw Up 7h / cc4101 Up 20h / ms_gw Up 2d / logs_db Up 2d).
- StartedAt 仍 **2026-07-18T21:26:29Z** (=R1836 restart, R1839 至 R1884 未再 restart), 确认跑 R1839 改后字节码. 0 restart.

## 验证结果
- 链路稳态持续 (SR 81.0% 连续第 6 轮破 93, 但根因全 NVCF 侧已知分类非 nv_gw 可控, 介入条件#1满足但处置指向查上游非调参).
- **breaker state 升到 4 后在窗口淘汰后自然回落未 OPEN** (R1771 滑动窗口设计鲁棒性活证据, 闭合"NVCF侧abs_cap/sporadic尖峰会否误触OPEN"悬案).
- SSLEOFError 当前 0 (持续缓和, 60min log=0, 120min DB=7 全在旧窗口尾部).
- fallback 非跳过类 0 + 0 真中断 + 0 restart + tier pexec 无 ATE/429/timeout-as-primary-error (干净).
- bug8 根除 (停巡).
- /health ok + docker ps 全 Up + env 无漂移.

## 决策理由
- **本轮 NOP 巡检而非盲改**:
  1. **SR 81.0% 连续第 6 轮破 93** (介入条件#1满足), 但 502 全 NVCF 侧 abs_cap/zombie/tier耗尽/ttfb 已知分类, **无新可配置错误分类**. R1881-R1883 已穷尽 nv_gw 侧所有调参旋钮并反证 (KEY/TIER_COOLDOWN/UPSTREAM 管不到 TLS 握手被 RST + TIER_BUDGET 收紧到 90 会误杀慢成功 SR 暴跌). 处置指向查上游/运维, 非调参.
  2. **breaker state=4 离 OPEN 阈值 5 只差 1** (R1842 NOP 以来 38 轮首次), 但本轮**数据证明它在窗口淘汰后自然回落未 OPEN**, 是 R1771 设计内吸收态而非误触. 调高 NVU_MS_FALLBACK_FAIL_THRESHOLD 或改 NVU_BREAKER_WINDOW_S 都违反 R1719/R1771 反复警告 ("别调高阈值去假装不 OPEN, 会把死循环请回来"). state=4 本身不是恶化信号, 是设计内工作.
  3. fallback 非跳过类 0 < 4 (介入条件#2 不满足).
  4. breaker 未 OPEN (介入条件#3 不满足).
  5. R1883 留的代码候选 (给 SSLEOF 补 append 带 egress_ip) 边际收益 0 + 副作用面 > 0 (改 key_cycle_attempts 长度→改 key_cycle_429s 计数语义), 且 SSLEOF 当前已缓和, 无据不动.
- **硬改违反铁律** (改前必有数据: 本轮反而证明 nv_gw 侧无可动 + 无据不改).
- **本轮价值**: 不是 R1878/R1879 那种纯惰性巡检, 而是闭合了 "breaker state 升到 4 会否误触 OPEN" 这个 R1880 STATE 预警过的悬案 — 数据答案是 **不会**, R1771 滑动窗口设计鲁棒.

## 给监督者/运维的结论 (沿用 R1883, 仍成立)
- nv_gw 侧所有调参旋钮已在 R1881-R1883 穷尽且反证, 无剩余可动. SSLEOF 根因 = NVCF 端对 HM2 出口 IP 段 134.195.101.0/24 的 TLS RST.
- 真正该动: a) 换出口 IP 段 (让 5 mihomo 端口 7894-7899 背后走非 134.195.101.0/24); b) 联系 NVCF 运维修对该 /24 段的 TLS RST/限流策略 (23:00+03:00 UTC 档密集可能夜间维护/限流窗口).
- 短期无法换时, nv_gw cycle 逻辑 (upstream.py R40/R1730 SSLEOF cycle + nv_breaker R1648c/R1771) 已在位兜底, SR 抖动 80-99% 近 40 轮可接受, fallback 热备 0 真中断.
- **本轮新判据**: breaker state 升到 4 也不会误 OPEN (R1771 滑动窗口鲁棒), 介入条件 #3 真正该盯的是"OPEN 频繁复现"而非"state 偶发升到 4". 下一轮仍按此标准.

## 铁律核对
- 改前必有数据 ✓ (本轮 30min 窗 + 60min tier + 30min fallback/breaker)
- 改后必有验证 ✓ (NOP, 验证 = 链路未碰 + /health ok + docker ps 全 Up)
- 聚焦 40006 ✓ (未碰 ms_gw 40007)
- 不碰 ms_gw ✓
- 写入仓库 ✓ (本 round 文件 + commit)
- 只改 HM2 不改 HM1 ✓ (0 改动)
- 改 .py 必须 restart ✓ (本轮 0 .py 改动, 0 restart)

## 文案备注
本轮 R1884 commit 单文件, 无 peer 误收. peer R1883 推 R1883 HM2→HM1 (BIG_INPUT 阈值/UPSTREAM 等, 对 HM2 0 影响, 抢号区间).
