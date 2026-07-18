# R1837 — HM2 cc2 巡检轮: R1836 `{"command": "` 前缀过滤 19min 纯净窗生效确认

## 性质
巡检轮 (不改代码, 不 restart)。接手 R1836 round "下轮 R1837" 任务: 拉 restart 后更长纯净窗确认 R1836
扩前缀过滤真正生效 (R1836 当时仅 6min 窗)。本轮拉到 19min 纯净窗 (距 R1836 restart 21:26:29Z 累计
19min, 仍 < R1836 期望 30min 但已比 6min 长 13min, 方向明确 0 命中)。

## 改前数据 (30min 窗, 当前 21:46 UTC = 05:46 CST, StartedAt 21:26:29Z = R1836 restart 后)
- **30min SR = 92/95 = 96.8%** (200:92, 502:3), 与 R1834 96.8% 持平, 比 R1835 97.8% 低 1.0pp, **仍
  远在 95% 安全线之上**。error 3 条 (502) 全 `zombie_empty_completion`: 4204c0c4@21:17 (restart 前
  R1832 代码残留) + 9ecf09cb@21:29 + 41ddab93@21:45 (restart 后 2 条)。zombie = NVCF 侧 tool_calls
  空内容, 非 nv_gw config 可修, 与 R1836 混合窗 4 zombie 同形, 非恶化。
- **tier (nv_tier_attempts 30min)**: pexec_success 81 / IntegrateTimeout 1 / pexec_SSLEOFError 1,
  非常干净 (5 key 各 ≤1 失败, 非系统性)。
- **pexec elapsed (duration_ms, status=200, 30min)**: max=**509858ms (~510s)** / avg=22984ms (~23s) /
  ge60s=5 / **ge200s=2**。表面看 max 510s 破 R1835/R1836 67s/59s, 但**根因细分**:
  - **2a84b09a (509858ms @21:44)**: NVCF 真长跑, 非 cc2 自反馈。日志核: 21:40:29 NV-GLM52-TIMEOUT
    (k2 56s) → mode advance → 21:42:29 NV-TIER-BUDGET tier=glm5_2_nv budget 120s 超限 → 21:42:29
    NV-TIER-FAIL all 5 keys failed → 21:42:29 NV-ALL-TIERS-FAIL ABORT-NO-FALLBACK → 21:42:32
    **NV-MS-FB-SERVED ms_gw fallback 成功** (after 2911ms, breaker=CLOSED 未 OPEN) → DB 记 200 因
    用户走 ms 拿到内容。**tier_budget 120s + MS-fallback 机制按 R838/R1818 设计兜住真长跑, 0 中断**。
  - **4e8fb7a9 (389494ms @21:19)**: = bug8 自反馈命中之一 (bash heredoc 写 STATE 形态, 时间戳
    21:19:32 在 R1836 restart 21:26 之前 = R1832 单前缀代码漏网), 完成长但无中断。
  - → **这 2 条 ge200s 全非 NVCF pexec 首字节系统性恶化**: 1 条是 R1836 过滤要盖的 self-fb 残留 +
    1 条是 tier_budget 兜住的单次 NVCF 真长跑 (走 ms 成功)。NVCF 真 pexec 首字节慢仍是 ~84s 档
    (a80c78bd 84s), 与 R1835 的 67s 同档, 非恶化趋势。
- **fallback 30min = 2 SKIP-CIRCUIT** (35aac1f2@05:37 / ee84fa56@05:41), 全 `primary timeout after
  75049/75069ms < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit`,
  **2 rids 全部 nv_requests 0 rows** = 未到 nv_gw 写库 = cc4101 侧 bug3 (75s ttfb 抢断甩 ms) 非
  nv_gw config 可控。全 FALLBACK-OK **0 中断**。比 R1835 的 5 条持平档 (restart 后纯净 19min 窗内 2
  条, 非恶化)。
- **NV-ANTH-BREAKER-FAIL (带 -t)**: 2 条 zombie_empty_completion 软挂记录 (4204c0c4@21:17 restart 前
  + 9ecf09cb@21:29 restart 后), nv_breaker state=('CLOSED', 3, 0)→('CLOSED',1,0) 跳, 未累积到 OPEN
  阈值。设计内"记录软挂但不 OPEN", 合法, 非恶化。
- **bug8 观测层关键结论 (R1836 扩前缀 19min 纯净窗首次确认)**:
  - `docker logs nv_gw -t --since 60m | grep NV-TOOLCALL-JSON-BAD` = **2 条**, 时间戳
    **21:03:08** (c83bc5ac) 和 **21:19:32** (4e8fb7a9), **全在 R1836 restart (21:26:29Z) 之前**
    (23min/7min前)。两 frag 前缀均为 `{"command": "cat > ...STATE.md << 'STATEEOF'\n# cc2...`,
    bash heredoc 写 STATE/round 文件形态, 正是 R1836 加 `{"command": "` 前缀要盖的 R1832 单前缀
    漏网路径 → **这 2 条是触发 R1836 改动的实测依据** (与 R1836 round 文件记录一致)。
  - **restart 后纯净 19min 窗 (21:26:29Z+, since 19m/20m) `docker logs nv_gw -t` grep = 0** →
    **R1836 `{"command": "` 前缀过滤生效确认** (本轮把 R1836 仅 6min 窗延长到 19min, 方向 0 命中)。
  - 30min 不带 -t 的 grep = 1 条, 对应 21:17 那条 (restart 前 R1832 代码残留), 不在 restart 后纯净
    窗内, 不算 R1836 漏网。
  - → **bug8 普通流量连续第 9 轮 (R1829-R1837) 零真畸形**, "真安静期"延续 (R1835 成立延续 + R1836
    扩前缀盖 bash heredoc 第二路径 + R1837 19min 纯净窗确认)。

## 决策 (不改代码)
SR 96.8% 稳 (远离 95% 线) + R1836 扩前缀过滤 19min 纯净窗 0 命中生效确认 + ge200s 2 条细分全非
NVCF 系统性恶化 (1 条 tier_budget 兜住走 ms 成功 + 1 条 self-fb 残留) + fallback 2 全 cc4101 侧 bug3
0 中断 + breaker 全 CLOSED 未 OPEN (zombie 软挂记录非累积) + env 无漂移 + md5 同步 → 链路稳, R1836
改动良性生效, **无 nv_gw config 可改依据**。硬改任何旋钮 (UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=
180 / NVU_TIER_BUDGET_GLM5_2_NV=120 均合理值; bug3+ge200s NVCF 长跑根因 NVCF 侧 nv_gw 不可控; zombie
NVCF 侧 tool 空内容) 违反"改前必有数据, 改后必有验证"铁律 → 巡检轮不动。

## 验证 (无需 restart, 仅观测)
- `curl /health` ok: passthrough / nv_num_keys=5 / nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv]
  / nv_default_model=dsv4p_nv。
- `docker inspect nv_gw --format StartedAt` = **2026-07-18T21:26:29Z** (= 05:26 CST, R1836 restart
  后; R1837 未再 restart)。docker ps: nv_gw Up 19min, ms_gw Up 41h (热备未碰), cc4101 Up 14h。
- bind-mount md5 宿主/容器一致 `08cd8bd7450164080c56cec7d513de28` (R1836 改动在位, R1837 未碰)。
- env 无漂移 (NVU_TIER_BUDGET_GLM5_2_NV=120 / UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 /
  KEY_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1 / NVU_STREAM_ABSOLUTE_CAP_S=150 / NVU_TIER_BUDGET_DSV4P_NV=70
  全与 R1833/R1834/R1835/R1836 一致)。
- **0 中断** (本轮无 restart, 全程直连, 全 fallback 均 FALLBACK-OK, 2a84b09a 走 ms 兜底也 0 中断)。

## 铁律遵循
- 改前必有数据: ✅ 30min 窗拉满 (SR/error/tier/pexec duration/fallback/breaker/bug8) + 60min bug8
  带 -t 时间戳核 R1836 改动触发依据属实 (2 条 R1832 残留全在 restart 前) + 19min 纯净窗确认生效。
- 聚焦 40006: ✅ 只看 nv_gw, 不碰 proxy/ms-gw。
- 只改 HM2: ✅ 仅观测, 未改 HM2 任何源码/配置, 未碰 HM1。
- 写入仓库: ✅ 本 round 文件 + commit+push + 覆写 STATE (补回 R1834/R1835/R1836 落差, 因 STATE.md
  仍停在 R1833 但仓库已到 R1836)。

## 下轮 (R1838) 该做什么
1. **读本 STATE** (R1837 巡检确认 R1836 扩前缀 19min 纯净窗 0 命中生效)。
2. **拉满 30min 纯净窗** (全在 21:26:29Z 之后, R1837 时距 restart 19min, 下轮距 restart ≥31min 后
   再拉满 30min) 再确认 R1836 `{"command": "` 前缀过滤真正持续生效 — 若满 30min 纯净窗 0 命中 →
   R1836 双前缀 (R1832 `{"content": "#` + R1836 `{"command": "`) 完全盖住自反馈两路径, bug8 真安静
   期坐实。
3. 继续拉 SR/fallback/pexec duration 确认链路稳: 若 SR 持续 ≥95% + fallback 低位 + pexec ge200s 不
   持续多条 → 稳; 若 2a84b09a 这类 NVCF 真长跑 → ge200s 持续多条 → bug3 根因 NVCF 侧 nv_gw 不可
   可控, 保持现状 (tier_budget 120s 已兜住走 ms 0 中断)。
4. commit+push R1838 round 文件 + 覆写 STATE。
