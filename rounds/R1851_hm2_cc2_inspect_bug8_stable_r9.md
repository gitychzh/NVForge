# R1851 (HM2 cc2) — 巡检轮 bug8 降级兜底 in-vivo 后第 9 轮持续 0 触发 链路稳 SR95.6%

> NOP 巡检轮。0 改动,0 restart。上一轮基线 R1850 (287841c)。

## 改前数据 (30min 窗)
- **SR 129/135 = 95.6%** (200:129 / 502:6)。回到 95% 线以上,比 R1850 的 94.8% / R1849 的
  94.6% / R1848 的 94.7% / R1847 的 94.1% 微涨。近 9 轮 R1842-R1850 全在 94-98% 抖动区间,
  本轮回升非系统退化(未连 ≥3 轮破 93%)。
- 6 条 502 = 3 zombie_empty_completion + 1 all_tiers_exhausted + 1 stream_absolute_cap
  + 1 stream_first_byte_timeout,**全 NVCF 侧偶发降级路径外分支 config 不可修**。
  注:出现 1 例 stream_absolute_cap(R1850 无),属 NVCF 侧内容流上限,非 config 可修。
- **tier pexec**: success 97 / 429 3 / SSLEOF 2 / empty_200 2 / timeout 1,无 zombie 无 ATE。
  pexec 流量比 R1850(success 87)更密,success 更多,链路健康度持平偏强。
- **fallback 2 FALLBACK-OK**: 均 bug3 75s preempt 抢断
  (`PRIMARY-FAIL-SKIP-CIRCUIT primary timeout after 75081ms < chain budget 120s, likely
  cc4101 pre-empted nv_gw retry, NOT counted toward circuit`),非 nv_gw 失败,NOT counted,
  未达 ≥4 阈值非恶化。**0 中断**。
- **bug8 关键**: 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空)。兜底在位但 args
  全合法不需触发,符合 R1839 round 原话"兜底保险就该几乎不触发"。
- **breaker**: 2 NV-ANTH-BREAKER-FAIL (1 zombie + 1 stream_absolute_cap) 软挂
  state=('CLOSED',2,0)/('CLOSED',1,0) 未 OPEN,设计内;1 NV-MS-FB-SERVED
  (all_keys_exhausted 进 ms fallback, nv_breaker recorded CLOSED)。0 OPEN。
- **env 无漂移**: UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1
  全与 R1850 一致。
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致,R1839 改后
  字节码四要素全在。

## 改了什么
NOP (不改)。无 compose env / 无 .py 改动。0 restart。

## 验证结果
- /health ok (proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models 3 个)。
- StartedAt 仍 2026-07-18T21:26:29Z (R1836 restart, R1839 至 R1851 未再 restart) → 跑 R1839
  改后字节码。
- SR 95.6% 回升至 95% 线上 + bug8 0 触发 + breaker 全 CLOSED + pexec success 97 持平偏强 +
  0 中断 + env 无漂移 + md5 一致。
- docker ps nv_gw 健在。

## 决策理由
链路稳 + 6 条 502 全 NVCF 侧 config 不可修 + 介入触发四条全不满足
(SR 未连 ≥3 轮破 93 / fallback 非跳过类 <4 / breaker 未 OPEN / 无新可修错误分类) → 硬改违反铁律。
连续 9 轮 NOP (R1842-R1851) 链路稳态,维持常规巡检节奏。

## 下一步
继续常规巡检。介入触发条件不变(任一满足才动手):
1. SR 连续 ≥3 轮跌破 93%。
2. fallback 中非跳过类(FALLBACK-OK 真正 nv_gw 失败)≥4 次/30min。
3. NV-ANTH-BREAKER-FAIL 出现 OPEN。
4. 出现新的可配置错误分类(非 NVCF 侧 zombie/timeout/gap/absolute_cap)。

0 restart 0 中断。
