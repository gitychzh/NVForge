# R1870 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第26轮持续0触发 链路稳 SR94.6% nv_breaker state 停留3未续增

> 模式: nv 直连 (cc4101→nv_gw)。R1839 bug8 真降级兜底 in-vivo 生效后连续巡检 NOP。
> 本轮 NOP (0 改动, 0 restart)，介入触发四条全不满足。

## 改前数据 (30min 窗, 本 session 09:30 CST 拉取)

### nv_gw 成功率
- SR 70/74 = **94.6%** (200:70 / 502:4)。远高于 93% 阈值。
- 连续 10 轮在 93 上: R1860 96.2 / R1861 98.0 / R1862 99.0 / R1863 97.6
  / R1864 98.6 / R1865 94.3 / R1867 93.5 / R1868 93.8 / R1870 94.6
  (注 R1866 为 peer 改 HM1 轮, R1869 为 peer HM2→HM1 NOP 轮, 不计 HM2 SR 抖动序列)。
- R1856+R1857 连 2 轮破 93 早被 R1858 94.7 反弹打断, 连破计数仍 0。
- 本轮较 R1868 93.8 小幅回升 (属抖动区间, 非退化)。**无系统退化信号**。

### 502 分类
- zombie_empty_completion 3 + stream_first_byte_timeout 1。
- 注: stream_first_byte_timeout 属 NVCF 侧 timeout 偶发**已知分类** (非全新可配置分类,
  历史轮曾多次出现), 4 条 502 **全 NVCF 侧偶发外分支 config 不可修**,
  与 R1851-R1868 同构。本轮无 abs_cap。**非新可配置错误分类**。

### tier pexec
- pexec_success 54, **无 ATE 无 SSLEOF 无 429 无 pexec_timeout** (干净)。
- pexec_empty_200 2 (NVCF 侧偶发, 合法范围内)。

### fallback (负向核心指标)
- 4 条 PRIMARY-FAIL-SKIP-CIRCUIT (bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted):
  - 09:10 req=c9a8bb9f → FALLBACK-OK ms 5380ms
  - 09:12 req=2a4164b0 → FALLBACK-OK ms 1960ms
  - 09:19 req=b31ffce1 → FALLBACK-OK ms 3399ms
  - 09:26 req=8ea3dfb7 → FALLBACK-OK ms 3611ms (本窗新增)
- **非跳过类真请求失败 0 条**, < 4 阈值。**0 中断**。

### bug8 (核心观测)
- 实战降级触发 **0** (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空, DB 0 + nv_gw log 0 双确认)。
- 兜底在位 args 全合法不需触发, 符合 R1839 round 文件原话"兜底保险就该几乎不触发"。

### breaker 30min (全 CLOSED 未 OPEN, 设计内)
- 09:03 1 NV-ANTH-BREAKER-FAIL zombie_empty_completion (req=b14f6431) state=('CLOSED', 3, 0) — 延续 R1865 同 req。
- 09:02 / 09:12 / 09:15 / 09:22 / 09:29 5× NV-MS-FB-SERVED (ms 兜底 served, nv breaker recorded failure state=CLOSED 无计数)。
  注: 09:02 req=ab165ea7 / 09:12 req=cf0e880d / 09:15 req=8faab390 / 09:22 req=a0ad8435 / 09:29 req=1c6a93bc。
- **重点结论**: nv_breaker state 第二字段自 R1865 (09:03 req=b14f6431) 起停在 3,
  本轮 R1870 (09:03 同 req) **仍 3, 未续增 (无 3→4 递进)**。
  延续 R1868 "否决 R1867 OPEN 顾虑" 答案: 未续增 = 未恶化, 设计内吸收态
  (fallback 路径取走 ms 兜底但不累加 mid-stream soft-fail 计数)。仍远低于 OPEN 阈值。

### 环境一致性
- env 无漂移 (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1,
  全与 R1850-R1868 一致)。
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
   container `/app/gateway/format/oai_to_anth.py`)。bug8 四要素全在。
- StartedAt 仍 2026-07-18T21:26:29Z (= R1836 restart, R1839 至 R1870 未再 restart) → 跑 R1839 改后字节码。
- /health ok, docker ps 全 Up。

## 验证结果
链路稳 (SR 94.6% > 93 抖动区间, 连续 10 轮在 93 上, 较 R1868 93.8 小幅回升属抖动无系统退化) +
bug8 0 触发 (DB+log 双确认) + breaker 全 CLOSED 未 OPEN (nv_breaker state 停 3 未续增, 延续否决答案) +
fallback 非跳过类 0 + 0 中断 + 0 restart + tier pexec 无 ATE 无 SSLEOF 无 429 timeout + /health ok。
连续 26 轮 NOP (R1842-R1870) 链路稳态。

## 决策理由 (为何 NOP)
介入触发四条全不满足:
1. SR 94.6% > 93, 连续 10 轮在 93 上, 连破计数 0 → 未达连续 >=3 轮破 93 触发线。
2. fallback 非跳过类 0 < 4 阈值。
3. NV-ANTH-BREAKER-FAIL 全 CLOSED 未 OPEN, state 未续增 (停 3)。
4. 无新可配置错误分类 (4 条 502 全 NVCF 侧 zombie/timeout 偶发外分支 config 不可修)。
→ 硬改违反铁律 (改前必有数据 + 无据不改)。NOP。

## 下轮建议 (R1871)
继续常规巡检。**重点**:
- **nv_breaker state**: 本轮停 3 未续增延续稳态。续盯 state 第二字段是否仍停留/续增/触 OPEN。
  (R1839 breaker 设计本就是"宁可 OPEN 走 ms 也不死循环", OPEN 本身是兜底动作非源码 bug;
  真正该看的是 OPEN 是否**频繁复现** → 那才是 nv_gw 软挂恶化信号, 需查 upstream/key 软挂源。)
- **SR**: 若 R1871 SR <93 → 只算 1 轮新破, 不能与旧 2 轮 (R1856 92.6 + R1857 90.2) 拼成 3 触发线
  (R1858 94.7 已打断旧连破), 需重新累积连续 3 轮破 93 才达介入线。

**介入触发条件** (任一满足才动手, 否则继续 NOP 巡检):
1. SR 连续 >=3 轮跌破 93% (系统退化信号, 非抖动; 抖动被打断后重启连破计数)。
2. fallback 中**非跳过类** (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min。
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 中第一字段变 OPEN, 超过 zombie 软挂)。
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap)。

## 改动
NOP — 无 compose env / 无 .py 改动 / 0 restart / 0 中断。
注: 本 session git pull 已含 peer R1869 (commit abcb0ec, HM2→HM1 NOP 轮, 只新增 rounds/R1869_hm2_optimize_hm1.md + 改 RN_hm2_optimize_hm1.md 一行, 0 改 HM2 nv_gw 源码/配置, 符合铁律对 HM2 0 影响)。本次 R1870 commit 单文件无 peer 误收。
