# R2118 (hm2_cc2) — NOP R152, 连续第 88 轮冻结

> 本轮 = NOP 巡检轮, 0 改动 0 restart. R2116 NVCF 429 风暴完全自愈确认.

## 拉数据时间

CST 04:35:23 / UTC 20:35:23. 30min 窗口起点 20:05 UTC, **R2116 风暴高峰 (19:45-20:00 UTC) 已完全滚出 30min 大窗**.

## 30min nv_gw 数据

| 指标 | 本轮 (R2118) | R2116 | 变化 |
|---|---|---|---|
| 30min SR | 125/136 = **91.9%** | 75.2% | +16.7pp 回稳态 |
| 200 | 125 | 100 | +25 |
| 502 | 11 | 32 | -21 大幅回落 |
| 429 | 0 | 1 | -1 |

### 小窗 SR (风暴滚出后稳态确认)

- last3 = 17/18 = 94.4%
- last5 = 25/27 = 92.6%
- last10 = 50/54 = 92.6%
- last15 = 71/78 = 91.0%
- last20 = 95/102 = 93.1%

全 91-94% 区间, 完全回到稳态 (vs R2116 last3 77.8% 风暴回落尾期).

### 5min 桶 (UTC, 风暴→自愈完整轨迹)

- 19:55: 200×5 / 502×7 / 429×1 (风暴高峰尾部)
- 20:00: 200×8 / 502×19 (R2116 峰值, SR 29.6%)
- 20:05: 200×11 / 502×3 (开始回落, 78.6%)
- 20:10: 200×19 / 502×2 (90.5%)
- 20:15: 200×25 / 502×0 (100%)
- 20:20: 200×21 / 502×2 (91.3%)
- 20:25: 200×24 / 502×2 (92.3%)
- 20:30: 200×24 / 502×2 (92.3%)
- 20:35: 200×7 / 502×1 (87.5%, 当前桶样本小)

## 502 错误分类 (30min, 11 条)

- all_tiers_exhausted × 8
- zombie_empty_completion × 2
- NVAnth_IncompleteRead × 1

**全 NVCF 上游已知类, 0 新可配置类** ✅ (vs R2116 all_tiers×31+zombie×2).

## tier 30min

- pexec_success × 30
- NVCFPexecRemoteDisconnected × 14
- pexec_conn_RemoteDisconnected × 6
- **429_nv_rate_limit = 0** (vs R2116 ×28 爆发, 风暴彻底滚出) ✅
- **0 pexec_SSLEOFError** (本次风暴纯 429 非 SSL)

## 未恶化机制 (核心)

| 指标 | 本轮 | 判定 |
|---|---|---|
| 真中断 | 0 (cc4101 both failed / UPSTREAM-ERROR-SEEN = 0) | ✅ |
| fallback | 7 全 75s SKIP-CIRCUIT 被 ms_gw 兜住, 0 失败, 0 条 120s 跑满 | ✅ (vs R2116 11 条) |
| breaker 30min | 1 recorded (NV-ANTH-BREAKER-FAIL zombie_empty_completion, state=('CLOSED',1,0), 04:32:35 req=e268d940) | ✅ recorded 但 CLOSED=单点软挂正常吸收, **连续第 22 轮** state CLOSED 未 OPEN 切流 |
| BUG-A SKIP-PEXEC2 | 4 次触发 | ✅ 持续复活生效 (R1913 修复真实有效) |
| abs_cap 30min | 0 | ✅ R1918 方案0 持续归零 |

fallback 样本 (全 75s SKIP-CIRCUIT, 全被兜): 3b06341f / 95f5992d / 4d489b7b / dd82a38a / 1aa377bd / d973182d / 93b2186f.

## 状态变化 (cc2 视角)

- nv_gw StartedAt = **2026-07-20T18:10:28Z** (连续第 8 轮核实未漂移, peer R2107 重启后稳定)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变)
- env 仍 peer R2108 改后值 (KEY_COOLDOWN=60 / TIER_COOLDOWN=180 / MIN_OUTBOUND=10), cc2 0 改动
- NVU_GLM52_EXP_BACKOFF 不在 env = 半成品仍冻结, chain_budget 仍 120s 未升 420
- 0 改动 0 restart

## 本轮需记录的变化

1. R2116 429 风暴**完全自愈**: 30min SR 75.2%→91.9% (+16.7pp), 502 32→11, tier 429_nv_rate_limit 28→0.
2. 5min 桶完整记录风暴→自愈轨迹 (20:00 峰值 502×19 → 20:10 后稳态 502×2-3).
3. 502 全 NVCF 已知类 (all_tiers×8+zombie×2+NVAnth_IncompleteRead×1), 0 新可配置类.
4. fallback 7 (vs R2116 11) 全 75s SKIP-CIRCUIT 被 ms_gw 兜住, 0 失败 0 条 120s 跑满.
5. breaker 30min recorded=1 (zombie 单点软挂, state CLOSED) = 连续第 22 轮未 OPEN; BUG-A SKIP-PEXEC2 4 次; abs_cap=0 全部未恶化持平.
6. nv_gw StartedAt 仍 18:10:28Z 连续第 8 轮核实未漂移; env 0 变更.

## 冻结理由 (连续第 88 轮) 仍成立

半成品未经 in-vivo 验证 (env 开关从未激活, NVU_GLM52_EXP_BACKOFF 根本不在容器 env) + 激活需同步 chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等: 本轮 30min SR 91.9% 0 真中断, abs_cap 30min 归零, BUG-A 修复真实生效, 边际收益小; R2116 风暴同 R2111 模式 (周期性 NVCF 429 约 1h 一波自愈), 非逻辑缺陷, 解冻不对症 (429 风暴延长 chain_budget 反拖 SR, R2111/R2112/R2113/R2116 四轮论证).

## 用户诉求达成

"可以报错但不能让 cc2 中断" (2026-07-19 01:40) 仍达成: R2118 0 真中断; 7 条 FALLBACK-OK 全被 ms_gw 兜住, 0 fallback 失败.

## HM2 only

只改 HM2 nv_gw (40006), 不碰 ms_gw (40007, 重启窗口热备), 不碰 HM1. 本轮 0 改动 0 restart.
