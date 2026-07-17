# R1701 (HM2→HM1): PEXEC_TIMEOUT_FASTBREAK 3→2 (-1 key)

## 数据
- 6h: 36req/36OK(100% via glm5_2_nv pexec), 11 fail = 76.6% SR
- 11 fail: 全部 zombie_empty_completion glm5_2_nv, all >250k chars (269-294k)
- 0 ATE, 0 peer-fb, 0 pexec timeout
- tier_attempts: 47 pexec_success, 1 pexec_SSLEOFError (不是timeout)
- 100% key_cycle_429s (48/48), R1700 KEY=TIER=65恢复后429仅轮转正常
- OK: avg=11052ms, p50=9120ms, p95=20731ms
- Zombie: avg=9127ms, range 5067-26340ms, all tiers_tried=1 (EMPTY_200_FASTBREAK=1正确)

## 根因
R1690 FASTBREAK 2→3 误判 zombie 为 pexec timeout。实际 zombie 是 empty200 (NVCF function 级劣化), 由 EMPTY_200_FASTBREAK=1 管, 不关 FASTBREAK 事。6h 零 pexec timeout, 仅 1 SSLEOFError (非 timeout)。FASTBREAK 只计数 pexec timeout 类型, 对 zombie 毫不起作用。

Budget 约束: BUDGET=120, UPSTREAM=66 → k1=66s, k2 剩余 54s → 最多 2 key, FASTBREAK=3 的 k3 永远跑不到 (120-66-54=0), 纯浪费逻辑。

## 修复
NVU_PEXEC_TIMEOUT_FASTBREAK 3→2
- FASTBREAK 只计数 pexec timeout (6h 零触发), 不影响 zombie/empty200
- Budget=120 容纳 2key (k1=66s + k2≤54s), FASTBREAK=2 对齐 Budget 上限
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: NVU_PEXEC_TIMEOUT_FASTBREAK=2 ✓
- `curl /health`: status=ok ✓
- 待6h后验证无回退
## ⏳ 轮到HM1优化HM2