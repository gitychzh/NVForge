# R1880 (HM2 cc2) — 巡检轮 bug8 降级兜底 in-vivo 后第36轮持续0触发

## 链路稳态持续确认,但警示升级: SR 连续 2 轮破 93 (连破计数=2 接近介入线) + pexec_SSLEOFError 6 持平连续 2 轮 + nv_breaker state 升到 3 (R1873 以来首次回到 3)

**改了什么**: NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 改前数据 (30min 窗, 本 session ~11:19 CST 拉取)

### SR
- SR **39/45 = 86.7%** (200:39 / 502:6). **本窗连续第 2 轮破 93%, 连破计数=2** (R1879 88.9 + R1880 86.7).
- 抖动区间此前连续 >93 序列: R1875 96.7 / R1877 93.65 / R1878 94.2, 全 >93.
- R1879 88.9 是第 1 轮破 93, R1880 86.7 是第 2 轮破 93 → **连破计数累计=2**.
  **需 R1881 再破 93 (连破计数达 3) 才触发介入线**. 当前=2, 接近但未达.
  注意: 旧 2 轮 R1856 92.6 + R1857 90.2 早被 R1858 94.7 反弹打断, 不能拼入当前连破序列.
  本轮较 R1879 88.9 续跌 2.2pp, 较 R1878 94.2 已探底 7.5pp, 是 R1842 NOP 巡检以来最深的连续 2 轮低位.
- 502 分类 (status=502, 共 6 条):
  - zombie_empty_completion 3 (NVCF 侧 zombie 偶发, 已知分类 config 不可修, R1851+ 间歇).
  - all_tiers_exhausted 1 (tier 全 key 耗尽兜底, 与本窗 all_keys_exhausted 增多同源).
  - stream_absolute_cap 1 (NVCF 侧 abs_cap, 已知分类 config 不可修).
  - **stream_no_content_gap 1** (NVCF 侧 content gap, 已知分类 config 不可修; R1879 无此分类, 本窗新增 1 条).
  - **全 NVCF 侧偶发外分支 + tier 耗尽兜底, 非新可配置错误分类**, 与 R1875-R1879 同构 (本窗无 stream_first_byte_timeout).

### tier pexec (30min)
- pexec_success 31 (干净基底, 较 R1879 36 略降 5, 与本窗 req 总量下降一致).
- **pexec_SSLEOFError 6** (**连续 2 轮维持批量 6 条**): R1877 首现 1 → R1878 1 (连续 2 轮单点) → R1879 6 → R1880 6.
  连续 4 轮观察序列: 1 → 1 → 6 → 6. **SSLEOFError 已稳定在批量 6 而非回落**, 即 R1879 STATE 预警的
  "上游 NVCF 侧 TLS 层恶化苗头"正在**兑现为持续态而非单点尖峰**. 但 SSLEOFError 本身是 NVCF 侧 TLS / 上游连接层
  (SSL EOF = TLS 连接被上游异常关闭), **不是 nv_gw config 可调旋钮**
  (改 UPSTREAM_TIMEOUT / TIER_TIMEOUT_BUDGET / KEY_COOLDOWN 都管不到 TLS 层重置).
  属 bug3/timeout 同类的"上游 NVCF 侧"分类. **若 R1881 续维持批量 (>=6) 且 SR 续破 93 (连破计数达 3) →
  达介入线, 但届时真正的处置是查 upstream / 联系运维, 非 nv_gw 调参能解**.
- pexec_empty_200 2 + pexec_timeout 2 (NVCF 侧偶发, 非新可配置分类).
- **无 ATE (all_tiers_exhausted 在 tier 表体现为 all_keys_exhausted 走 ms 兜底, 非 tier 自身 ATE 错误)
  无 429 无 pexec_timeout-as-primary-error** (主路径干净).

### fallback (cc4101 30min)
- fallback 计数 **6 条**, **全 PRIMARY-FAIL-SKIP-CIRCUIT** (bug3 75s header/ttfb 抢断 cc4101 preempt nv_gw retry,
  非 nv_gw 失败 NOT counted):
  - 10:55 req=467a3608 → FALLBACK-OK ms 4432ms (R1879 跨窗复现).
  - 10:58 req=043c5dd3 → FALLBACK-OK ms 11813ms (R1879 跨窗复现, ~12s).
  - 11:02 req=d252cab7 → FALLBACK-OK ms 7357ms (R1879 跨窗复现, <10s).
  - **11:06 req=ff907c36 → 双路全超时**: nv_gw 75s timeout (PRIMARY-FAIL-SKIP-CIRCUIT) +
    ms_gw 60s 也 timeout (FALLBACK-FAIL) → CC outer retry 兜住. **1 次"体验中断"信号**
    (R1879 跨窗复现, nv+ms 都卡在 60-75s 区间). 仍单点非趋势.
  - 11:11 req=fcadb789 → FALLBACK-OK ms 11236ms (**本窗新增**, ~11s).
  - 11:15 req=c74107fb → FALLBACK-OK ms 9117ms (**本窗新增**, ~9s).
- **非跳过类真请求失败 0 条**, < 4 阈值. **0 真中断** (ff907c36 被 CC outer retry 兜住, 用户无感).
- fallback ms 延迟趋势: R1879 关切的 11:11/11:15 新增 2 条均在 9-12s 区间, 仍是单点尖峰非趋势,
  fallback 负载/健康无持续恶化, ms_gw 热备兜住 0 真中断.

### bug8 (降级兜底)
- **实战降级触发 0** (NV-TOOLCALL-JSON-DOWNGRADE 60min log = 0).
  兜底在位 args 全合法不需触发, 符合 R1839 round 文件原话"兜底保险就该几乎不触发".

### breaker (nv_gw 30min)
- 5× NV-MS-FB-ATTEMPT+OK+SERVED (nv chain all_keys_exhausted for glm5_2_nv, ms 兜底 served,
  breaker recorded failure state=CLOSED 无计数):
  - 10:58:20 req=e6e07545 (ms 7632ms) — R1879 跨窗复现.
  - 11:04:52 req=e88c455c (ms 11176ms) — R1879 跨窗复现.
  - 11:07:56 req=192dd11e (ms 16923ms) — R1879 跨窗复现 (本窗窗内).
  - 11:14:14 req=27a737bf (ms 3419ms) — **本窗新增**.
  - 11:17:55 req=66525f8e (ms 3940ms) — **本窗新增**.
- 11:07:46 **NV-ANTH-BREAKER-FAIL** (glm5_2_nv) anth mid-stream soft-fail
  err=stream_absolute_cap -> nv_breaker recorded (state=('CLOSED', **2**, 0), req=e88c455c) — R1879 跨窗复现.
- **11:10:40 NV-ANTH-BREAKER-FAIL** (glm5_2_nv) anth mid-stream soft-fail
  err=stream_no_content_gap -> nv_breaker recorded (state=('CLOSED', **3**, 0), req=192dd11e) — **本窗新增事件**.
- **重点结论**: nv_breaker state 第二字段: R1873=2 → R1874/R1875/R1877/R1878=1 → R1879=2 → **本轮 R1880 升到 3**.
  **R1873 以来首次回到 3**, 本轮是首次单窗内连升 (R1879 窗内只到 2, 本轮到 3).
  state 在 1-3 之间漂移而非单调累积, 远低于 OPEN 阈值, 设计内吸收态. 但仍 CLOSED 未 OPEN
  (state[0]=CLOSED, state[2]=0 即 cooldown 未触发), 在 1-3 漂移区间上沿.
  **出现事件 (state 升到 3) ≠ 真恶化 (触 OPEN)**, 仍属设计内吸收态具有自恢复能力. 需续盯是否继续升到 OPEN
  或单窗内频繁 NV-ANTH-BREAKER-FAIL (那才是 nv_gw 软挂恶化信号).

### 环境与字节码一致性
- env 无漂移 (KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 /
  TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 /
  MIN_OUTBOUND=0, 全与 R1850-R1879 一致).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
  container `/app/gateway/format/oai_to_anth.py`). bug8 四要素全在.
- nv_gw 真实 StartedAt = **2026-07-18T21:26:29Z** (R1836 restart, R1839 至 R1880 未再 restart) → 跑改后字节码.
- /health ok: status=ok, nv_num_keys=5, nv_default_model=dsv4p_nv, port=40006.
- docker ps 全 Up: nv_gw Up 6h / cc4101 Up 19h / ms_gw Up 47h / logs_db Up 2d.

## 验证结果
链路稳态持续但**警示升级三连**:
1. **SR 连破计数 1→2** (R1879 88.9 + R1880 86.7 连续 2 轮破 93, 接近介入线需 3 轮).
2. **pexec_SSLEOFError 6→6 持平连续 2 轮** (R1879 6 → R1880 6, 未回落 = "TLS 恶化苗头"兑现为持续态).
3. **nv_breaker state 2→3** (R1873 以来首次回到 3, 仍 CLOSED 未 OPEN, 1-3 漂移区间上沿).
+ bug8 0 触发 (60min log 确认) + breaker 仍 CLOSED 未 OPEN + fallback 非跳过类 0 + 0 真中断 +
  tier pexec 无 ATE/429/pexec_timeout-as-primary-error (干净; SSLEOFError 6 条为 NVCF 侧 TLS 层非 config 可修) +
  /health ok + docker ps 全 Up + 0 restart. StartedAt 仍 21:26:29Z 跑 R1839 改后字节码. 连续 36 轮 NOP (R1842-R1880) 链路稳态.

## 决策理由
介入触发四条**全不满足** → NOP 硬改违反铁律 (改前必有数据 + 无据不改):
1. SR 连续 >=3 轮破 93% — **当前连破计数=2** (R1879+R1880), 未达 3. 接近但未达介入线.
2. fallback 非跳过类 >=4 — 0 条 (全 PRIMARY-FAIL-SKIP-CIRCUIT, cc4101 preempt 非 nv_gw 失败). 不满足.
3. NV-ANTH-BREAKER-FAIL 出现 OPEN — state=('CLOSED', 3, 0) **仍 CLOSED 未 OPEN**, state[1]=3 在 1-3 漂移区间上沿
   但未触 OPEN. 不满足. (但需高度警惕: 此为首次单窗内 state 升到 3.)
4. 新可配置错误分类 — 无. SSLEOFError (NVCF 侧 TLS 非可修) + all_tiers_exhausted (NVCF 上游 key 耗尽)
   + stream_no_content_gap (NVCF 侧 content gap, 已知分类) 全是 NVCF 上游侧信号非 nv_gw 调参能解.
→ **本轮 NOP 不改**. 硬改违反"改前必有数据 + 无据不改"铁律. 警示三连属"接近介入线"信号, 下轮 R1881 是关键判窗.

## 文案备注
本轮 R1880 commit 单文件 (本 round 文件), 无 peer 误收 (git pull 后 git log 最新仍 R1879 4d3239c + peer R1877/R1876 均只改 HM1).
[/thinking]
