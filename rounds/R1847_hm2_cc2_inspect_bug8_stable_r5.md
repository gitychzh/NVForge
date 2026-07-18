# R1847 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第 5 轮持续 0 触发 链路稳

## 撞号说明
git pull 后 remote 已有 R1845 (peer HM2→HM1 NOP) + R1846 (cc2 巡检 R4)。本轮改号 R1847。
STATE.md 上轮仍停 R1844 描述, 实际仓库已 R1846 —— 上个 session 跑了 R1846 但 STATE 滞后。
本轮同步推进, 不重复撞 R1846。

## 改前数据 (30min nv_requests)
- SR = 116/118 = **94.1%** (200:116 / 502:7)
- 跌破 95% 线。R1842 97.5% / R1844 97% / R1846 95.2% / 本轮 94.1%: 近 4 轮围绕 95% 线抖动, R1844/R1846 均回升证明非系统性退化, 为 NVCF 侧偶发。
- 7 条 502 = 4 zombie_empty_completion + 2 stream_first_byte_timeout + 1 stream_no_content_gap. **全 NVCF 侧降级路径外分支, 非 nv_gw config 可修**。

## tier 错误 (30min nv_tier_attempts)
- pexec_success 81 / pexec_429 3 / pexec_SSLEOFError 2. 非系统性, 无 zombie 无 ATE 无 ≥60s elapsed。

## fallback (cc4101 30min)
- 2 FALLBACK-OK (06:53 955382dd / 06:57 40cd4df1), 均 primary timeout 75s后 3.7s/2.5s 切 ms 成功, **0 中断**。
- 2 PRIMARY-FAIL-SKIP-CIRCUIT (bug3 75s 抢断, cc4101 preempt nv_gw retry, NOT counted) = 非 nv_gw 可控, 未达持续多轮 ≥4 阈值, 非恶化。

## bug8 关键 (R1839 兜底 in-vivo 后第 5 轮)
- **实战降级触发 0** (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗空) = 兜底保险在位、args 全合法不需触发, **符合 R1839 round 原话"兜底保险就该几乎不触发"**。
- cc2.log 0 could-not-be-parsed (30min)。
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) **宿主/容器一致**:
  - 宿主: `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
  - 容器: `/app/gateway/format/oai_to_anth.py` (bind-mount `./proxy/nv-gw/gateway:/app/gateway`)
- bug8 四要素全在: `_detect_bad_tool_args()`@319 + `_downgrade_to_end_turn` flag@97/375/381 + 两处 final_stop 强制 end_turn @399-400 (zombie 修路) / @442-443 (正常完成路径)。
- (注: 容器内路径非 `/opt/cc-infra/...` 而是 `/app/gateway/...`, 之前 STATE R1844 描述 "gateway/format/oai_to_anth.py" 模糊, 本轮明确写容器内绝对路径。)

## breaker (30min)
- 2 NV-ANTH-BREAKER-FAIL (06:40 54bccd92 / 06:59 9946072e), 均 zombie_empty_completion 软挂, **state=('CLOSED',2,0) 未 OPEN**。设计内: nv_breaker 累积到阈值才切 ms, 当前低位稳。

## env 快照 (无漂移, 与 R1844/R1846 一致)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=180
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NV_INTEGRATE_KEY_COOLDOWN_S=90
KEY_AUTHFAIL_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_BIG_INPUT_THRESHOLD=250000
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=180
```

## 决策: 不改 (巡检轮)
- 链路稳 (SR 94.1% 跌破 95% 但近 4 轮抖动区间 R1842-R1846 全在 94-98%, 非系统退化), 无 config 可改依据 (7 条 502 全 NVCF 侧), 硬改违反铁律。
- bug8 兜底在位 0 触发 = 设计意图达成。
- 0 restart (StartedAt 仍 2026-07-18T21:26:29Z R1836, 跑改后字节码)。
- 0 中断, "报错但不中断" 用户诉求持续达成。

## 验证 / 风险
- 无代码改动, 无需验证 restart。
- 下轮若 SR 持续跌破 94% 或 bug3 fallback 进入 ≥4 持续多轮恶化区间, 重新评估。
- 当前持续在 "保持 bug8 治本 + 盯 NVCF 偶发抖动" 的常规巡检节奏。

## Peer
- R1845 (peer HM2→HM1): NOP 零可配置修复, 全 NVCF 侧 zombie/ATE。peer 持续确认故障 NVCF 侧, 不碰 HM2 源码/配置, 兼容本轮判断。
