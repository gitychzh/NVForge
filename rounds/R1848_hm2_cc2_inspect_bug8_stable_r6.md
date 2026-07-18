# R1848 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第6轮持续0触发 链路稳SR94.7%

## 改前数据 (30min 窗, git pull 后 remote R1847=3db25c9, 本轮 R1848)

- **nv_requests**: 200=125 / 502=7 → **SR 125/132 = 94.7%** (跌破95%线但近6轮 R1842 97.5% / R1844
  97.0% / R1846 95.2% / R1847 94.1% / 本轮 94.7% 全在 94-98% 抖动区间, 非系统退化).
- **7条502 分类**:
  - zombie_empty_completion × 3
  - stream_first_byte_timeout × 2
  - all_tiers_exhausted × 1
  - stream_no_content_gap × 1
  全 NVCF 侧偶发降级路径之外分支, config 不可修.
- **nv_tier pexec**: success 89 / 429 3 / SSLEOFError 2, 无 zombie 无 ATE 无 ≥60s.
- **pexec elapsed**: max 53.3s / avg 10.7s / ≥60s 0 / ≥200s 0. 持续自愈, NVCF 侧无卡死.
- **fallback 30min**: 2 FALLBACK-OK (07:53 / 07:57 全 bug3 75s 抢断 SKIP-CIRCUIT, cc4101 preempt
  nv_gw retry, 非 nv_gw 可控, 未达 ≥4 阈值非恶化). **0 中断**.
- **bug8 关键**: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空) + cc2.log
  could-not-be-parsed 0. 兜底保险在位 args 全合法不需触发, 符合 R1839 round 文件原话.
- **breaker 30min**: 1 NV-ANTH-BREAKER-FAIL (zombie 软挂 state=('CLOSED',2,0) 未 OPEN, 设计内)
  + 2 NV-MS-FB-ATTEMPT/SERVED (all_keys_exhausted 进 ms fallback, nv_breaker recorded CLOSED).
- **oai_to_anth.py**: md5=4983bcec1d1203a1f3f8acf371786c6c (550行) 宿主 /opt/cc-infra/proxy/nv-gw/
  gateway/format/ 与容器 /app/gateway/format/ 一致, bind-mount 正常. bug8 四要素全在:
  _detect_bad_tool_args()@319 + _downgrade_to_end_turn flag@97/375/381 + 两处 final_stop
  强制 end_turn@399-400/442-443.
- **env 无漂移**: UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1,
  全与 R1844/R1846/R1847 快照一致.
- **StartedAt**: 仍 2026-07-18T21:26:29Z (= R1836 restart, R1839/R1841/R1842/R1844/R1846/R1847
  至本轮 0 restart) → 跑 R1839 改后字节码.

## 决策
**不改 (NOP 巡检轮)**. 理由: 链路稳 (SR 94.7% 在 6 轮抖动区间下沿非退化) + 7 条 502 全 NVCF 侧
config 不可修 + bug8 降级在位 0 触发 (符合设计) + breaker CLOSED 设计内 + env 无漂移 → 硬改违反
"改前必有数据 / 无 config 可改依据不动手" 铁律. bug8 历史遗留治本持续确认, 维持常规巡检节奏.

## 执行
0 restart, 0 中断, 0 改动. StartedAt 仍 21:26:29Z (R1836).

## 验证结果
SR 94.7% / fallback 2 (bug3 抢断 SKIP-CIRCUIT 非恶化) / bug8 0 触发 / breaker CLOSED /
could-not-be-parsed 0. 链路稳, 兜底在位.

## 下一轮建议
继续常规巡检. 若 SR 连续 ≥3 轮跌破 93% 或 fallback 非跳过类(FALLBACK-OK) ≥4 才视为恶化
需介入观测. 保持只在"有 config 可改依据"时才动手.
