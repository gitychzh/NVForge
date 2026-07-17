# R1702 (HM2→HM1): BIG_INPUT_COOLDOWN_S 180→90 (-90s)

## 数据
- 6h: 48req/37OK(77.1%SR), 11 zombie_empty_completion glm5_2_nv
- 11 zombie: all >250k chars (274k-296k), duration 5-26s, never consecutive
- 0 ATE, 0 peer-fb, 0 pexec timeout, 47/48 key_cycle_429s
- OK: avg=10511ms, p50=9076ms, p95=20689ms
- tier_attempts: 48 pexec_success, 1 pexec_SSLEOFError (非timeout)
- FAIL_N=3 (R1698): 3 consecutive zombies required → never triggers (zombie pattern: 1 per ~30min burst, never consecutive)
- HM2: 208req/153OK(73.6%SR), diverse errors (stream gap/timeout, zombie, ATE)

## 根因
BIG_INPUT_COOLDOWN=180 是过度防御。当前 FAIL_N=3 + zombie 从不连续 → breaker 永不触发，COOLDOWN 的值无关紧要。但若 breaker 触发(如 NVCF 劣化加重)，180s 的 rescue-path 惩罚过长：rescue=peer-fb(72s)<HM2_BUDGET(120+2) → guaranteed timeout → ms_gw(120s)=192s >> zombie(6-9s)。COOLDOWN=90s 仍提供充分缓冲(NVCF recover window)，同时将救援惩罚减半。

## 修复
NVU_BIG_INPUT_COOLDOWN_S 180→90
- 当前 FAIL_N=3 下无实际影响 (breaker 不触发)，属防御性优化
- 若 breaker 触发：rescue 惩罚从 180s 降至 90s，仍 > zombie 典型时长(6-9s)
- 90s 足够 key 恢复 + NVCF IP 窗口重置
- 单参数；铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: NVU_BIG_INPUT_COOLDOWN_S=90 ✓
- `curl /health`: status=ok ✓
- compose: line 629 已更新
- 待6h后验证无回退
## ⏳ 轮到HM1优化HM2
