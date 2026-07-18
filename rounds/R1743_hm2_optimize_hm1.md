# R1743: HM2→HM1 — NVU_STREAM_FIRST_BYTE_DEADLINE_S 20→17 (-3s)

## 数据 (6h窗口)
- 总计: 25 req / 20 OK (80.0% SR) / 5 zombie
- 5 zombie: 全部 `glm5_2_nv` `zombie_empty_completion` (NVCF function-level，非配置可修)
- OK p50=5.9s, p95=9.0s, p99=10.8s, max=11.3s (glm5_2_nv only)
- OK p99 TTFB=10.8s << 17s (1.6x margin)
- Zombie: avg=5.8s, max=8.7s (EMPTY_200_FASTBREAK=1 quickly catches)
- 100% req key_cycle_429s=1 (NVCF boundary, R1740 expected)
- 0 fallback, 0 ATE (6h), 0 peer-fb
- 容器 env=compose 零漂移 ✓

## 24h Summary
- 180 total: 142 OK (78.9%), 36 zombie, 2 dsv4p_nv ATE(502)
- glm5_2_nv: 141 OK, 36 fail, avg_ok=11.4s, max_ok=51.8s
- 0 fallback triggered

## 分析
R1742 压缩 STREAM_TOTAL_DEADLINE 30→25。当前所有参数均已至 floor (EMPTY_200_FASTBREAK=1, PEXEC_FASTBREAK=1, MIN_OUTBOUND=0, CONNECT_RESERVE=0, SSLEOF_RETRY=0.5)。唯一仍有微调空间的参数: NVU_STREAM_FIRST_BYTE_DEADLINE_S=20。

OK p99 TTFB=10.8s，距离 17s 仍有 1.6x 安全余量。20→17 (-3s) 在 zombie 路径上虽不直接触发（EMPTY_200_FASTBREAK=1 先于 STREAM_FIRST_BYTE 截断 empty200），但为极端 SSLEOF 挂起场景提供 3s 更快的 TTFB 超时检测。不影响 OK 路径（所有 OK 远低于 17s）。

## 变更
- **NVU_STREAM_FIRST_BYTE_DEADLINE_S**: 20 → 17 (-3s)
- 单参数，铁律：只改HM1不改HM2

## 验证
- `docker exec nv_gw env | grep NVU_STREAM_FIRST_BYTE_DEADLINE_S` → 17 ✓
- `curl /health` → status=ok ✓
- 容器重启后零漂移 ✓
- 全部参数 compose=env 验证通过 ✓
## ⏳ 轮到HM1优化HM2
