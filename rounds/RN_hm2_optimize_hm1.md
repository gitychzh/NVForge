# RN: HM2 Optimize HM1 (锚定文件)

## 最新轮次
- **R499** (2026-07-01): ⏸️ NOP · CC清单3项6h+30min第4轮复检全证伪 · 6h SR=81.7%(757/927) · 30min SR=90.0%(90/100) · 170ATE全NVCF server-side(≈2×25s) · 0×429/empty200 · 5键全100%SR均衡 · 全参数天花板 · k4 via 7896 ✓p95=39.2s(vs旧直连54.4s↓28%) · compose-env零漂移 · 零配置变更 · 铁律:只改HM1不改HM2

## 历史轨迹
- R498: ★k4直连→mihomo 7896(p95 54.4s→39.2s) · compose漂移全同步
- R497: ⏸️ NOP · CC清单第3轮证伪
- R492: TIER_COOLDOWN 38→25 (修复不变量)
- R491: UPSTREAM 23→25 (+2s revert)
- R481: UPSTREAM 25→23 (-2s, later reverted in R491)
- R473: FASTBREAK 3→2 (-1)

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记
