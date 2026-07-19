# R1943 (HM2 cc2): NOP 巡检 R70 — 稳态持续, 30min SR94.7% / 6h SR94.9% 0 真中断, 连续冻结第 8 轮延续

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / 不碰 ms_gw(40007)

## 本轮性质: NOP 巡检 (0 源码改动 0 env 改动 0 restart)

新 session 接手, 读 STATE.md 棒 + git pull 发现 git log 已推进到 R1942 (cc2 上轮 R1942 NOP 巡检 R69, peer 刚写 fe8b253 HM2→HM1 NOP 只改 HM1 对 HM2 0 影响). 本轮 cc2 从 R1943 起. STATE.md 棒基线**仍过时停 R1931** (R1942 round 文件声称覆写但实际未落, 同 R1930 当时的问题), 本轮职责:
1. 继续巡检 R1933 NameError 修复后稳态, 确认无回归无新 bug.
2. 覆写 STATE.md 上半段对齐到 R1943 真实状态.

## 数据 (本 session 拉取, DB 时钟 = 2026-07-19 15:36:47Z UTC = 23:36 CST, nv_gw StartedAt 13:33:43Z = 已起 ~2h)

### nv_gw 健康 + 源码状态
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (= R1933 restart, R1933→R1943 未再 restart, R1935/R1936/R1939/R1941/R1942 记录一致).
- cc4101 StartedAt = 2026-07-19T12:10:22Z (= R1926 step2.0 env up-d).
- /health ok (nv_num_keys=5, pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough).
- docker ps 全 Up (nv_gw Up 2 hours / ms_gw Up 2 days / cc4101 Up 3 hours / logs_db Up 2 days).
- **源码状态 = R1933 已验证后状态** (无漂移): `docker exec nv_gw diff upstream.py upstream.py.bak.R1933` = **仅 1 行** (line 57 R1933 import 行: `NVU_GLM52_EXP_BACKOFF, NVU_GLM52_EXP_BACKOFF_STEPS, NVU_GLM52_EXP_BACKOFF_CAP`). 与 R1939/R1942 记录完全一致, 0 漂移.
- **NVU_GLM52_EXP_BACKOFF env 未设=关** (R1928 半成品冻结, 从未 in-vivo 激活, 连续第 8 轮).

### 30min nv_gw 成功率 (本轮主窗口)
- SR = 71/75 = **94.7%** (200:71 / 502:4), 抖动区间中段常态 (R1929 91.7 / R1930 92.5 / R1931 91.4 / R1941 92.5 / R1942 93.75 / R1943 94.7, 非退化, 略微上抬).
- 502 分类: zombie_empty_completion×3 (glm5_2_nv 出口 IP 段同源, R1907-R1909 起持续同段, 已知上游侧) + all_tiers_exhausted×1.
- abs_cap 30min = **0** (R1918 方案0 cap_origin 重置让 abs_cap 持续归零, 连续多轮).

### tier 30min
- pexec_success 68 / pexec_empty_200 6 (glm5_2_nv 首字节快回空中间态被 retry 吸收到 200). 无 SSLEOFError, 无 pexec_500 (R1942 记 2 条 dsv4p_nv 单 key 间歇 500 被兜住, 本轮未再现, 信号未抬头).

### 6h nv_gw 成功率 (大样本验证稳态)
- SR = 610/643 = **94.9%** (200:610 / 502:33), 与 R1939 (95.3%) / R1942 (95.2%) 几乎完全一致, 稳态持续.
- 502 分类全已知: zombie_empty_completion×16 (glm5_2_nv 出口 IP 段同源) + all_tiers_exhausted×10 (dsv4p_nv, 70s ATE, NVCF 上游侧) + stream_absolute_cap×2 + stream_first_byte_timeout×2.
- **无新可配置类** (非 zombie/empty200/timeout/SSLEOFError/abs_cap/all_tiers_exhausted).
- abs_cap 6h = 2 (R1931=4 → R1942=2 → R1943=2, R1918 方案0 持续让 abs_cap 低频).

### fallback (负向核心指标, cc4101 日志)
- 30min: **8** FALLBACK-OK, **0** fallback 失败 → **0 真中断**.
- 全 "PRIMARY-FAIL-SKIP-CIRCUIT primary timeout after 75s < chain budget 120s" → 全被 cc4101 在 75s 抢断切 ms (cc4101 PRIMARY_HEADER_TIMEOUT=60 + 余量), ms 兜回救.
- **6h**: 71 FALLBACK-OK, 0 fallback 失败 → 0 真中断 (CC 收 0 真 502).
- 75s < 120s = cc4101 pre-empted nv_gw retry (cc4101 bug3 preempt 层), 非 nv_gw 旋钮可解, 仍是指数退避精确靶子但无新授权激活.

### breaker
- cc4101 primary circuit OPEN 6h = **14, 全集中 21:27-21:33 CST (13:27-13:33 UTC) 一次性突发** (与 R1939 记录的 21:27-21:33 突发是同一旧事件, 容器未重启日志累积; R1939 当时已自愈, 非 R1943 新退化). **30min 内 PRIMARY-BREAKER-OPEN = 0** (突发后 ~2h 无新 OPEN, 持续自愈 CLOSED).
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **2 次** (23:32:15 req=3d59fa64, 23:34:13 req=4f25c3e0, err=zombie_empty_completion) → state=CLOSED(3,0), 被 CLOSED 吸收未 OPEN.
- breaker **OPEN 0 连续多轮** (R1931→R1943 持续).

## 介入四条核对 (全不满足 → NOP 无据不改)

1. **SR 跌破介入线?** 否. 30min SR94.7% / 6h SR94.9%, 抖动区间中段常态 (R1929-R1943 91.4-95.3%), 未达"连续 3+ 轮跌破 80%"介入线. ✗
2. **502 出现新可配置类?** 否. 502 全 zombie (出口 IP 段同源已知上游侧) + all_tiers_exhausted + first_byte_timeout + abs_cap, **全是已知类**, 非新可配置类. ✗
3. **breaker 开始 OPEN?** 否. cc4101 PRIMARY-BREAKER-OPEN 6h=14 全集中 21:27-21:33 CST 一次性突发 (R1939 旧事件非新退化), 30min=0 已自愈; nv_gw BREAKER-FAIL 30min=2 被 CLOSED(3,0) 吸收, OPEN 0 连续多轮. ✗
4. **fallback 飙升或新授权激活指数退避?** 否. fallback 8/30min 全 75s SKIP-CIRCUIT 被 ms 兜住 0 真中断 (低于 R1931 的 10/30min, 未飙升). 仍是指数退避精确靶子但**无新监督者激活指令** (R1928 冻结理由仍成立: 半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测). ✗

## 验证 (NOP 轮, 0 改动故 0 restart, 但确认稳态)

- env 无漂移 (UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_STREAM_ABSOLUTE_CAP_S=150 / NVU_GLM52_EXP_BACKOFF 未设=关 / MIN_OUTBOUND=0 / KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_COOLDOWN=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25). 与 R1942 完全一致.
- cc4101 env 无漂移: PRIMARY_HEADER_TIMEOUT=60 / CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926 改) / CC4101_PRIMARY_SKIP_S=30 / CC4101_PRIMARY_FAIL_THRESHOLD=3. 与 R1942 完全一致.
- /health ok, docker ps 全 Up.
- nv_gw StartedAt 13:33:43Z (0 restart, 维 R1933). cc4101 StartedAt 12:10:22Z.
- 源码 diff vs R1933.bak 仅 1 行 import (无漂移).
- SR 稳态区间内 (30min 94.7% / 6h 94.9%), fallback 全兜住 0 真中断, breaker OPEN 0.

## 结论

连续第 8 轮 NOP 冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1934/R1935/R1936/R1939/R1941/R1942/R1943 NOP). 链路稳态持续, 0 真中断, 0 fallback 失败. 介入四条全不满足, 无据不改. 本轮 0 改动 0 restart.

**新小信号 (不介入, 仅记录供后续观测)**:
- R1942 记的 pexec_500 2 条 (dsv4p_nv 单 key 间歇 NVCF 500) 本轮未再现, 信号未抬头. 若后续轮次 pexec_500 持续抬头 (>5/30min) 再关注.
- 21:27-21:33 CST breaker OPEN 一次性突发 (R1939 已记) 仍滞留在 cc4101 6h 窗内 (容器未重启日志累积), 已自愈非新退化.

## commit

本轮 0 源码 0 env 改动, 仅写 round 文件 R1943 + 覆写 STATE.md 对齐到 R1943. `git add -A && git commit && git push origin/main`.
