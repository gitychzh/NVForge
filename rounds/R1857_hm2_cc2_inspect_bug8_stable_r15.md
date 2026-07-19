# R1857 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第15轮持续0触发 链路抖动SR90.2%连续2轮破93未达3轮触发线

## 模式
nv 直连 (cc4101→nv_gw), R1839 bug8 真降级兜底已落地 in-vivo (commit ddc8bd6)。
连续 15 轮巡检 (R1842-R1857) bug8 实战降级 0 触发, 兜底保险在位但 args 全合法不需触发
(符合 R1839 round 原话"兜底保险就该几乎不触发")。

## 改前数据 (30min 窗, 本 session 拉取)
- **SR 83/92 = 90.2%** (200:83 / 502:9). **连续 2 轮破 93% 但未达连续 >=3 轮触发线**:
  近 5 轮 R1853 94.8% / R1854 94.7% / R1855 94.6% / R1856 92.6% / R1857 本轮 90.2%,
  **SR 4 轮连续下滑 94.7→90.2, 已连 2 轮破 93, 预警升级** (STATE 明确警告 R1858 若仍<93 达连续 3 轮触发线需介入排查).
- **9 条 502 错误分类** (全 NVCF 侧偶发外分支, config 不可修, 与 R1851-R1856 同构):
  - zombie_empty_completion: 5 (NVCF 侧空 completion)
  - stream_first_byte_timeout: 2 (NVCF 侧 TTFB 超时)
  - all_tiers_exhausted: 1 (全 tier 耗尽)
  - stream_absolute_cap: 1 (NVCF 侧墙钟超 150s)
- **tier pexec** (30min): success 75 / 429 7 / SSLEOF 4 / empty_200 2 / NVCFPexecTimeout 1 / timeout 1.
  无 zombie 无 ATE (all_tiers_exhausted).
- **fallback** (30min): 2 条 PRIMARY-FAIL-SKIP-CIRCUIT
  (07:52 req=0ded572c + 07:59 req=063ad0de, 均 bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted)
  → 后 FALLBACK-OK ms 成功 (递进合法, 3842ms / 2912ms). **非跳过类真请求失败 0 条** <4 阈值. **0 中断**.
- **bug8 关键**: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空). 兜底在位 args 全合法不需触发.
- **breaker** (30min): 6 条 NV-ANTH-BREAKER-FAIL **全 CLOSED** (state 全 (1,0)/(2,0)/(1,0),
  zombie 软挂累积未达 OPEN 阈值) + 1 NV-ANTH-ABS-CAP
  (cap_elapsed=**221s** 超 150s, 比 R1852-R1856 的 159s 明显变长, 单请求墙钟逃逸)
  未 OPEN, 设计内.

## 状态核对 (无漂移)
- /health ok (nv_num_keys=5, models kimi/dsv4p/glm5_2, default dsv4p_nv)
- env 无漂移: UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1
  (与 R1850-R1856 快照全一致)
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host /opt/cc-infra/proxy/nv-gw/gateway/format vs container /app/gateway/format),
  bug8 四要素 (_detect_bad_tool_args + _downgrade_to_end_turn flag + 两处 final_stop) 全在.
- StartedAt = 2026-07-18T21:26:29Z (R1836 restart, R1839 至 R1857 未再 restart) → 跑 R1839 改后字节码.
- 容器全 Up: nv_gw Up 3h / cc4101 Up 16h / ms_gw Up 44h / logs_db Up 2d.

## 改了什么
**NOP (不改)**. 无 compose env / 无 .py 改动. 0 restart.

## 决策理由 (介入触发四条全不满足)
1. **SR 连续 >=3 轮跌破 93%**: 当前只 **2 轮** (R1856 92.6% + R1857 90.2%), 未达 3 轮触发线.
   R1858 若仍 <93 将达连续 3 轮, 届时需介入排查 (但仍需先定位可配置旋钮).
2. **fallback 非跳过类 (FALLBACK-OK 真 nv_gw 失败) >=4 次/30min**: **0 条** (2 条全 SKIP-CIRCUIT bug3 抢断), 不满足.
3. **NV-ANTH-BREAKER-FAIL 出现 OPEN**: 6 条全 **CLOSED**, 不满足.
4. **新可配置错误分类**: 9 条 502 全 NVCF 侧 (zombie/first_byte/all_tiers/abs_cap) config 不可修, 不满足.

硬改违反铁律 (改前必有数据 + 无据不改). abs_cap cap_elapsed 221s vs 159s 变长是 NVCF 侧单请求墙钟,
STREAM_ABS_CAP 150s 是检测线非延长点 — 调高=让死循环请回来 (违反 CLAUDE.md 明确警告), 不动.

## 验证结果
0 restart 0 中断. 链路稳态 (bug8 0 触发 + breaker 全 CLOSED + fallback 非跳过类 0 + env 无漂移 + 字节码一致).
唯一变化: SR 连续 2 轮破 93 (94.7→94.6→92.6→90.2) 进入预警区间, 但 502 全 NVCF 侧偶发非系统退化信号.

## 下一轮 (R1858) 重点
**SR 走向是核心**:
- 若 R1858 SR >=93% → 本次 90.2 确认为抖动, 解除预警, 继续 NOP 巡检.
- 若 R1858 SR <93% → **连续 3 轮破 93 达触发线**, 需介入排查:
  1. 先定位 502 是否仍全 NVCF 侧 config 不可修 (zombie/first_byte/all_tiers/abs_cap).
  2. 若仍全 NVCF 侧 → 无可调旋钮, 仅可记录归因 (不可硬改).
  3. 若出现新可配置分类 (非 NVCF 侧) → 按 CLAUDE.md 可调旋钮表逐个对照定位.
  4. 重点复盘 abs_cap: cap_elapsed 159s→221s 趋势, 若持续变长且 NVCF 侧系统性而非偶发, 再评估.
