# R1879 (HM2 cc2) — 巡检轮 bug8 降级兜底 in-vivo 后第35轮持续0触发

## 链路稳态持续确认,但本窗出现 SR 单窗探底 88.9% + pexec_SSLEOFError 批量化苗头 + all_keys_exhausted 增多

**改了什么**: NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 改前数据 (30min 窗, 本 session ~11:08 CST 拉取)

### SR
- SR **48/54 = 88.9%** (200:48 / 502:6). **本窗跌破 93% 阈值,但仅 1 轮 (第1轮新破)**.
- 抖动区间此前的连续 >93 序列: R1875 96.7 / R1877 93.65 / R1878 94.2, 全 >93.
- 本轮 R1879 88.9 是 **第 1 轮破 93** → 连破计数重启为 1 (旧 2 轮 R1856 92.6+R1857 90.2 早被 R1858 94.7 反弹打断,
  本轮单窗破 93 不能与旧 2 轮拼成 3 触发线). **需 R1880+ 续破 2 轮累计达 3 才介入**. 未达介入线.
- 502 分类 (status=502, 共 6 条):
  - zombie_empty_completion 3 (NVCF 侧 zombie 偶发, 已知分类 config 不可修, R1851+ 间歇).
  - all_tiers_exhausted 2 (tier 全 key 耗尽兜底, 与本窗下半 all_keys_exhausted 增多同源).
  - stream_absolute_cap 1 (NVCF 侧 abs_cap, 已知分类 config 不可修).
  - **全 NVCF 侧偶发外分支 + tier 耗尽兜底, 非新可配置错误分类**, 与 R1875-R1878 同构 (本窗无 stream_first_byte_timeout).

### tier pexec (30min)
- pexec_success 36 (干净基底).
- **pexec_SSLEOFError 6** (**本窗批量化的苗头**): R1877 首现 1 → R1878 1 (连续 2 轮单点) → 本轮 R1879 6.
  连续 3 轮观察序列显示 SSLEOFError 在**化**: 从单点 (1) → 批量 (6). 但 SSLEOFError 本身是
  NVCF 侧 TLS / 上游连接层 (SSL EOF = TLS 连接被上游异常关闭), **不是 nv_gw config 可调旋钮**
  (改 UPSTREAM_TIMEOUT / TIER_TIMEOUT_BUDGET / KEY_COOLDOWN 都管不到 TLS 层重置).
  属 bug3/timeout 同类的"上游 NVCF 侧"分类. **若 R1880 再批量 (>=6) 且伴随 SR 续跌 →
  真正上游 NVCF 侧 TLS 层恶化信号, 届时需查 upstream / 联系运维, 非 nv_gw 调参能解**.
- pexec_empty_200 2 + pexec_timeout 2 (NVCF 侧偶发, 非新可配置分类).
- **无 ATE (all_tiers_exhausted 在 tier 表体现为 all_keys_exhausted 走 ms 兜底, 非 tier 自身 ATE 错误)
  无 429 无 pexec_timeout-as-primary-error** (主路径干净).

### fallback (cc4101 30min)
- fallback 计数 **5 条**, **全 PRIMARY-FAIL-SKIP-CIRCUIT** (bug3 75s header/ttfb 抢断 cc4101 preempt nv_gw retry,
  非 nv_gw 失败 NOT counted):
  - 10:41 req=3e3843b9 → FALLBACK-OK ms 6790ms (R1877/R1878 跨窗复现).
  - 10:49 req=d3ce9c44 → FALLBACK-OK ms 18009ms (R1878 跨窗复现, 18s 单点慢化尖峰).
  - 10:55 req=467a3608 → FALLBACK-OK ms 4432ms (**本窗新增**, <10s).
  - 10:58 req=043c5dd3 → FALLBACK-OK ms 11813ms (**本窗新增**, ~12s).
  - 11:02 req=d252cab7 → FALLBACK-OK ms 7357ms (**本窗新增**, <10s).
  - **11:06 req=ff907c36 → 双路全超时**: nv_gw 75s timeout (PRIMARY-FAIL-SKIP-CIRCUIT) +
    ms_gw 60s 也 timeout (FALLBACK-FAIL) → CC outer retry 兜住. **1 次"体验中断"信号** (nv+ms 都卡在 60-75s 区间).
    但这是 **1 条** < 4 阈值. 非 nv_gw 失败类 (SKIP-CIRCUIT), 非 nv_gw 可修.
- **非跳过类真请求失败 0 条** < 4 阈值. **0 真中断** (ff907c36 被 CC outer retry 兜住, 用户无感).
- fallback ms 延迟趋势: R1878 关切的 10:49 req=d3ce9c44 18009ms 18s 慢化尖峰本窗未续恶化,
  本窗新增 3 条 (10:55/10:58/11:02) 均在 4-12s 区间, 仍是单点尖峰非趋势,
  fallback 负载/健康无持续恶化, ms_gw 热备兜住 0 真中断.

### bug8
- 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 60min log + 120min DB 双确认 = 0).
  兜底在位 args 全合法不需触发, 符合 R1839 原话"兜底保险就该几乎不触发".

### breaker (nv_gw 30min)
- **全 CLOSED 未 OPEN** 设计内:
  - 10:39:04 / 10:40:30 / 10:44:21 / 10:58:20 / 11:04:52 / 11:07:56 — 6× NV-MS-FB-ATTEMPT+
    NV-MS-FB-OK+NV-MS-FB-SERVED (nv chain all_keys_exhausted for glm5_2_nv, ms 兜底 served,
    breaker recorded failure state=CLOSED 无计数). req: f9eddf69 / 2efe9c93 / 05b4db97 / e6e07545 /
    e88c455c / 192dd11e.
    **重点**: all_keys_exhausted (全 key 耗尽走兜底) 本窗 6 次, **上半窗 (10:39-10:44) 3 次 + 下半窗
    (10:58-11:07) 3 次**, 下半窗密集化 = NVCF 上游 key 在本窗后半被频繁 ratelimit/耗尽.
  - **11:07:46 NV-ANTH-BREAKER-FAIL** (glm5_2_nv) anth mid-stream soft-fail
    err=stream_absolute_cap -> nv_breaker recorded (state=('CLOSED', **2**, 0), req=e88c455c) **本窗新增事件**.
  - **重点结论**: nv_breaker state 第二字段: R1873=2 → R1874/R1875/R1877/R1878=1 → 本轮 R1879 从 1 升回 2.
    state 在 1-3 之间漂移而非单调累积 (R1871 从 3 掉回 2, R1874 掉到 1, 本轮升回 2),
    远低于 OPEN 阈值, 设计内吸收态且具自恢复能力. **本窗出现新 NV-ANTH-BREAKER-FAIL 事件 (11:07:46)
    但 state 升到 2 而非续增到 3 → 即"出现事件"≠"恶化"**, state 在 1-2 区间漂移正常工作.

### env + 代码一致性
- env 无漂移 (KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 /
  TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 /
  MIN_OUTBOUND=0, 全与 R1850-R1878 一致).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
   container `/app/gateway/format/oai_to_anth.py`), bug8 四要素全在.
- nv_gw 真实 StartedAt = **2026-07-18T21:26:29Z** (= R1836 restart, R1839 至 R1878 未再 restart) → 跑 R1839 改后字节码.
- /health ok (passthrough, nv_num_keys=5, nvcf_pexec_models 含 glm5_2_nv).
- docker ps 全 Up (nv_gw Up 6h / cc4101 Up 19h / ms_gw Up 47h / logs_db Up 2d).

## 验证结果
- 链路稳态持续 (SR 88.9% 本窗单轮探底但仅 1 轮未达连续 3 轮介入线; 连破计数重启为 1) +
  bug8 0 触发 (DB+log 双确认) + breaker 全 CLOSED 未 OPEN (nv_breaker state 从 R1878 的 1 升回 2,
  仍在 1-3 漂移区间非续增触 OPEN; 出现新事件但 state 衰减/漂移而非单调累积, 出现事件≠恶化) +
  fallback 非跳过类 0 + 0 真中断 (ff907c36 被 CC outer retry 兜住) + 0 restart +
  tier pexec 无 ATE 无 429 无 pexec_timeout-as-primary-error (干净; SSLEOFError 6 条为 NVCF 侧 TLS 层非 config 可修) +
  /health ok + docker ps 全 Up + StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码. 连续 35 轮 NOP (R1842-R1879) 链路稳态.

## 决策理由
介入触发四条全不满足:
1. SR 连续 >=3 轮破 93%: 本轮 (R1879 88.9) 是第 1 轮破, 连破计数重启为 1, **未达连续 3 轮介入线**.
2. fallback 非跳过类 >=4 次/30min: 本窗 5 条全 SKIP-CIRCUIT (bug3 75s 抢断), 非跳过类真失败 0 < 4.
3. NV-ANTH-BREAKER-FAIL OPEN: 全 CLOSED 未 OPEN, state 升到 2 非 OPEN.
4. 新可配置错误分类: pexec_SSLEOFError 6 条为 NVCF 侧 TLS 层 (非 nv_gw config 可调旋钮),
   all_tiers_exhausted 2 为 tier 全 key 耗尽兜底 (NVCF 上游 key 侧问题), 502 分类全 NVCF 侧偶发外分支 —
   **均非 nv_gw 可调旋钮能解的新分类**.

→ NOP 硬改违反铁律 (改前必有数据 + 无据不改). 本轮记录两个新关注点供下轮重点盯.

## 新关注点 (留给 R1880 重点盯)
1. **pexec_SSLEOFError 批量化苗头**: R1877 首现 1 → R1878 1 → R1879 6 (连续 3 轮化中).
   若 R1880 再批量 (>=6) 且伴随 SR 续跌 → 真正上游 NVCF 侧 TLS 层恶化信号, 届时需查 upstream / 联系运维,
   非 nv_gw 调参能解 (SSLEOF 是 TLS 层, 改 UPSTREAM/TIER/KEY_COOLDOWN 都管不到).
2. **SR 单窗探底 88.9**: 第 1 轮破 93, 连破计数重启为 1. 续盯 R1880+ 是否续破累计 3 轮才达介入线.
3. **11:06 req=ff907c36 双路全超时** (nv 75s + ms 60s): 1 次"体验中断"信号 (CC outer retry 兜住),
   说明 11:06 那个时间点 nv+ms 都在 60-75s 区间卡住, 可能 NVCF 上游短时故障. 单点非趋势.
4. **all_keys_exhausted 下半窗密集**: 6 次 (上半 3 + 下半 3), NVCF 上游 key 后半窗被频繁 ratelimit/耗尽.
   若续密集 → 查 upstream key 健康, 非 nv_gw 调参.

## 介入触发条件 (任一满足才动手, 否则继续 NOP 巡检)
1. SR 连续 >=3 轮跌破 93% (系统退化信号, 非抖动; 抖动被打断后重启连破计数). **当前连破计数=1**.
2. fallback 中非跳过类 (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min.
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 中第一字段变 OPEN, 超过 zombie 软挂).
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap). 注: SSLEOFError 属 NVCF 侧 TLS 层非 config 可修.

若以上都不满足, 继续 NOP 巡检轮, 维持 bug8 兜底在位观测.

## commit
本轮 R1879 单文件 commit (R1879_hm2_cc2_inspect.md). 注: 本 session git pull 之后未见 peer 新推 HM2→HM1 轮,
若 commit 时 peer 又推了被 `git add -A` 带上, 如实记录.
