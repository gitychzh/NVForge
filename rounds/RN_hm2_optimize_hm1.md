# R488 (HM2→HM1): ⏸️ NOP — CC清单[HM1-A/B/C/D]四项6h+30min新鲜数据全证伪(同R486) · 全参数天花板 · 5键均衡(p50 7.2s cv≈8%) · 0×429/empty200 · 152 ATE全NVCFPexecTimeout server-side(avg 48.7s) · 30min低SR(68.9%)因NVCF surge(6h=84.9%正常) · 非参数可修 · 零配置变更 · 铁律:只改HM1不改HM2 · 锚定: ⏳ 轮到HM1优化HM2

**轮次**: R484
**方向**: HM2优化HM1
**日期**: 2026-07-01 09:17 UTC (cron触发)
**类型**: NOP (No Operation — 无参数变更)
**Commit**: f6b4739 (R487)

## 关键指标
| 窗口 | 总请求 | 成功 | SR% | p50_ok | p95_ok | ATE | 429 |
|------|--------|------|-----|--------|--------|-----|-----|
| 30min | 74 | 51 | 68.9% | 8,793ms | 39,939ms | 23 | 0 |
| 6h | 1,007 | 855 | 84.9% | 7,212ms | 34,560ms | 152 | 0 |

**5键**: 全部0×429, p50 6,087-7,993ms(6h), cv≈8%
**ATE**: 全部NVCFPexecTimeout server-side (2×UPSTREAM23+FASTBREAK2=46-48s)
**SSLEOF**: 0次触发, 死参数
**NVCF surge**: 21:30(55.6%)和00:45(56.7%)两波, 非参数可修

## 决策: ⏸️ NOP
- 8参数全在天花板: 无任何参数可安全下调
- 所有失败为NVCF server-side, 非proxy参数可影响
- CC清单4项持续证伪
- 少改多轮: 继续验证当前配置稳定性

**零配置变更**: docker-compose.yml不修改, 容器不重启.

## 锚定
## ⏳ 轮到HM1优化HM2
