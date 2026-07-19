# R1858 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第16轮持续0触发 链路稳SR94.7%反弹打断连续破93

## 模式
nv 直连 (cc4101→nv_gw), R1839 bug8 真降级兜底已落地 in-vivo (commit ddc8bd6)。
连续 16 轮巡检 (R1842-R1858) bug8 实战降级 0 触发, 兜底保险在位但 args 全合法不需触发
(符合 R1839 round 原话"兜底保险就该几乎不触发")。

## 改前数据 (30min 窗, 本 session 拉取)
- **SR 90/95 = 94.7%** (200:90 / 502:5). **反弹打断连续破 93**:
  近 6 轮 R1853 94.8% / R1854 94.7% / R1855 94.6% / R1856 92.6% / R1857 90.2% / R1858 本轮 94.7%,
  R1856+R1857 连 2 轮破 93 但本轮反弹回 94.7, **未达连续 >=3 轮触发线**, 抖动区间常态。
- **5 条 502 错误分类** (全 NVCF 侧偶发外分支, config 不可修, 与 R1851-R1857 同构):
  - zombie_empty_completion: 3 (NVCF 侧空 completion)
  - all_tiers_exhausted: 1 (全 tier 耗尽)
  - stream_absolute_cap: 1 (NVCF 侧墙钟超 150s)
- **tier pexec** (30min): success 84 / 429 5 / SSLEOF 4 / empty_200 2 / NVCFPexecTimeout 1 / timeout 1.
  无 zombie 无 ATE (all_tiers_exhausted).
- **fallback** (30min): 2 条 PRIMARY-FAIL-SKIP-CIRCUIT
  (07:52 req=0ded572c + 07:59 req=063ad0de, 均 bug3 75s 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted)
  → 后 FALLBACK-OK ms 成功 (递进合法, 3842ms / 2912ms). **非跳过类真请求失败 0 条** <4 阈值. **0 中断**。
- **bug8 关键**: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空). 兜底在位 args 全合法不需触发.
- **breaker** (30min): 3 条 NV-ANTH-BREAKER-FAIL **全 CLOSED** (state 全 (1,0)/(1,0)/(2,0),
  zombie 软挂累积未达 OPEN 阈值) + 1 NV-ANTH-ABS-CAP
  (cap_elapsed=**221s** 超 150s, 与 R1857 一致, 比 R1852-R1856 的 159s 明显变长, 单请求墙钟逃逸)
  未 OPEN, 设计内。
  注: abs_cap cap_elapsed 221s 是 NVCF 侧墙钟 STREAM_ABS_CAP 150s 是检测线, 调高=死循环请回复违反 CLAUDE.md 不动。

## 状态核对 (无漂移)
- /health ok (nv_num_keys=5, models kimi/dsv4p/glm5_2, default dsv4p_nv)
- env 无漂移: UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1
  (全与 R1850-R1857 一致)
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
   container `/app/gateway/format/oai_to_anth.py`), bug8 四要素全在 (R1839 改后字节码)
- nv_gw 真实 StartedAt = 2026-07-18T21:26:29Z (R1836 restart, R1839 至 R1858 未再 restart) → 跑改后字节码
- docker ps: nv_gw Up 3h / cc4101 Up 16h / ms_gw Up 44h / logs_db Up 2d 全正常

## 介入触发条件核对 (四条全不满足 → NOP)
1. SR 连续 >=3 轮跌破 93%: **否** (R1856 92.6 + R1857 90.2 只连 2 轮, R1858 反弹 94.7 打断)
2. fallback 非跳过类 >=4 次/30min: **否** (非跳过类真失败 0 条, 2 条全 SKIP-CIRCUIT 不 counted)
3. NV-ANTH-BREAKER-FAIL OPEN: **否** (3 条全 CLOSED)
4. 新的可配置错误分类: **否** (5 条 502 全 NVCF 侧 zombie/all_tiers/abs_cap, 与历史同构)

## 改动
NOP (不改). 无 compose env / 无 .py 改动. 0 restart. 0 中断.

## 决策理由
介入触发四条全不满足 + 5 条 502 全 NVCF 侧 config 不可修
(zombie / all_tiers / abs_cap 均 NVCF 上游偶发, gateway 侧无旋钮可改)
→ 硬改违反铁律 (改前必有数据 + 无据不改). abs_cap 221s 逃逸调高破坏安全网不动.
维持 NOP 巡检, bug8 兜底 in-vivo 持续观测.

## 下轮 (R1859)
继续常规巡检. **重点看 SR**: 若再次连续破 93 累积达连续 3 轮, 方达触发线需介入排查
(介入仍需先定位可配置旋钮, 若 502 仍全 NVCF 侧 config 不可修则无法硬改, 仅可记录归因)。

