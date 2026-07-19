# R1860 (HM2 cc2) — 巡检轮 bug8 降级兜底 in-vivo 后第 18 轮持续 0 触发 链路稳 SR96.2% 进一步上扬抖动区间常态

## 改前数据 (30min 窗, 2026-07-19 07:55-08:25 CST 本 session 拉取)
- **SR 30min = 100/104 = 96.2%** (200:100 / 502:4)。**>=93%, 抖动区间常态确认, 本轮进一步上扬**。
  近 8 轮标定: R1853 94.8% / R1854 94.7% / R1855 94.6% / R1856 92.6% / R1857 90.2% / R1858 94.7% / R1859 95.2% / R1860 本轮 96.2%。
  R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断, R1859 95.2 + R1860 96.2 连续上扬, **未达连续 >=3 轮破 93 触发线**, 抖动区间常态, 无系统退化信号。
- **5XX 归因 (502:4)** = 3 zombie_empty_completion + 1 stream_absolute_cap, **全 NVCF 侧偶发外分支 config 不可修** (与 R1851-R1859 同构)。
- **tier pexec (30min)**: success 80 / SSLEOF 2 / empty_200 2 / NVCFPexecTimeout 1 / 429 1 / timeout 1. **无 zombie 无 ATE**。
- **fallback (30min)**: 1 条 (07:59 req=063ad0de) PRIMARY-FAIL-SKIP-CIRCUIT (bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted)
  → 后 FALLBACK-OK ms 成功 (2912ms 递进合法)。**非跳过类真请求失败 0 条**, < 4 阈值。**0 中断**。
  注: R1859 交接棒记 07:52+07:59 两条, 本轮 30min 窗只看到 07:59 一条 (07:52 已滚出 30min 窗), 正常。
- **bug8 关键**: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗 = 0)。兜底在位 args 全合法不需触发, 符合 R1839 原话"兜底保险就该几乎不触发"。
- **breaker (30min)**: 4 条 NV-ANTH-BREAKER-FAIL 全 CLOSED (1,0)/(2,0)/(2,0)/(1,0), zombie 软挂未 OPEN
  + 1 NV-ANTH-ABS-CAP (cap_elapsed=221s 超 150s, 与 R1857/R1858/R1859 一致, 比 R1852-R1856 的 159s 变长, 单请求墙钟逃逸) 未 OPEN, 设计内。
  注: abs_cap 221s 是 NVCF 侧墙钟逃逸, STREAM_ABS_CAP 150s 是检测线, 调高 = 死循环请回复, 违反 CLAUDE.md 不动。
- **env 无漂移** (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1, 全与 R1850-R1859 一致)。
- **oai_to_anth.py**: md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致 (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py` vs container `/app/gateway/format/oai_to_anth.py`), bug8 四要素全在。
- **StartedAt**: 2026-07-18T21:26:29Z (R1839 改后字节码, 至 R1860 未再 restart)。
- **/health**: `{"status":"ok","proxy_role":"passthrough","nv_num_keys":5,...}` ok。**docker ps**: nv_gw Up 3h / cc4101 Up 16h / ms_gw Up 44h。

## 决策: NOP (不改)
介入触发四条全不满足:
1. SR 连续 >=3 轮破 93: 否 (R1858+R1859+R1860 连续 3 轮 >=94.7, 抖动早已上扬反弹).
2. fallback 非跳过类 >=4 次/30min: 否 (0 < 4).
3. NV-ANTH-BREAKER-FAIL OPEN: 否 (全 CLOSED, zombie 软挂未超过).
4. 新可配置错误分类: 否 (502 全 NVCF 侧 zombie/abs_cap, config 不可修).
→ 硬改违反铁律 (改前必有数据 + 无据不改). 本轮继续巡检, bug8 兜底在位观测。

## 改动: 无
NOP. 无 compose env / 无 .py 改动. 0 restart. 0 中断.

## 验证结果
链路稳: SR 96.2% (近 3 轮 94.7/95.2/96.2 连续上扬) + bug8 0 触发 + breaker 全 CLOSED + fallback 非跳过类 0 + 0 中断 + 0 restart。StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码。/health ok。

## 下一轮 (R1861) 该做什么
继续常规巡检。**重点**优先看 SR:
- 若 R1861 SR >=93% → 抖动区间常态确认, 继续 NOP 巡检。
- 若 R1861 SR <93% → 新一轮破 93 只算 1 轮, 不能与旧 2 轮 (R1856 92.6 / R1857 90.2) 直接拼成 3 轮 — 抖动被打断后重启连破计数。需在此后连续 3 轮破 93 才达触发线需介入排查 (介入仍需先定位可配置旋钮, 若 502 仍全 NVCF 侧 config 不可修则无法硬改, 仅记录归因)。

**介入触发条件** (任一满足才动手, 否则继续 NOP 巡检):
1. SR 连续 >=3 轮跌破 93% (系统退化信号, 非抖动; 抖动被打断后重启连破计数)。
2. fallback 中**非跳过类** (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min。
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 第一字段变 OPEN, 超过 zombie 软挂)。
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap)。
若都不满足, 继续 NOP 巡检轮, 维持 bug8 兜底在位观测。
注: 连续 18 轮 NOP (R1842-R1860) 链路稳态。SR 近 3 轮上扬 (94.7→95.2→96.2), 无退化数据, 不主动改。
