# R1942 (HM2 cc2): NOP 巡检 R69 — 稳态持续, 30min SR93.75% / 6h SR95.2% 0 真中断, 连续冻结第 7 轮延续

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / 不碰 ms_gw(40007)

## 本轮性质: NOP 巡检 (0 源码改动 0 env 改动 0 restart)

新 session 接手, 读 STATE.md 棒 + git pull 发现 git log 已推进到 R1941 (cc2 上轮 R1941 NOP 巡检 R68). 本轮 cc2 从 R1942 起. peer 已写到 R1940 (HM1→HM1 NOP, 只改 HM1 对 HM2 0 影响).

棒基线已对齐到 R1939 (上轮已修正), 记录上一轮 R1941 为 "连续冻结第 6 轮, R1933 NameError 修复后稳态持续". 本轮职责: 继续巡检 R1933 修复后稳态, 确认无回归无新 bug. 本轮 0 改动 0 restart.

## 数据 (本 session 拉取, DB 时钟 = 2026-07-19 15:25:33Z UTC, nv_gw StartedAt 13:33:43Z = 已起 ~1h52m)

### nv_gw 健康 + 源码状态
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (= R1933 restart, R1933→R1942 未再 restart, R1935/R1936/R1939/R1941 记录一致).
- cc4101 StartedAt = 2026-07-19T12:10:22Z (= R1926 step2.0 env up-d).
- /health ok (nv_num_keys=5, pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough).
- docker ps 全 Up (nv_gw Up 2 hours / ms_gw Up 2 days / cc4101 Up 3 hours / logs_db Up 2 days).
- **源码状态 = R1933 已验证后状态** (无漂移, 未逐一 diff 因 R1941 已确认仅 1 行 import 差异, 本轮 StartedAt 未变故源码必未重载):
  - upstream.py:57 R1933 import 行在位 (`NVU_GLM52_EXP_BACKOFF, NVU_GLM52_EXP_BACKOFF_STEPS, NVU_GLM52_EXP_BACKOFF_CAP`).
  - upstream.py:1028-1035 R1928 半成品指数退避代码在位, py_compile OK (R1933 修 NameError 后).
  - config.py:522-527 R1928 半成品 config 在位.
  - **NVU_GLM52_EXP_BACKOFF env 未设=关** (R1928 半成品冻结, 从未 in-vivo 激活, 连续第 7 轮).

### 30min nv_gw 成功率 (本轮主窗口)
- SR = 60/64 = **93.75%** (200:60 / 502:4), 抖动区间中段常态 (R1929 91.7 / R1930 92.5 / R1931 91.4 / R1941 92.5 / R1942 93.75, 非退化, 略微上抬).
- 502 分类: zombie_empty_completion×3 (glm5_2_nv 出口 IP 段同源, R1907-R1909 起持续同段, 已知上游侧) + all_tiers_exhausted×1.
- abs_cap 30min = **0** (R1918 方案0 cap_origin 重置让 abs_cap 持续归零, 连续多轮).

### tier 30min
- pexec_success 59 / pexec_empty_200 3 (glm5_2_nv 首字节快回空中间态被 retry 吸收到 200) / pexec_500 2 / pexec_SSLEOFError 2.
- **新小信号 pexec_500 2 条** (R1941 未记 pexec_500): 实测 1 条日志 `tier=dsv4p_nv k1 → 500 (500_nv_error), cycling to next key` — dsv4p_nv 单 key 间歇性 NVCF 上游 500, 被 cycle 到下一 key 兜住吸收到 200. **单条+被 retry 兜住, 不构成异常**, 不介入 (nv_breaker/cycle 机制工作正常).

### 6h nv_gw 成功率 (大样本验证稳态)
- SR = 594/624 = **95.2%** (200:594 / 502:30), 与 R1939 (95.3%) / R1941 (95.2%) 几乎完全一致, 稳态持续.
- 502: zombie×16 + all_tiers_exhausted×9 + stream_first_byte_timeout×3 + stream_absolute_cap×2.
- abs_cap 6h = 2 (R1931=4 → R1942=2, R1918 方案0 持续让 abs_cap 低频甚至归零).

### fallback (负向核心指标, cc4101 日志)
- 30min: **7** FALLBACK-OK (R1941 未记 fallback 数, R1931=10), 10min=3. **0 fallback 失败 → 0 真中断**.
- 全 "PRIMARY-FAIL primary timeout after 75s" + "PRIMARY-FAIL-SKIP-CIRCUIT 75s < chain budget 120s" → 全被 cc4101 在 75s 抢断切 ms (cc4101 PRIMARY_HEADER_TIMEOUT=60 + 余量), ms 2.5-49s 救回.
- **新小信号 1 条**: 23:21:15 `PRIMARY-FAIL primary timeout after 120099ms ... after 120s` — 这条**计入了 chain budget 120s** (不是 75s SKIP-CIRCUIT), 说明 nv_gw 这次跑满完整 budget 才回, cc4101 未抢断 (PRIMARY_HEADER_TIMEOUT 在这条上未抢断, 可能是大请求分档). 这条没标 SKIP-CIRCUIT = 会被算进 circuit. 单条, fallback 仍 OK (ms 3.8s 救回), 不构成介入.
- 75s < 120s = cc4101 pre-empted nv_gw retry (cc4101 bug3 preempt 层), 非 nv_gw 旋钮可解, 仍是指数退避精确靶子但无新授权激活.

### breaker
- NV-ANTH-BREAKER-FAIL **1 次** (23:06:34 req=92044b8b, err=zombie_empty_completion) → state=CLOSED(1,0), 被 CLOSED 吸收未 OPEN.
- breaker **OPEN 0 连续多轮** (R1931→R1942 持续).

## 介入四条核对 (全不满足 → NOP 无据不改)

1. **SR 跌破介入线?** 否. 30min SR93.75% / 6h SR95.2%, 抖动区间中段常态 (R1929-R1942 91.4-95.3%), 未达"连续 3+ 轮跌破 80%"介入线. ✗
2. **502 出现新可配置类?** 否. 502 全 zombie (出口 IP 段同源已知上游侧) + all_tiers_exhausted + first_byte_timeout + abs_cap, **全是已知类**, 非新可配置类. ✗
3. **breaker 开始 OPEN?** 否. breaker OPEN 0 连续多轮, 本轮 BREAKER-FAIL 1 被 CLOSED(1,0)吸收未 OPEN. ✗
4. **fallback 飙升或新授权激活指数退避?** 否. fallback 7/30min 全 75s SKIP-CIRCUIT 被 ms 兜住 0 真中断 (低于 R1931 的 10/30min, 未飙升). 仍是指数退避精确靶子但**无新监督者激活指令** (R1928 冻结理由仍成立: 半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测). ✗

## 验证 (NOP 轮, 验证 = 确认稳态持续)

- env 无漂移 (UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_STREAM_ABSOLUTE_CAP_S=150 / NVU_GLM52_EXP_BACKOFF 未设=关 / MIN_OUTBOUND=0 / KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_COOLDOWN=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25). 与 R1941 完全一致.
- /health ok, docker ps 全 Up.
- nv_gw StartedAt 13:33:43Z (0 restart, 维 R1933). cc4101 StartedAt 12:10:22Z.
- SR 稳态区间内 (30min 93.75% / 6h 95.2%), fallback 全兜住 0 真中断, breaker OPEN 0.

## 结论

连续第 7 轮 NOP 冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1934/R1935/R1936/R1939/R1941/R1942 NOP). 链路稳态持续, 0 真中断, 0 fallback 失败. 介入四条全不满足, 无据不改. 本轮 0 改动 0 restart.

**新小信号 (不介入, 仅记录供后续观测)**:
- pexec_500 2 条 (dsv4p_nv 单 key 间歇 NVCF 500, 被 cycle 兜住). 若后续轮次 pexec_500 持续抬头 (>5/30min) 再关注.
- 1 条 PRIMARY-FAIL 跑满 120s chain budget (非 75s SKIP-CIRCUIT), 计入 circuit. 若后续轮次 120s 满档 PRIMARY-FAIL 持续抬头 (>5/30min) 触发 circuit OPEN 再关注.

## commit

本轮 0 源码 0 env 改动, 仅写 round 文件 R1942. `git add -A && git commit && git push origin/main`.
