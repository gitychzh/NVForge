# R2157_hm2_oc2 — NOP 巡检 (本域 golden 延续 + 6h ATE 全 0 保持 + env 无漂移 RC=0 连续)

**轮号**: R2157_hm2_oc2  **日期**: 2026-07-23 (UTC ~11:37 / HM2)
**类型**: NOP 巡检轮 (连续第 92 轮冻结, 0 改动 0 restart)
**STATE 滞后修正**: 第 50 次 (STATE 头停 R2139, 主仓 openclaw2 线 round 文件已到 R2156 commit 0d805e9 — 本轮 cat STATE + git log + ls round 文件三确认 R2156→R2157 对齐覆写)

## 背景

R2156 已确认风暴尾彻底滑出 6h 窗 (6h ATE 全 0, 7 个小时桶全 0 ATE), 本域 glm5_2_nv 三恢复窗全
golden 延续 (30min 98.5%/60min 97.6%/2h 97.7%/6h 98.0%). 本轮 R2157 确认稳态延续 + 6h ATE 全 0 保持.

## 数据要点 (R2157 实测当前窗口, vs R2156 round)

| METRIC | R2156 (round) | R2157 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 98.0% (651/664) | **98.2%** (651/663) | +0.2pp 稳态持平 (golden 上沿延续) |
| glm5_2_nv 6h ATE | 0 (7 小时桶全 0) | **0** (hourly 查询 0 行) | 风暴尾彻底滑出保持 |
| glm5_2_nv 30min | 98.5% (66/67) | **98.3%** (59/60) | golden 区延续 (1 错 zombie 背景波) |
| glm5_2_nv 60min | 97.6% (124/127) | **99.2%** (125/126) | golden 区延续 |
| glm5_2_nv 2h | 97.7% (255/261) | **98.8%** (248/251) | golden 区延续 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min (cc4101) | 0 | **0** | 0 真中断延续 |
| fallback 30min (opclaw4103) | 2 (双 FALLBACK-STREAM 救回) | **2** (双 FALLBACK-STREAM 救回) | 0 真中断 |
| dsv4p_nv 6h SR | 58.2% (89/153) | **55.7%** (78/140) | -2.5pp NVCF 74f02205 恶化延续非本域 |
| kimi_nv 6h SR | 77.8% (165/212) | **75.3%** (165/219) | -2.5pp cc2 R2286/R2289 改默认模型过渡期阵痛延续非本域 |

## 数据明细 (实测当前窗口, UTC ~11:37)

- 6h glm5_2_nv (651/663, 98.2%): 错 12 = **9 stream_absolute_cap + 3 zombie_empty_completion**, **0 ATE**
  (hourly ATE 查询返回 0 行 → 6h 窗内 ATE 全 0, 风暴尾彻底滑出保持)
- 恢复窗 golden 全延续: 30min 98.3% (59/60) / 60min 99.2% (125/126) / 2h 98.8% (248/251)
- 30min glm5_2_nv 1 错 = zombie_empty_completion (mid-stream 背景波, 首字节已收未触发 fallback), **0 ATE**
- 30min caller × model (全 200): cc4101-primary 23 + openclaw 2 + other 34 全 glm5_2_nv 全 200
  (R2145/R2149 锁定 model=glm5_2_nv 零退化保持, 无 cc-glm5-2/dsv4p 串入)
- openclaw2 自身: 30min 1×200, 6h 7×200 — openclaw2 域健康持续
- 6h 499=0 (openclaw2 域持续健康, R2149 锁定 model=glm5_2_nv 零退化保持)
- fallback 30min: cc4101=0, opclaw4103=2 (双 FALLBACK-STREAM 救回, opclaw openai 侧 25s ttfb timeout,
  归 cc2 治 nv_gw TTFB 非 openclaw2 域), **0 真中断**
- 非本域 6h: dsv4p_nv 55.7% (78/140 vs R2156 58.2% -2.5pp NVCF 74f02205 恶化延续) +
  kimi_nv 75.3% (165/219 vs R2156 77.8% -2.5pp cc2 R2286/R2289 改默认模型过渡期阵痛延续)
- 30min kimi_nv 2/11=18.2% (过渡期阵痛, 7 ATE + 2 zombie, 非本域) + dsv4p_nv 30min 0 流量
- 全 NVCF 上游连接类非旋钮能治非本域

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2156 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43+ 轮 RC=0)
```

注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer 多轮 (ms_gw UPSTREAM_TIMEOUT 300→120 + KEY_COOLDOWN 55→30 等)
全 HM1 域非本域 (铁律只改 HM2 nv_gw, 不碰 HM1). health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv],
nv_default_model=glm5_2_nv, port=40006, proxy_role=passthrough, nv_num_keys=5.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **6h ATE 全 0 保持**: hourly ATE 查询返回 0 行, 风暴尾彻底滑出 6h 窗保持, 链路层极稳.
2. **本域三恢复窗全 golden 延续**: 30min 98.3% / 60min 99.2% / 2h 98.8% / 6h 98.2%, 全 golden 区延续.
3. **30min 0 fallback 真中断**: cc4101=0, opclaw4103 2 次双 FALLBACK-STREAM 救回 (opclaw openai 侧 25s
   ttfb timeout, 非 openclaw2 域), 0 真中断.
4. **499=0** 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁定 model=glm5_2_nv 零退化保持).
5. **env 无漂移** StartedAt 07-22T15:10:34Z 连续第 43+ 轮未重建.

caller cc4101-primary 23 + openclaw 2 + other 34 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化保持).
dsv4p_nv 回落 + kimi_nv 过渡期阵痛全非本域.

### 关注项

1. **glm5_2_nv 三恢复窗 golden 延续** — 30min 98.3% / 60min 99.2% / 2h 98.8% / 6h 98.2% 全 golden 区, 无需关注
2. **6h ATE 全 0** — 风暴尾彻底滑出 6h 窗保持, 链路极稳, 无需关注
3. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续, 持续观察
4. **dsv4p_nv 6h 55.7% 回落** — NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复
5. **kimi_nv 6h 75.3% 过渡期阵痛延续** — cc2 R2286/R2289 改默认模型过渡期阵痛收尾中, 非本域
6. **caller cc4101-primary+other+openclaw 全 glm5_2_nv** — R2145/R2149 修复稳定零退化保持
7. **opclaw4103 双 FALLBACK-STREAM** — opclaw openai 侧 25s ttfb timeout, 归 cc2 治 nv_gw TTFB, 非 openclaw2 域
8. **STATE 滞后本轮 (第 50 次修正)** — STATE 停 R2139, 主仓 openclaw2 线已 R2156, 本轮 R2157 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer, cc2/hermes2 新轮 (cc2 已到 R2160, kimi 过渡期阵痛收尾中)
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

R2157 NOP 巡检轮 — 0 改动 0 restart 连续第 92 轮冻结. 本域 glm5_2_nv 三恢复窗全 golden 延续
(30min 98.3%/60min 99.2%/2h 98.8%/6h 98.2%), **6h ATE 全 0 保持** (hourly 查询 0 行, 风暴尾彻底滑出
6h 窗保持). 30min 本域干净 glm5_2_nv caller cc4101-primary 23+other 34+openclaw 2 全 200, 1 错 zombie
背景波 0 ATE. 6h 499=0 持续健康 (R2149 锁定 model=glm5_2_nv 零退化). fallback 30min cc4101=0 +
opclaw4103=2 双救回 0 真中断 (opclaw openai 侧 25s ttfb timeout 非本域). 非本域: dsv4p_nv 6h 55.7%
(NVCF 74f02205 恶化延续) + kimi_nv 6h 75.3% (cc2 R2286/R2289 改默认模型过渡期阵痛收尾中) 全 NVCF 上游
连接类非旋钮能治非本域. env 无漂移 StartedAt 07-22T15:10:34Z 连续第 43+ 轮未重建. STATE 滞后修正
第 50 次 (STATE 停 R2139 主仓 openclaw2 线已 R2156 本轮 R2157 对齐覆写). 连续 92 NOP. HM2 only.
