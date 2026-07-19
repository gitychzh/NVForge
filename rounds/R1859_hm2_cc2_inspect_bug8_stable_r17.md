# R1859 (HM2 cc2) — 巡检轮 bug8 降级兜底 in-vivo 后第 17 轮持续 0 触发 链路稳 SR95.2%

## 改前数据 (30min 窗, 2026-07-19 07:48-08:18 CST 本 session 拉取)
- **SR 30min = 99/104 = 95.2%** (200:99 / 502:5)。**>=93%, 抖动区间常态确认, 本轮再加反弹**。
  近 7 轮标定: R1853 94.8% / R1854 94.7% / R1855 94.6% / R1856 92.6% / R1857 90.2% / R1858 94.7% / R1859 本轮 95.2%。
  R1856+R1857 连 2 轮破 93 被 R1858 (94.7) 反弹打断, R1859 (95.2) 进一步上扬 → **未达连续 >=3 轮破 93 触发线**, 抖动区间常态。
- 5 条 502 = 3 zombie_empty_completion + 1 all_tiers_exhausted + 1 stream_absolute_cap,
  **全 NVCF 侧偶发外分支 config 不可修** (与 R1851-R1858 同构)。
- tier pexec 30min: pexec_success 80 / pexec_SSLEOFError 2 / pexec_empty_200 2 / NVCFPexecTimeout 1 / pexec_429 1 / pexec_timeout 1。
  **无 zombie 无 ATE (all_tiers_exhausted 在 nv_requests 顶层 1 条, 非 pexec 行)**。
- fallback 30min: 2 条 (07:52:32 req=0ded572c + 07:59:37 req=063ad0de)
  全 PRIMARY-FAIL-SKIP-CIRCUIT (primary timeout after 75058ms / 75038ms < chain budget 120s,
  bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 **NOT counted**)
  → 后 FALLBACK-OK ms 成功 (3842ms / 2912ms 递进合法)。
  **非跳过类真请求失败 0 条**, < 4 阈值。**0 中断**。
- bug8: **实战降级触发 0** (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗 = 0)。
  兜底保险在位但 args 全合法不需触发, 符合 R1839 round 原话"兜底保险就该几乎不触发"。
- breaker 30min: 4 条 NV-ANTH-BREAKER-FAIL 全 CLOSED:
  (1,0) req=8da05d44 / (2,0) req=51487ebf / (2,0) req=a474544f / (1,0) req=6b47318d
  (zombie 软挂 + 1 stream_absolute_cap, 未超 zombie 软挂阈值)
  + 1 NV-ANTH-ABS-CAP (req=a474545f, cap_elapsed=221s 超 150s, total_elapsed=221s, content_chars=0,
  与 R1857/R1858 一致, 比 R1852-R1856 159s 变长, 单请求墙钟逃逸) **未 OPEN**, 设计内。
  注: abs_cap 221s 调高 STREAM_ABS_CAP 150s 检测线 = 死循环请回复, 违反 CLAUDE.md 不动。
- env 无漂移: KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NV_INTEGRATE_KEY_COOLDOWN=90 /
  TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 / NVU_BIG_INPUT_FAIL_N=1 /
  UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / MIN_OUTBOUND_INTERVAL_S=0。
  全与 R1850-R1858一致。
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
   container `/app/gateway/format/oai_to_anth.py`),
  `_detect_bad_tool_args()` + finish() `_downgrade_to_end_turn` flag + 两处 final_stop 强制 end_turn
  (zombie 修路 / 正常完成路径) 四要素全在。
- nv_gw 真实 StartedAt = **2026-07-18T21:26:29Z** (R1836 restart, R1839 至 R1859 未再 restart) → 跑 R1839 改后字节码。
  (docker ps "Up 3 hours" 是粗略显示; 精确以 docker inspect StartedAt 为准。)
- /health ok: {"status":"ok", nv_num_keys=5, nv_default_model=dsv4p_nv, port=40006}。
  docker ps: nv_gw Up 3h / cc4101 Up 16h / ms_gw Up 44h 三件套在位 (ms_gw 热备不动)。

## 改了什么
NOP (不改)。无 compose env / 无 .py 改动 / 0 restart。

## 决策理由
介入触发四条全不满足:
1. SR 连续 >=3 轮破 93: **否** (R1856 92.6+R1857 90.2 只连 2 轮, R1858 94.7+R1859 95.2 反弹打断)。
2. fallback 非跳过类真失败 >=4: **否** (=0)。
3. NV-ANTH-BREAKER-FAIL 出现 OPEN: **否** (全 CLOSED)。
4. 新的可配置错误分类: **否** (5 条 502 全 NVCF 侧 zombie/all_tiers/abs_cap config 不可修)。
硬改违反铁律 (改前必有数据 + 无据不改)。abs_cap 221s 调高破坏安全网不动。

## 验证结果
链路稳: SR 95.2% (>=93 抖动区间常态) + bug8 0 触发 (兜底在位) + breaker 全 CLOSED +
fallback 非跳过类 0 + 0 中断 + 0 restart。 StartedAt 仍 21:26:29Z 跑 R1839 改后字节码。/health ok。

## 下轮 R1860 建议
继续常规巡检。重点看 SR 走向:
- 若 SR >=93% → 抖动区间常态, 继续 NOP。
- 若 SR <93% → 只算 1 轮新破 93 (R1856+R1857 旧 2 轮已被 R1858+R1859 反弹打断, 不能拼成 3)。
  若此后再连续 3 轮破 93 达触发线需介入排查 (仍需先定位可配置旋钮; 若 502 全 NVCF 侧 config 不可修仅可记录归因)。
连续 17 轮 NOP (R1842-R1859) 链路稳态, 当前无数据支持主动改。
