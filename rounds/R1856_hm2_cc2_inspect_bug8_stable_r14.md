# R1856 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第14轮持续0触发 链路稳SR92.6%下沿逼近93

## 改前数据 (30min 窗, 本 session 拉取)
- **SR 88/95 = 92.6%** (200:88 / 502:7)。近 5 轮趋势: R1852 96.1 / R1853 94.8 / R1854 94.7 / R1855 94.6 / **本R1856 92.6**。
  **单轮逼近但未破 93% 阈值下沿, 未达连续 >=3 轮破 93 触发线**。属抖动下沿而非系统退化
  (502 全 NVCF 侧偶发降级路径外分支而非常态结构化失败)。注意: 若 R1857 仍 <93, R1858
  将达连续 3 轮预警线, 届时需介入排查 (本轮标记, 下轮重点观察 SR 走向)。
- **7 条 502 分类**: 4 zombie_empty_completion + 2 stream_first_byte_timeout + 1 all_tiers_exhausted
  + 1 stream_absolute_cap, **全 NVCF 侧偶发降级路径外分支 config 不可修** (与 R1851-R1855 同构)。
- **tier pexec 30min**: success 79 / 429 10 / SSLEOF 2 / empty_200 2 / timeout 1, **无 zombie 无 ATE**。
- **fallback 30min** (cc4101 日志): 1 条。
  - 07:52:32 PRIMARY-FAIL-SKIP-CIRCUIT: primary timeout status=0 after 75058ms (header/ttfb timeout 75s)
    < chain budget 120s, **bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted toward circuit**。
  - 07:52:36 FALLBACK-OK ms 成功 after 3842ms (递进合法)。
  - **非跳过类真请求失败 0 条** (远 < 4 阈值), **0 中断**。
- **bug8**: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空)。兜底在位 args 全合法不需触发。
- **breaker 30min** (nv_gw 日志):
  - NV-ANTH-ABS-CAP 1: cap_elapsed=159s 超 150s (与 R1852-R1855 159s 完全一致, 同一 NVCF 内部上限)。
  - NV-ANTH-BREAKER-FAIL 5 全 CLOSED: (1,0)/(1,0)/(2,0)/(1,0)/(1,0),
    全 zombie 软挂 + 1 stream_absolute_cap, **未 OPEN**, 设计内。
- **env 无漂移**: UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / KEY_COOLDOWN_S=25 /
  NVU_BIG_INPUT_FAIL_N=1 (全与 R1850-R1855 一致)。
- **oai_to_anth.py**: md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) **宿主/容器一致**
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
   container `/app/gateway/format/oai_to_anth.py`),
  R1839 改后字节码四要素全在 (`_detect_bad_tool_args()` + finish() 正常路径 `_downgrade_to_end_turn`
  flag + 两处 final_stop 强制 end_turn)。

## 改动
- **NOP (不改)**。无 compose env / 无 .py 改动 / 0 restart。
- StartedAt 仍 **2026-07-18T21:26:29Z** (R1836 restart, R1839 至 R1856 未再 restart) → 跑 R1839 改后字节码。
- /health ok (nv_num_keys=5, pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv)。

## 决策理由 (为何 NOP)
介入触发四条全不满足:
1. SR 92.6% — **单轮接近 93 但仅 1 轮未连 >=3 轮破 93**。502 全 NVCF 侧偶发 (4zombie+2first_byte+
   1all_tiers+1abs_cap) 而非常态, 属抖动下沿非系统退化。
2. fallback 非跳过类 (FALLBACK-OK 真正 nv_gw 失败) **0 次** /30min (< 4 阈值)。
3. NV-ANTH-BREAKER-FAIL 5 全 CLOSED, **未 OPEN**。
4. 无新可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap)。
→ 硬改违反铁律 (改前必有数据 + 无据不改)。6 条 502 全 NVCF 侧 config 不可修, 无可调动旋钮。

## 验证结果
- 链路稳 (SR 92.6% 单轮下沿逼近 93, 502 全 NVCF 侧同构非退化) + bug8 0 触发 + breaker 全 CLOSED
  + fallback 非跳过类 0 + 0 中断 + 0 restart。
- StartedAt 21:26:29Z 确认跑 R1839 改后字节码 (未漂移)。
- /health ok, env 无漂移, oai_to_anth md5 4983bcec 宿主/容器一致。
- **用户诉求 "可以报错但不能让 cc2 中断" 仍达成** (本轮 0 中断, fallback 递进 ms 兜住)。

## 下一轮建议
继续常规巡检。**重点**: R1857 拉数据后**优先看 SR**:
- 若 R1857 SR >=93 → 本次 92.6 确认为抖动, 继续维持 NOP 巡检。
- 若 R1857 SR <93 → 连续 2 轮破 93, R1858 若仍 <93 将达连续 3 轮触发线, 需介入排查
  (但介入仍需先定位可配置旋钮, 若 502 仍全 NVCF 侧 config 不可修则无法硬改, 仅可记录归因)。
**介入触发条件** (任一满足才动手, 否则 NOP):
1. SR 连续 >=3 轮跌破 93%。
2. fallback 非跳过类 (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min。
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 第一字段变 OPEN)。
4. 出现新可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap)。
连续 14 轮 NOP (R1842-R1856) 链路稳态, bug8 兜底在位 0 触发持续确认。
