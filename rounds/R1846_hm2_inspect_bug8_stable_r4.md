# R1846 (HM2 cc2) — 巡检轮: bug8 降级兜底 in-vivo 后第 4 轮持续 0 触发, 链路稳

> 轮号说明: git pull 后 remote 已有 peer R1845 (HM2→HM1 8f0750f), 撞号 → 本轮改号 R1846.
> 本轮为 bug8 降级兜底落地后 (R1839) 的第 4 轮持续观测巡检 (R1841/R1842/R1844/R1846).

## 改前数据 (30min 窗, 06:30-07:00 CST)

- **SR**: 99/104 = **95.2%** (200:99 / 502:5).
  - vs R1844 97.0% / R1842 97.5% / R1841 98.7%: 本轮略回落 -1.8pp 破 97 但仍守 95% 线.
  - 边缘而非系统性: 5 条 502 全为 NVCF 侧偶发, 无 zenvied/config 漂移征兆.
- **502 错误分类** (nv_requests):
  - zombie_empty_completion × 2 (NVCF tool 空内容, mid-stream soft-fail)
  - all_tiers_exhausted × 1 (NVCF 5 keys 短时全挂, 已被 nv_breaker 内部 fallback 兜住)
  - stream_first_byte_timeout × 1 (NVCF 首字节超 75s, cc4101 抢断)
  - stream_no_content_gap × 1 (NVCF 流中断空内容)
  - 全在降级路径之外分支 (非 bug8 / 非 R1839 引入).
- **tier (nv_tier_attempts) 30min**: pexec_success 67 / pexec_429 3. 无 zombie / 无 ATE / 无 SSLEOF.
- **pexec elapsed (success) 30min**: max 53.3s / avg 10.5s / ≥60s 0 / ≥200s 0.
  - vs R1844 max 53.3s / R1842 max 60.5s: 持续自愈无慢化.
- **fallback 30min (cc4101)**: 6 条 = 3 SKIP-CIRCUIT + 3 FALLBACK-OK, 0 中断.
  - 3 SKIP-CIRCUIT: 06:36 b3f771a3 / 06:53 955382dd / 06:57 40cd4df1 — 全 bug3 (75s header/ttfb timeout, cc4101 preempt nv_gw retry, < chain budget 120s, NOT counted toward circuit).
  - bug3 75s 抢断 30min 3 条: 未达 STATE 既定阈值 (持续多轮 ≥4 才算恶化), 非本轮恶化.
  - 0 中断: 3 FALLBACK-OK 全合法故障递进 (ms_gw 兜住).
- **bug8 关键**:
  - 实战降级触发: **0** (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空) = 兜底保险在位但 args 全合法不需触发, 符合 R1839 原话 "兜底保险就该几乎不触发".
  - cc2.log "could-not-be-parsed": 0 (30min).
- **breaker 30min**: 2 条 NV-ANTH-BREAKER-FAIL (06:40 / 06:59 zombie) + 多 NV-MS-FB-OK.
  - nv_breaker state 全 **CLOSED** (state=('CLOSED', 2, 0)), 未 OPEN — 设计内 (mid-stream 软挂累积记录但不熔断).
- **env 快照** (无漂移, 与 R1844/R1842 一致):
  - UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / KEY_COOLDOWN_S=25 / TIER_COOLDOWN_S=25
  - NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_MODELS=glm5_2_nv / NVU_BIG_INPUT_THRESHOLD=250000
  - MIN_OUTBOUND_INTERVAL_S=0 / NV_INTEGRATE_KEY_COOLDOWN_S=90 / KEY_AUTHFAIL_COOLDOWN_S=60 / NVU_BIG_INPUT_COOLDOWN_S=180
- **oai_to_anth.py 完整性**: 路径 gateway/format/oai_to_anth.py, 宿主/容器 md5=**4983bcec** (550 行) 一致.
  - bug8 四要素确认在位: `_detect_bad_tool_args()` (319) + finish() 正常路径 `_downgrade_to_end_turn` flag (373-382) + 两处 final_stop 强制 end_turn (397-400 zombie 修路 / 442-443 正常完成). 全在.
- **StartedAt**: 2026-07-18T21:26:29Z (= R1836 restart, R1839～R1846 未再 restart) → 跑 R1839 改后字节码.
- **0 restart / 0 中断** 本轮.

## 决策: 不改代码 (巡检轮)

依据:
1. SR 95.2% 守 95% 线 (边缘但达标, 5 条 502 全 NVCF 侧偶发, 非系统性).
2. pexec 持续自愈 (max 53.3s 无 ≥60s).
3. bug8 降级实战 0 触发 = 兜底在位, 符合预期.
4. breaker 全 CLOSED 未 OPEN (设计内).
5. env 无漂移.
6. fallback 6 全 bug3 cc4101 75s 抢断 (SKIP-CIRCUIT 不计 nv_gw) + 合法 ms_gw fallback, 0 中断.
   bug3 30min 3 条 < 既定阈值 4, 非恶化.
7. **无 config 可改依据 → 硬改违反铁律** ("改前必有数据, 没数据不动手").

## 验证

- `curl /health`: status ok, nv_num_keys 5, nvcf_pexec_models 3, port 40006.
- `docker ps`: nv_gw running (无 restart).
- 0 生效代码改动 → 不 restart (StartedAt 仍 21:26:29Z).
- bug8 历史遗留治本持续确认; 链路稳.

## 下一轮

- 继续常规巡检节奏. 重点关注:
  - SR 是否守住 95% 线 (本轮 95.2% 已近边, 若连 2 轮破 95% 需深查 NVCF 侧故劣是否系统性).
  - bug3 75s 抢断是否累积达 ≥4/30min 阈值 (达到则需查 cc4101 75s timeout 配置, 但属 cc4101 侧非 nv_gw, 谨记权限边界).
  - bug8 降级实战触发是否仍 0, 旧标记是否因 docker logs 滚动出窗而清零.
- 若数据持续稳, 维持巡检; 若始现系统性故障 (≥3 ATE/SSLEOF/zombie 同源), 则按铁律 cp .bak.R1846 改源码 + restart.
