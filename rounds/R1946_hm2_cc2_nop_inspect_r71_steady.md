# R1946 (HM2 cc2): NOP 巡检 R71 — 稳态持续, 30min SR78.9%(小样本)/ 6h SR93.8% 0 真中断, 连续冻结第 9 轮延续

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / 不碰 ms_gw(40007)

## 本轮性质: NOP 巡检 (0 源码改动 0 env 改动 0 restart)

新 session 接手, 读 STATE.md 棒 (棒基线**严重过时停 R1931**, 实际仓库已推进到 R1945). git pull 后 origin/main 已是最新 (peer 推到 R1945 HM2→HM1 NOP, cc2 上轮 cc72d63 R1943 NOP 巡检 R70). 本轮 cc2 从 R1946 起. STATE.md 棒基线仍过时停 R1931 + StartedAt 错记 10:42:20Z (实际 13:33:43Z, R1933 restart) — 这是连续多轮"声称覆写未落"的老问题 (R1930/R1942/R1943 round 均声称覆写但 STATE.md 未落). 本轮职责:
1. 继续巡检 R1933 NameError 修复后稳态, 确认无回归无新 bug.
2. 覆写 STATE.md 上半段对齐到 R1946 真实状态 (含 StartedAt 修正 + 轮号基线推进).

## 数据 (本 session 拉取, DB 时钟 = 2026-07-19 16:27:29Z UTC = 00:27 CST, nv_gw StartedAt 13:33:43Z = 已起 ~3h)

### nv_gw 健康 + 源码状态
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (= R1933 restart, R1933→R1946 未再 restart, R1935/R1936/R1939/R1941/R1942/R1943 记录一致).
- cc4101 StartedAt = 2026-07-19T12:10:22Z (= R1926 step2.0 env up-d).
- /health ok (nv_num_keys=5, pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough).
- docker ps 全 Up (nv_gw Up 3 hours / ms_gw Up 2 days / cc4101 Up 4 hours / logs_db Up 2 days).
- **源码状态 = R1933 已验证后状态** (无漂移, 与 R1943 记录一致).
- **NVU_GLM52_EXP_BACKOFF env 未设=关** (R1928 半成品冻结, 从未 in-vivo 激活, 连续第 9 轮).

### 30min nv_gw 成功率 (本轮主窗口)
- SR = 15/19 = **78.9%** (200:15 / 502:4), 样本极小 (本 session 刚启动, nv 流量稀, 2 条 502 拉低 10pp 非退化信号). 抖动区间常态 (R1929 91.7 / R1930 92.5 / R1931 91.4 / R1941 92.5 / R1942 93.75 / R1943 94.7 / R1946 30min 78.9, 小样本偶低非连续跌破 80%).
- 502 分类: zombie_empty_completion×2 (glm5_2_nv 出口 IP 段同源, R1907-R1909 起持续同段, 已知上游侧) + all_tiers_exhausted×2.
- abs_cap 30min = **0** (R1918 方案0 cap_origin 重置让 abs_cap 持续归零, 连续多轮).

### tier 30min
- pexec_success 9 (流量稀, 仅 success 无错误类抬头).

### 6h nv_gw 成功率 (大样本验证稳态)
- SR = 571/609 = **93.8%** (200:571 / 502:38), 与 R1939 (95.3%) / R1942 (95.2%) / R1943 (94.9%) 几乎完全一致区间, 稳态持续.
- 502 分类全已知: zombie_empty_completion×22 (glm5_2_nv 出口 IP 段同源) + all_tiers_exhausted×12 (dsv4p_nv, 70s ATE, NVCF 上游侧) + stream_first_byte_timeout×4.
- **abs_cap 6h = 0** (R1931=4 → R1942=2 → R1943=2 → R1946=0, R1918 方案0 持续让 abs_cap 归零或趋零).
- **无新可配置类** (非 zombie/empty200/timeout/SSLEOFError/abs_cap/all_tiers_exhausted).

### fallback (负向核心指标, cc4101 日志)
- 60min: **6** FALLBACK-OK, **0** fallback 失败 → **0 真中断**.
- 全 "PRIMARY-FAIL-SKIP-CIRCUIT primary timeout after 75s < chain budget 120s" → 全被 cc4101 在 75s 抢断切 ms (cc4101 PRIMARY_HEADER_TIMEOUT=60 + 余量), ms 兜回救 (ms 3.9-30.4s 救回).
- 1 条 120s timeout (req=48f4c195 23:33, PRIMARY-FAIL 非 SKIP-CIRCUIT, 也被 ms 5.1s 兜回).
- **75s < 120s = cc4101 pre-empted nv_gw retry** (cc4101 bug3 preempt 层), 非 nv_gw 旋钮可解, 仍是指数退避精确靶子但无新授权激活.
- 30min 内 FALLBACK-OK = 0 (窗口内无 fallback 事件, 流量稀).

### breaker
- cc4101 primary circuit OPEN 6h = **14, 全集中 21:27-21:33 CST (13:27-13:33 UTC) 一次性突发** (与 R1939/R1943 记录的 21:27-21:33 突发是同一旧事件, 容器未重启日志累积; R1939 当时已自愈, 非 R1946 新退化). **30min 内 PRIMARY-BREAKER-OPEN = 0** (突发后 ~3h 无新 OPEN, 持续自愈 CLOSED).
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **0 次** → 无 BREAKER-FAIL 触发.
- breaker **OPEN 0 连续多轮** (R1931→R1946 持续).

## 介入四条核对 (全不满足 → NOP 无据不改)

1. **SR 跌破介入线?** 否. 6h SR93.8% 大样本稳态 (R1939-R1946 93.8-95.3% 区间), 30min SR78.9% 是小样本 (19 条) 抖动非连续跌破 80% (单窗口 2 条 502 就拉低 10pp). 未达"连续 3+ 轮跌破 80%"介入线. ✗
2. **502 出现新可配置类?** 否. 502 全 zombie (出口 IP 段同源已知上游侧) + all_tiers_exhausted + first_byte_timeout, **全是已知类**, 非新可配置类. abs_cap 6h=0 持续归零. ✗
3. **breaker 开始 OPEN?** 否. cc4101 PRIMARY-BREAKER-OPEN 6h=14 全集中 21:27-21:33 CST 一次性突发 (R1939 旧事件非新退化), 30min=0 已自愈; nv_gw BREAKER-FAIL 30min=0, OPEN 0 连续多轮. ✗
4. **fallback 飙升或新授权激活指数退避?** 否. fallback 6/60min 全 75s SKIP-CIRCUIT 被 ms 兜住 0 真中断 (低于介入线 15/30min). 仍是指数退避精确靶子但**无新监督者激活指令** (R1928 冻结理由仍成立: 半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测). ✗

## 验证 (NOP 轮, 0 改动故 0 restart, 但确认稳态)

- env 无漂移 (UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_STREAM_ABSOLUTE_CAP_S=150 / NVU_GLM52_EXP_BACKOFF 未设=关 / MIN_OUTBOUND=0 / KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_COOLDOWN=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25). 与 R1943 完全一致.
- cc4101 env 无漂移: PRIMARY_HEADER_TIMEOUT=60 / CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926 改) / CC4101_PRIMARY_SKIP_S=30 / CC4101_PRIMARY_FAIL_THRESHOLD=3. 与 R1943 完全一致.
- /health ok, docker ps 全 Up.
- nv_gw StartedAt 13:33:43Z (0 restart, 维 R1933). cc4101 StartedAt 12:10:22Z.
- SR 稳态区间内 (30min 78.9% 小样本 / 6h 93.8% 大样本), fallback 全兜住 0 真中断, breaker OPEN 0.

## 结论

- 连续冻结第 9 轮 (R1928 冻结 → R1929/R1930/R1931/R1933→R1946 NOP). 链路稳态持续, 0 真中断, abs_cap 持续归零.
- STATE.md 上半段仍过时停 R1931 (R1943 round 声称覆写但未落, 同 R1930/R1942 老问题). 本轮覆写 STATE.md 上半段对齐到 R1946 真实状态 (含 StartedAt 修正 R1918 10:42:20Z → R1933 13:33:43Z, 轮号基线推进 R1931 → R1946).
- 指数退避激活决策仍冻结: R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 4 坑 + 24h 观测) 仍成立, 当前链路稳态 (6h SR93.8% 0 真中断) + 本轮无新监督者激活指令 → 继续冻结.
