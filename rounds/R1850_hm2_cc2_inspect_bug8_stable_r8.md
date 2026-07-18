# R1850 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第 8 轮持续 0 触发, 链路稳 SR 94.8%

> 时间: 2026-07-19 08:30 CST (估, 拉数据时点)
> 模式: nv 直连 (cc4101→nv_gw). 0 改动 0 restart. StartedAt 仍 2026-07-18T21:26:29Z (R1839 改后字节码).

## 改前数据 (30min 窗)
- **SR**: 127/134 = **94.8%** (200:127 / 502:7). 跌破 95% 线但近 8 轮
  R1842 97.5% / R1844 97.0% / R1846 95.2% / R1847 94.1% / R1848 94.7% / R1849 94.6% / 本轮 94.8%
  全在 94-98% 抖动区间, **非系统退化** (未连 ≥3 轮破 93%, 近 3 轮 94.7/94.6/94.8 微回弹).
- **7 条 502 分类**:
  - zombie_empty_completion: 3
  - stream_first_byte_timeout: 2
  - all_tiers_exhausted: 1
  - stream_no_content_gap: 1
  - **全 NVCF 侧偶发降级路径外分支, config 不可修** (与 R1849 同构).
- **tier pexec (30min)**: success 87 / SSLEOFError 2 / 429 1 / empty_200 1. **无 zombie 无 ATE**.
  pexec elapsed max 43.8s / avg 10.0s / ≥60s 0 / ≥200s 0 (比 R1849 的 53s 更轻, 持续自愈).
- **fallback (cc4101 30min)**: 3 条, 全 SKIP-CIRCUIT (06:53/06:57/07:14 全 bug3 75s 抢断,
  cc4101 preempt nv_gw retry, 非 nv_gw 真正失败, NOT counted). **0 中断**. 未达 ≥4 阈值非恶化.
- **bug8 关键**: 实战降级触发 **0** (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空).
  兜底保险在位但 args 全合法不需触发, 符合 R1839 原话 "兜底保险就该几乎不触发".
- **breaker (30min)**: 1 NV-ANTH-BREAKER-FAIL (zombie 软挂 state=('CLOSED',2,0) 未 OPEN 设计内)
  + 2 NV-MS-FB-ATTEMPT/SERVED (all_keys_exhausted 进 ms fallback, nv_breaker recorded CLOSED). 无 OPEN.
- **env 无漂移** (UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1
  全与 R1849 快照一致).
- **oai_to_anth.py md5**: 4983bcec1d1203a1f3f8acf371786c6c 宿主 `/opt/cc-infra/proxy/nv-gw/gateway/format/`
  与 容器 `/app/gateway/format/` 一致 (550 行, R1839 改后字节码). bind-mount 正常.

## 介入触发条件核对 (STATE.md 四条)
1. SR 连续 ≥3 轮跌破 93%? — 否 (R1848 94.7 / R1849 94.6 / 本轮 94.8, 全守 93 线且微回弹).
2. fallback 非跳过类 ≥4 次/30min? — 否 (3 全 SKIP-CIRCUIT bug3 75s 抢断, 非 nv_gw 失败).
3. NV-ANTH-BREAKER-FAIL 出现 OPEN? — 否 (state=('CLOSED',2,0)).
4. 出现新的可配置错误分类? — 否 (7 502 全 NVCF 侧 zombie/first_byte/all_tiers/gap 老分类).
- **四条全不满足 → NOP 巡检轮. 硬改违反铁律.**

## 改了什么
NOP — 无 compose env / 无 .py 改动 / 0 restart.
维持 bug8 兜底在位观测 (oai_to_anth.py 四要素全在: `_detect_bad_tool_args()` @319 +
`_downgrade_to_end_turn` flag @97/375/381 + 两处 final_stop 强制 end_turn @399-400/442-443).

## 验证结果
- 链路稳: SR 94.8% 在抖动区间下沿微回弹, 非退化.
- bug8 兜底 in-vivo 在位 + 实战 0 触发 (设计内: 几乎不触发).
- breaker 全 CLOSED, fallback 全抢断类 0 中断.
- env 无漂移, oai_to_anth md5 一致, StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码.
- /health ok (passthrough, nv_num_keys=5, NVCF pexec models 正常).
- pexec elapsed 全 <60s, NVCF 侧持续自愈.

## 决策理由
链路稳 + 无 config 可改依据 + 四条介入触发全不满足 → 不改. 维持常规巡检节奏.
连续 8 轮 NOP 巡检 (R1842-R1850) 链路稳态确认, bug8 兜底治本持续 in-vivo 在位 0 触发.
