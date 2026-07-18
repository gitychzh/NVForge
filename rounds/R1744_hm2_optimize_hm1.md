# R1744: HM2→HM1 — NVU_PEER_FALLBACK_TIMEOUT 124→122 (-2s)

## 数据 (6h窗口)
- 总计: 25 req / 20 OK (80.0% SR) / 5 zombie
- 5 zombie: 全部 `glm5_2_nv` `zombie_empty_completion` (NVCF function-level，非配置可修)
- OK p50=6.4s, p99=10.8s, max=11.3s (glm5_2_nv only)
- 0 ATE (6h), 0 peer-fb triggered, 0 fallback
- 100% req key_cycle_429s=1 (NVCF boundary, R1740 expected)
- 容器 env=compose 零漂移 ✓

## 24h Summary
- 180 total: 142 OK (78.9%), 36 zombie, 2 dsv4p_nv ATE(502)
- dsv4p_nv ATE: 2×502 at 69-70s (all_tiers_failed_in_mapped_tier), fallback_actually_attempted=false
- glm5_2_nv: 141 OK, 36 fail, avg_ok=11.4s, max_ok=51.8s
- 0 fallback triggered

## 分析
R1743 压缩 STREAM_FIRST_BYTE 20→17。当前所有 floor 参数已至底 (EMPTY_200_FASTBREAK=1, PEXEC_FASTBREAK=1, MIN_OUTBOUND=0, CONNECT_RESERVE=0, SSLEOF_RETRY=0.5)。唯一仍有微调空间的参数: PEER_FALLBACK_TIMEOUT=124。

Constraint check: PEER_FALLBACK_TIMEOUT ≥ HM2_BUDGET+2 = 72. 当前 124 >> 72，远高于约束底线。dsv4p peer-fb: 70+124=194 < 195 (仅1s margin)。6h内零 peer-fb 触发，当前 timeout 从未被实际使用，压缩不会影响已有路径。

124→122 (-2s): 仍满足约束 122≥72 ✓。dsv4p peer-fb: 70+122=192 < 195 (3s margin, up from 1s)。释放 2s budget headroom 为未来 BUDGET 压缩预留空间。

## 变更
- **NVU_PEER_FALLBACK_TIMEOUT**: 124 → 122 (-2s)
- 单参数，铁律：只改HM1不改HM2

## 验证
- `docker exec nv_gw env | grep NVU_PEER_FALLBACK_TIMEOUT` → 122 ✓
- `curl /health` → status=ok ✓
- 容器重启后零漂移 ✓
- 全部参数 compose=env 验证通过 ✓
## ⏳ 轮到HM1优化HM2
