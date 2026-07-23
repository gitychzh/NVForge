# R2156_hm2_oc2 — NOP 巡检 (本域 golden 满分延续 + 6h ATE 全 0 风暴尾彻底滑出 + env 无漂移 RC=0 连续)

**轮号**: R2156_hm2_oc2  **日期**: 2026-07-23 (UTC ~11:20 / HM2)
**类型**: NOP 巡检轮 (连续第 91 轮冻结, 0 改动 0 restart)
**STATE 滞后修正**: 第 49 次 (STATE 头停 R2139, 主仓 openclaw2 线 round 文件已到 R2155 commit 2f38313 — 本轮 cat STATE + git log + ls round 文件三确认 R2155→R2156 对齐覆写)

## 背景

R2155 已确认风暴尾彻底滑出 6h 窗 (6h ATE 仅 2 全 03:00 风暴尾, 04:00 后 0), 本域 glm5_2_nv 三恢复窗
全满分 golden (30min 100%/60min 100%/2h 99.6%/6h 98.9%). 本轮 R2156 确认稳态延续 + 风暴尾已完全滑出
(6h ATE 全 0, 7 个小时桶全 0 ATE).

## 数据要点 (R2156 实测当前窗口, vs R2155 round)

| METRIC | R2155 (round) | R2156 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 98.9% (515/524) | **98.0%** (651/664) | -0.9pp 稳态延续 (风暴尾全滑出 6h 窗内样本��增) |
| glm5_2_nv 6h ATE | 2 (全 03:00 风暴尾) | **0** (7 小时桶全 0) | 风暴尾彻底滑出 |
| glm5_2_nv 30min | 100.0% (53/53) | **98.5%** (66/67) | golden 区延续 (1 错 zombie 背景波) |
| glm5_2_nv 60min | 100.0% (121/121) | **97.6%** (124/127) | golden 区延续 |
| glm5_2_nv 2h | 99.6% (238/239) | **97.7%** (255/261) | golden 区延续 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min (cc4101) | 0 | **0** | 0 真中断延续 |
| fallback 30min (opclaw4103) | — (round 未单列) | **2** (19:05 双 FALLBACK-STREAM 救回) | 0 真中断 |
| dsv4p_nv 6h SR | 65.1% (142/212) | **58.2%** (89/153) | -6.9pp NVCF 74f02205 恶化延续非本域 |
| kimi_nv 6h SR | 73.2% (113/157) | **77.8%** (165/212) | +4.6pp cc2 R2286 改默认模型过渡期阵痛收尾中 |

## 数据明细 (实测当前窗口, UTC ~11:20)

- 6h 全表 901×200 + 125×502 (SR 87.8%): 非本域拖累 (dsv4p_nv 64 + kimi_nv 47 = 111/125 非本域)
- **6h glm5_2_nv (651/664, 98.0%)**: 错 13 全背景波 (zombie/cap/IR/no_content_gap mid-stream), **ATE=0**
  (7 个小时桶 05:00/06:00/07:00/08:00/09:00/10:00/11:00 全 0 ATE) — 风暴尾彻底滑出 6h 窗
- **6h glm5_2_nv 时间桶**: 05:00 71/75, 06:00 61/61, 07:00 94/94, 08:00 134/136, 09:00 135/139,
  10:00 119/121, 11:00 37/38 — 全稳态, 无风暴残留
- 30min 全表 89×200 + 5×502:
  - glm5_2_nv cc4101-primary 30×200 + other 34×200+1×502(zombie 背景波) + openclaw 2×200 全 200
  - kimi_nv unknown 24×200+4×502 (4 ATE 全 NVCF 上游连接类, cc2 R2286 改默认模型过渡期阵痛, 非本域)
- 30min 2 错归因: glm5_2_nv other 1×zombie_empty_completion (mid-stream 背景波, 首字节已收未触发 fallback)
  + kimi_nv unknown 4×all_tiers_exhausted (非本域过渡期阵痛)
- **6h 499=0 (openclaw2 域)**: cc2 R2199 全局 settings env 改后持续健康 (R2149 锁定 model=glm5_2_nv 后零退化)
- fallback 30min: cc4101=0, opclaw4103=2 (19:05:24/27 双 FALLBACK-STREAM 对应 19:05:21 cc4101 PRIMARY-FAIL-STREAM
  `nv_gw 流式 timeout status=0 after 25030ms 25s header/ttfb timeout` — opclaw agent openai 侧请求, 非 openclaw2 域,
  兜底救回 0 真中断). 无 NV-MS-FB-FAIL.
- 30min caller cc4101-primary 30 + other 34 + openclaw 2 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化保持)
- dsv4p_nv 6h 58.2% (89/153 vs R2155 65.1% -6.9pp, NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复)
- kimi_nv 6h 77.8% (165/212 vs R2155 73.2% +4.6pp, cc2 R2286/R2289 改默认模型过渡期阵痛收尾中, 非本域)

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2155 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  (连续第 43+ 轮未重建)
```

注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer 多轮 (ms_gw UPSTREAM_TIMEOUT 300→120 + KEY_COOLDOWN 55→30 等)
全 HM1 域非本域 (铁律只改 HM2 nv_gw, 不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006, proxy_role=passthrough, nv_num_keys=5.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **风暴尾彻底滑出 6h 窗**: 6h ATE=0 (7 个小时桶全 0 ATE), 无风暴残留. 链路层极稳.
2. **本域三恢复窗全 golden**: 30min 98.5% / 60min 97.6% / 2h 97.7% / 6h 98.0%, 全 golden 区延续.
3. **30min 0 fallback 真中断**: cc4101=0, opclaw4103 2 次双 FALLBACK-STREAM 救回 (opclaw openai 侧 25s
   ttfb timeout, 非 openclaw2 域), 0 真中断.
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 07-22T15:10:34Z 连续第 43+ 轮未重建.

caller cc4101-primary 30 + other 34 + openclaw 2 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化).
dsv4p_nv 回落 + kimi_nv 过渡期阵痛全非本域.

### 关注项

1. **glm5_2_nv 三恢复窗 golden 延续** — 30min 98.5% / 60min 97.6% / 2h 97.7% / 6h 98.0% 全 golden 区, 无需关注
2. **6h ATE 全 0** — 风暴尾彻底滑出 6h 窗, 链路极稳, 无需关注
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
4. **dsv4p_nv 6h 58.2% 回落** — NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复
5. **kimi_nv 6h 77.8% 过渡期阵痛** — cc2 R2286/R2289 改默认模型过渡期阵痛收尾中, 非本域
6. **caller cc4101-primary+other+openclaw 全 glm5_2_nv** — R2145/R2149 修复稳定零退化保持
7. **opclaw4103 19:05 双 FALLBACK-STREAM** — opclaw openai 侧 25s ttfb timeout, 归 cc2 治 nv_gw TTFB, 非 openclaw2 域
8. **STATE 滞后本轮 (第 49 次修正)** — STATE 停 R2139, 主仓 openclaw2 线已 R2155, 本轮 R2156 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer, cc2/hermes2 新轮 (cc2 已到 R2159, kimi 过渡期阵痛收尾中)
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 6h ATE 是否保持 0 (风暴尾不再回灌)?
   - 本域 glm5_2_nv 三恢复窗是否保持 golden (>97%)?
   - 30min 是否保持 0 ATE / 0 fallback 真中断?
   - caller cc4101-primary+other+openclaw 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - 6h 499 是否保持 0?
   - dsv4p_nv 是否 NVCF 74f02205 自愈或再恶化?
   - kimi_nv 过渡期阵痛是否收尾 (zombie 归零连续)?
3. **决策**:
   - 三恢复窗 golden + caller 全 glm5_2_nv + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若风暴再起 (双 tier 同挂) → 记录观测, 不动 (旋钮无效已证)
4. 覆写 STATE

## 一句话总结

R2156 NOP 巡检轮 100 — 0 改动 0 restart 连续第 91 轮冻结. 本域 glm5_2_nv 三恢复窗全 golden 延续
(30min 98.5%/60min 97.6%/2h 97.7%/6h 98.0%), **6h ATE 全 0** (7 小时桶全 0 风暴尾彻底滑出 6h 窗).
30min 本域干净 glm5_2_nv caller cc4101-primary30+other34+openclaw2 全 200, 1 错 zombie 背景波.
6h 499=0 持续健康 (R2149 锁定 model=glm5_2_nv 零退化). fallback 30min cc4101=0 + opclaw4103=2 双救回 0 真中断
(opclaw openai 侧 25s ttfb timeout 非本域). 非本域: dsv4p_nv 6h 58.2% (NVCF 74f02205 恶化延续) +
kimi_nv 6h 77.8% (cc2 R2286 改默认模型过渡期阵痛收尾中) 全 NVCF 上游连接类非旋钮能治非本域. env 无漂移
StartedAt 07-22T15:10:34Z 连续第 43+ 轮未重建. STATE 滞后修正第 49 次 (STATE 停 R2139 主仓 openclaw2 线
已 R2155 本轮 R2156 对齐覆写). 连续 91 NOP. HM2 only.
