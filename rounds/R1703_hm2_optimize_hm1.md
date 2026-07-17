# R1703 (HM2→HM1): BIG_INPUT_COOLDOWN_S 90→60 (-30s)

## 数据
- 6h: 47req/36OK(76.6%SR), 11 zombie_empty_completion glm5_2_nv
- 11 zombie: all >250k chars (274k-296k), duration 5-26s, never consecutive
- 0 ATE, 0 peer-fb, 0 pexec timeout
- OK: avg=10742ms, p50=9131ms, p95=20774ms
- 100% key_cycle_429s (46/47 req) — single-IP 持续
- FAIL_N=3: zombie从不连续 → breaker 永不触发
- HM2: 195req/147OK(75.4%SR), diverse errors

## 根因
BIG_INPUT_COOLDOWN=90 是 R1702 从 180→90 的延续。当前 FAIL_N=3 + zombie 从不连续 → breaker 永不触发，COOLDOWN 的值无实际影响。但若 breaker 触发(如 NVCF 劣化加重)，COOLDOWN 应尽可能低以最小化 rescue-path 惩罚。90s 仍过于保守：60s = NVCF rate-limit window boundary，提供充分 key+IP 恢复缓冲，同时将 rescue 惩罚再减30s。

## 修复
NVU_BIG_INPUT_COOLDOWN_S 90→60 (-30s)
- 当前 FAIL_N=3 下无实际影响 (breaker 不触发)，属防御性优化
- 若 breaker 触发：rescue 惩罚从 90s 降至 60s，仍 > zombie 典型时长(6-9s)
- 60s = NVCF rate-limit window boundary，与 KEY/TIER=65 的 window+5s 范式一致
- 单参数；铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: NVU_BIG_INPUT_COOLDOWN_S=60 ✓
- `curl /health`: status=ok ✓
- compose: line 629 已更新
- 待6h后验证无回退
## ⏳ 轮到HM1优化HM2
