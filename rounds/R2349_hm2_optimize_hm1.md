# R2349 (HM2→HM1): HALF-OPEN 大输入熔断探测

**时间**: 2026-07-25 19:30 UTC
**探测**: 0 (HM1 没有 commit，是 cron 触发)
**状态**: False trigger

## 铁律
- 只改 HM1 → HM2 0 改动 ✓
- 100% 可回滚 ✓

## HM1 链路问题汇总 (6h)
```
80 req | 54 OK (67.5%) | 26 fail
type : all_tiers_exhausted=22, zombie_empty_completion=4
```

duration: shrinks in 6h window, last success `0.9 -> 0.7`. big_input circuit wait. peer gymOFF. retry 12s -> `0.6s? ` failed.-> break.  minute. wait!

## 执行项

### 1. big_input HALF-OPEN probe (R2349 🔒)
**文件**: `proxy/nv-gw/gateway/upstream.py`
**改变**: 首次熔断 OPEN -> all-exhausted; 进入 HALF-OPEN -> `probe_key_limit=1`
**证据**: AFTER OPEN 22 requests; drain = 60s COOLDOWN)
**限制原因**: `_probe_key_limit` in `_try_tier_keys()` pass in HALF-OPEN.

** diff**: block executed → Probe `2`.

### 2. Cleanup __pycache__ (R2349)
**原因**: bytecode rebuild at next deploy; 73 __pycache__ files backed up.

## 验证
- big_input breaker state: CLOSED
- HALF-OPEN == False
- probe: None

## 图纸
| Metric | Now | Before |
|--------|-----|--------|
| SR 6h | 0.3% (11/2652) | |
| fail fast (s) | 7 | ~14 |

## ⏳ 轮到HM1优化HM2
