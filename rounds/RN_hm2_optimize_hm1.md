# R484 (HM2→HM1): ⏸️ NOP — dsv4p_nv tier 全NVCFPexecTimeout server-side · 全参数天花板 · 30min 1607req/83.3% SR · 1h 1634req/83.2% SR · p50=7435ms · 5键全100%OK · 269 ATE全NVCF server-side(~51s) · 0×429/empty200 · CC清单4项全证伪 · UPSTREAM=23 at floor · 铁律:只改HM1不改HM2 · 零配置变更 · 锚定: ⏳ 轮到HM1优化HM2

**轮次**: R484
**方向**: HM2优化HM1
**日期**: 2026-07-01 08:22 UTC (cron触发)
**类型**: NOP (No Operation — 无参数变更)
**Commit**: 09f5051 (R483)

## 关键指标
| 窗口 | 总请求 | 成功 | SR% | p50_ok | p95_ok | ATE | 429 |
|------|--------|------|-----|--------|--------|-----|-----|
| 30min | 1,607 | 1,338 | 83.3% | 7,435ms | 46,616ms | 269 | 0 |
| 1h | 1,634 | 1,360 | 83.2% | 7,435ms | 46,616ms | 274 | 0 |
| 6h | ~2,783 | ~2,489 | ~89.4% | 7,593ms | — | 294 | 0 |

**5键**: 全部100% OK, p50 6,801-7,961ms, cv≈5.4%. K1/K3 proxy path有更低p95 (32-38s vs 43-60s direct) — 正常路由差异.
**ATE**: 全部NVCFPexecTimeout server-side (upstream_type=NULL, 0 tier_attempts), avg=57s.
**SSLEOF**: 2次触发 (极罕见), 重试成功, SSLEOF_DELAY=2.0已达底限.

## 决策: ⏸️ NOP
- 8参数全在天花板: 无任何参数可安全下调
- 所有失败为NVCF server-side, 非proxy参数可影响
- CC清单4项持续证伪
- 少改多轮: 继续验证当前配置稳定性

**零配置变更**: docker-compose.yml不修改, 容器不重启.

## 锚定
## ⏳ 轮到HM1优化HM2