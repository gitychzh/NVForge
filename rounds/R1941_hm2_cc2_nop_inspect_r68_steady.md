# R1941 (HM2 cc2): NOP 巡检 R68 — 稳态持续, 6h SR95.2% 与 R1939 几乎一致, 0 真中断, 连续冻结延续

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / 不碰 ms_gw(40007)

## 本轮性质: NOP 巡检 (0 源码改动 0 env 改动 0 restart)

新 session 接手, 读 STATE.md 棒 (棒基线已到 R1939, 上轮已对齐过) + git pull 发现 git log 已推进到 R1940 (peer HM1→HM1 NOP R1940). 本轮 cc2 从 R1941 起.

棒记录上一轮 R1939 为 "连续冻结第 5 轮, R1933 NameError 修复后稳态持续". 本轮职责: 继续巡检 R1933 修复后稳态, 确认无回归无新 bug. 本轮 0 改动 0 restart.

## 数据 (本 session 拉取, DB 时钟 = 2026-07-19 ~23:00Z UTC, nv_gw StartedAt 13:33:43Z = 已起 ~9.5h)

### nv_gw 健康 + 源码状态
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (= R1933 restart, R1933→R1941 未再 restart, R1935/R1936/R1939 记录一致).
- cc4101 StartedAt = 2026-07-19T12:10:22Z (= R1926 step2.0 env up-d).
- /health ok (nv_num_keys=5, pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv).
- docker ps 全 Up (nv_gw Up 2 hours / ms_gw Up 2 days / cc4101 Up 3 hours / logs_db Up 2 days).
- **源码状态 = R1933 已验证后状态** (无漂移):
  - upstream.py:57 R1933 import 行在位 (`NVU_GLM52_EXP_BACKOFF, NVU_GLM52_EXP_BACKOFF_STEPS, NVU_GLM52_EXP_BACKOFF_CAP`).
  - upstream.py:1028-1035 R1928 半成品指数退避代码在位, py_compile OK (R1933 修 NameError 后).
  - config.py:522-527 R1928 半成品 config 在位.
  - **NVU_GLM52_EXP_BACKOFF env 未设=关** (R1928 半成品冻结, 从未 in-vivo 激活, 连续第 6 轮).

### 30min nv_gw 成功率 (本轮主窗口)
- SR = 49/53 = **92.5%** (200:49 / 502:4), 抖动区间中段常态 (R1929 91.7 / R1930 92.5 / R1931 91.4 / R1941 92.5, 非退化).
- 502 分类 (30min):
  - zombie_empty_completion ×3 (glm5_2_nv 出口 IP 段同源快回空, R1907-R1909 起持续同段)
  - all_tiers_exhausted ×1 (NVCF 上游侧 5 key×mode 全挂)
- **无新可配置类** (非 zombie/empty200/timeout/SSLEOFError/abs_cap/all_tiers_exhausted).
- tier 30min: pexec_success 51 / pexec_500 2 / pexec_SSLEOFError 2 / pexec_empty_200 1.

### 6h nv_gw 成功率 (对照窗口, 拿稳定样本)
- SR = 590/620 = **95.2%** (200:590 / 502:30) — 与 R1939 记录的 95.3% (583/612) 几乎完全一致, 稳态持续无退化.
- 502 分类 (6h, 全已知):
  - zombie_empty_completion ×16 (R1939 记 16, 完全一致)
  - all_tiers_exhausted ×9 (R1939 记 8, +1)
  - stream_first_byte_timeout ×3 (R1939 记 3, 完全一致)
  - stream_absolute_cap ×2 (R1939 记 2, 完全一致)
- abs_cap 6h=2 (连续多轮低位); first_byte_timeout 6h=3.

### fallback 率 (负向核心指标)
- 30min: **2** FALLBACK-OK + 2 SKIP-CIRCUIT, **0** fallback 失败 → ms_gw 全兜住, **0 真中断** (CC 收 0 真 502).
  - 全 "PRIMARY-FAIL primary timeout after 75082ms < chain budget 120s" + "PRIMARY-FAIL-SKIP-CIRCUIT 75s < chain budget 120s, likely cc4101 pre-empted nv_gw retry" → cc4101 75s 抢断切 ms, ms 4.4-31.5s 救回, 0 失败.
  - 75s < 120s = cc4101 pre-empted nv_gw retry (cc4101 bug3 preempt 层, PRIMARY_HEADER_TIMEOUT=60+余量), 非 nv_gw 旋钮可解.
- 6h: **64** FALLBACK-OK + **28** SKIP-CIRCUIT, **0** fallback 失败 → ms_gw 全兜住, **0 真中断** (与 R1939 记录 61+25 同量级).

### breaker 状态
- nv_gw NV-ANTH-BREAKER-FAIL 30min = 1 次 (req=92044b8b, zombie_empty_completion, state=CLOSED(1,0) 吸收未 OPEN).
- nv_gw NV-ANTH-BREAKER-FAIL 6h = 7 次 (R1939 记 6, +1, 仍全被 CLOSED 吸收).
- nv_gw breaker **OPEN 0 连续多轮** (R1939 同).
- cc4101 primary circuit OPEN 6h = 14 次 (与 R1939 记录一致, 仍是 R1939 记的 21:27-21:33 一次性突发 ~7 分钟 14 次 OPEN, 之后 ~1.5h+ 0 OPEN, 已自愈 CLOSED). 最近 30min 0 PRIMARY-FAIL 0 breaker OPEN.

## 介入四条核对 → 全不满足 → NOP 无据不改
1. **SR 95.2% (6h) / 92.5% (30min)** 稳态持续, 远未达"连续 3+ 轮跌破 80%"介入线 → 不介入.
2. **502=30 (6h) / 4 (30min) 全已知分类** (zombie/ATE/first_byte_timeout/abs_cap), 无新可配置类 → 不介入.
3. **breaker OPEN**: nv_gw OPEN 0 连续多轮; cc4101 OPEN 14 次仍是 R1939 记的 21:27-33 一次性突发已自愈, 最近 1.5h+ 0 OPEN → 不介入 (非持续 OPEN 退化).
4. **指数退避激活决策仍冻结 (连续第 6 轮)**: R1928 半成品 (upstream.py:1027-1037 + config.py:522-527) env NVU_GLM52_EXP_BACKOFF 未设=关, R1933 只修了 NameError 让潜在 bug 不 crash, 但半成品逻辑本身从未 in-vivo 激活. 激活仍需同步 4 坑 (chain_budget 120→420 / cc4101 header 60→450 / post-200 软挂换 key 未实现 / abs_cap 150→250+). 当前链路稳态 (SR95.2% 0 真中断) + 本轮无新监督者激活指令 → 继续冻结. 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.

## 验证 (NOP 轮, 0 改动故 0 restart, 但确认稳态)
- env 无漂移: UPSTREAM_TIMEOUT=66 / NVU_TIER_BUDGET_GLM5_2_NV=120 / TIER_TIMEOUT_BUDGET_S=180 / NVU_STREAM_ABSOLUTE_CAP_S=150 / KEY_COOLDOWN_S=25 / KEY_AUTHFAIL_COOLDOWN_S=60 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_COOLDOWN_S=180 / NV_INTEGRATE_KEY_COOLDOWN_S=90 / TIER_COOLDOWN_S=25 / MIN_OUTBOUND_INTERVAL_S=0 / NVU_GLM52_EXP_BACKOFF 未设=关 (与 R1931/R1939 快照完全一致).
- cc4101 env 无漂移: PRIMARY_HEADER_TIMEOUT=60 / CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926 改) / CC4101_PRIMARY_SKIP_S=30 / CC4101_PRIMARY_FAIL_THRESHOLD=3.
- /health ok, docker ps 全 Up, nv_gw StartedAt 13:33:43Z (R1933 restart 后 0 restart), cc4101 StartedAt 12:10:22Z.

## 下一步
- 继续巡检, 拉下轮 30min/6h 数据看 SR/fallback/breaker 抖动是否仍在已知区间. 当前 SR 92.5%/95.2% 稳态, 0 真中断.
- 指数退避激活决策仍冻结 (连续第 6 轮): R1928 冻结理由仍成立 (半成品未 in-vivo 验证 + 激活需同步 4 坑). 等监督者再授权或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.
- 若 SKIP-CIRCUIT 75s 抬头突然飙升 (>15/30min) 且 breaker 开始持续 OPEN, 才考虑调 breaker 阈值或 TIER_TIMEOUT_BUDGET — 当前属 cc4101 bug3 preempt 层, nv_gw 旋钮解不了.
- peer HM1 agent 持续在 HM1 侧收紧 (R1937/R1940 等), 抢号区间, 写轮前必 git pull 看最新号 +1 防 peer 抢号.
