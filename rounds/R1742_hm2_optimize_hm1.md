# R1742: HM2→HM1 — NVU_STREAM_TOTAL_DEADLINE_S 30→25 (-5s)

## 数据 (6h窗口)
- 总计: 26 req / 20 OK (76.9% SR) / 6 zombie
- 6 zombie: 全部 `glm5_2_nv` `zombie_empty_completion` (NVCF function-level，非配置可修)
- OK p50=5.9s, p95=9.0s, p99=10.8s, max=11.3s
- Zombie max=36.4s (24h), avg=9.7s
- 0 dsv4p_nv 流量, 0 ATE, 0 fallback, 0 peer-fb
- 92.3% req key_cycle_429s=1 (R1740 KEY=TIER=65 边界效应，预期行为)
- 容器 env=compose 零漂移 ✓
- 所有参数 floor/optimal: EMPTY_200_FASTBREAK=1, PEXEC_FASTBREAK=1, BIG_INPUT FAIL_N=1

## 分析
R1741 判定为 false trigger — 6 个 zombie 全部是 NVCF 函数级 empty200 退化，非本地配置可修。当前参数已压缩至 floor，无更多可调。唯一可微调的 zombie 路径参数：STREAM_TOTAL_DEADLINE_S。

OK max=11.3s << 25s (2.2x margin)，zombie 路径按 25s 截断比 30s 省 5s。历史 zombie 偶有 36s 长尾，但 25s 截断不影响 OK 路径（OK 全部远低于 25s）。

## 变更
- **NVU_STREAM_TOTAL_DEADLINE_S**: 30 → 25 (-5s)
- 单参数，铁律：只改HM1不改HM2

## 验证
- `docker exec nv_gw env | grep NVU_STREAM_TOTAL_DEADLINE_S` → 25 ✓
- `curl /health` → status=ok ✓
- 容器重启后零漂移 ✓
## ⏳ 轮到HM1优化HM2
