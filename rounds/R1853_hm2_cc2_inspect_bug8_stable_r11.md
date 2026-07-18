# R1853 (HM2 cc2) — 巡检轮 bug8 降级兜底 in-vivo 后第11轮持续0触发 链路稳SR94.8%

## 模式
nv 直连 (cc4101→nv_gw 40006)。R1839 bug8 真降级兜底已落地 in-vivo 生效。
本轮 = R1842 起��续第 11 轮 NOP 巡检确认。0 改动 / 0 restart / 0 中断。

## 改前数据 (30min 窗, 拉取于本 session 开头)
- **SR 109/115 = 94.8%** (200:109 / 502:6). 抖动区间下沿, 非系统退化:
  近 4 轮 R1850 94.8 / R1851 95.6 / R1852 96.1 / 本轮 94.8 持续在 94-98% 区间,
  未连 ≥3 轮破 93% (介入条件1 不满足).
- 6 条 502 = 2 stream_first_byte_timeout + 2 zombie_empty_completion +
  1 all_tiers_exhausted + 1 stream_absolute_cap.
  **全 NVCF 侧偶发降级路径外分支 config 不可修** (与 R1851/R1852 同构).
- tier pexec: pexec_success 77 / pexec_429 6 / pexec_empty_200 2 / pexec_timeout 1.
  无 zombie 无 ATE. 429 6 比 R1852 的 4 略多但仍低频正常抖动.
- fallback: cc4101 30min 共 8 行 = **2 条真请求** (07:14:29 / 07:25:03),
  全 PRIMARY-FAIL-SKIP-CIRCUIT (75s bug3 抢断, cc4101 preempt nv_gw retry,
  <chain budget 120s, 非 nv_gw 失败, NOT counted toward circuit).
  非跳过类 (FALLBACK-OK 真正 nv_gw 失败) = 0, 未达 ≥4 阈值 (介入条件2 不满足).
  2 条 fallback 均 FALLBACK-OK 成功, **0 中断**.
- bug8 关键: 实战降级触发 **0** (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空).
  兜底在位但 args 全合法不需触发, 符合 R1839 原话"兜底保险就该几乎不触发".
- breaker (30min): NV-ANTH-ABS-CAP 1 (cap_elapsed=159s 超 150s, req=b8468c4a)
  + NV-ANTH-BREAKER-FAIL 3 (1 stream_absolute_cap state=(CLOSED,1,0) /
  2 zombie_empty_completion state=(CLOSED,1,0)/(CLOSED,2,0)).
  **全 CLOSED 未 OPEN** (介入条件3 不满足), 设计内 mid-stream 软挂.
- cc2.log could-not-be-parsed 30min = 0.

## 验证项
- /health: `{"status":"ok","proxy_role":"passthrough","nv_num_keys":5,...}` ok.
- env 无漂移: UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 /
  NVU_BIG_INPUT_FAIL_N=1 / MIN_OUTBOUND=0, 全与 R1850-R1852 一致.
- oai_to_anth.py md5 = **4983bcec1d1203a1f3f8acf371786c6c** (550 行)
  宿主 (/opt/cc-infra/proxy/nv-gw/gateway/format/) 与容器 (/app/gateway/format/) 一致.
  bug8 四要素在位: _detect_bad_tool_args() + _downgrade_to_end_turn flag
  + 两处 final_stop 强制 end_turn.
- StartedAt = 2026-07-18T21:26:29Z (R1836 restart, R1839 至 R1853 未再 restart)
  → 跑 R1839 改后字节码持续确认.
- docker ps nv_gw up, 无重启.

## 决策理由
链路稳 (SR 94.8% 抖动区间下沿非退化) + 6 条 502 全 NVCF 侧 config 不可修 +
bug8 0 触发 + breaker CLOSED + 0 中断 + 0 restart.
介入触发四条件 (SR 连破93 / fallback 非跳过类≥4 / breaker OPEN / 新错误分类)
**全不满足** → NOP 硬改违反铁律 (改前必有数据 = 无可改依据).

## 结论
连续 11 轮 NOP (R1842-R1853) bug8 兜底在位实战 0 触发, 链路稳态.
维持常规巡检节奏. 下一轮继续观测, 任一介入触发条件满足才动手.
