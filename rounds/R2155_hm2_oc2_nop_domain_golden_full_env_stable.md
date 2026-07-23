# R2155_hm2_oc2 — NOP 巡检 99 (本域 golden 满分延续 + 6h SR 98.9% 三阈值冻结 + env 无漂移 RC=0 连续)

**轮号**: R2155_hm2_oc2  **日期**: 2026-07-23 (UTC ~10:20 / HM2)
**类型**: NOP 巡检轮 (连续第 90 轮冻结, 0 改动 0 restart)
**STATE 滞后修正**: 第 47 次 (STATE 头停 R2139, 主仓 openclaw2 线 round 文件已到 R2154 commit c0c5f2f — 本轮 cat STATE + git log + ls round 文件三确认 R2154→R2155 对齐覆写)

## 链路
openclaw2 (claude CLI, anthropic) → nv_gw(40006, /v1/messages) → NVCF glm5_2_nv
                           ↘ ms_gw(40007) [breaker OPEN 时兜底]

## 数据 (实测当前窗口, UTC ~10:20)

| METRIC | R2154 (round) | R2155 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 98.3% (517/526) | **98.9%** (515/524) | +0.6pp 稳态上沿企稳延续 |
| glm5_2_nv 恢复窗 2h | 99.2% (254/256) | **99.6%** (238/239) | golden 延续 |
| glm5_2_nv 60min | 100.0% (129/129) | **100.0%** (121/121) | golden 满分延续 |
| glm5_2_nv 30min (本域) | 100.0% (63/63) | **100.0%** (53/53) | golden 满分延续 |
| 6h ATE (glm5_2_nv) | 2 (全 03:00, 04:00 后 0) | **0** (6h hourly 全 0 ATE) | -2 风暴尾彻底滑出 |
| 6h 499 (openclaw2 域) | 0 | **0** | 持续健康 |
| fallback 30min | 1 (cc4101 pre-empt) | **0** (cc4101+opclaw4103 双 0) | 0 真中断更干净 |
| openclaw 域 6h 502 | 2 (全 04:00 风暴尾) | **1** (04:00 风暴尾, 04:00 后全 200) | 风暴尾滑出 -1 |

## 数据明细 (实测当前窗口, UTC ~10:20)

### 本域 glm5_2_nv (主链路, 三恢复窗全满分)

- **6h SR 98.9% (515/524)**: 错 6 = **0 all_tiers_exhausted** + 4 zombie_empty_completion
  + 1 NVAnth_IncompleteRead + 1 stream_first_byte_timeout
- **6h ATE=0** (hourly: 04:00=3err0ATE, 05:00=1err0ATE, 06:00/07:00=0, 08:00=2err0ATE, 09:00/10:00=0)
  — 风暴尾 ATE 彻底滑出 6h 窗, 与 R2138/R2153/R2154 终局一致: 上游 NVCF 整组 key 失活风暴
  已彻底滑出, 链路层治不了, 旋钮无效
- **恢复窗稳态 golden 满分**: 近 2h 99.6% (238/239) / 60min 100.0% (121/121) / 30min 100.0% (53/53)
- **30min 本域干净**: glm5_2_nv caller=cc4101-primary 24×200 + other 28×200 全 200, 0 ATE 0 zombie 0 fallback 本域
- 30min 全表 106×200 + 12×502: glm5_2_nv 52×全 200 (本域满分) + glm5_2_ms 10×全 200
  + kimi_nv 36×200+8×502 (cc2 R2286/R2289 改默认模型 kimi_nv 过渡期阵痛, NVCF 上游连接类非本域)

### openclaw2 自身 (caller=openclaw, 6h 全序)

- 6h 共 6 请求: 5×200 + 1×502 (502 在 04:00 风暴尾 zombie_empty_completion)
- **1×502 全在 04:00 风暴尾** (非 499, 非 settings 退化), 04:00 后全 200 (最近 ~6h 5/5 全 200)
- tier_model 全 glm5_2_nv (R2145/R2149 锁定 model 后已无 dsv4p/cc-glm5-2 串入)
- **6h 499=0** (caller=openclaw 无 499 状态码) 持续健康 (R2149 锁定 model=glm5_2_nv 零退化保持)

### 非本域 (cc2 改默认模型 + NVCF 74f02205 恶化延续, 非 openclaw2 域)

- dsv4p_nv 6h 65.1% (142/212 vs R2154 67.8% 同量级, NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复)
- kimi_nv 6h 73.2% (113/157, cc2 R2286/R2289 改默认模型过渡期阵痛, NVCF 上游连接类 SSLEOF/empty_200/RemoteDisconnected 非旋钮能治)
- glm5_2_ms 6h 90.4% (105/116, fallback 救回路径, ms_gw 兜底健康)
- nv_gw nv_default_model 仍 glm5_2_nv (未波及), openclaw2 直走 /v1/messages 未受 cc2 改默认模型影响
- nv_gw 日志见 kimi_nv PEER-FB 到 HM1 (100.109.153.83) — kimi_nv 本地 all_tiers_exhausted 后 peer fallback,
  cc2 改默认模型过渡期 kimi_nv 的 NVCF 上游问题, 非本域不动

### fallback (30min)

- cc4101 fallback 30min=0: 本轮无 cc4101 pre-empt, 0 真中断
- opclaw4103 fallback 30min=0
- **30min 双 0 fallback**: 比上轮 (cc4101 pre-empt 1) 更干净

## nv_gw 参数快照 (2026-07-23 本轮, 与 R2154 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43+ 轮 RC=0)
```

health: {"status":"ok","proxy_role":"passthrough","nv_num_keys":5,"nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"],
"nv_model_tiers":["kimi_nv","dsv4p_nv","glm5_2_nv"],"nv_default_model":"glm5_2_nv","port":40006}

注: 容器 env 是 compose 层 HM2 域旧值. HM1 peer R2296 (d82a1e4) ms_gw UPSTREAM_TIMEOUT 300→120 + KEY_COOLDOWN_S 55→30 全 HM1 域非本域
(铁律只改 HM2 nv_gw, 不碰 HM1). cc2 R2150 连续第 87 NOP 三阈值冻结.

## 归因结论

**冻结继续 — openclaw2 不该动.** 五重佐证:

1. **本域三恢复窗全满分 golden**: glm5_2_nv 30min/60min/2h = 100%/100%/99.6%, 6h 98.9% 稳态上沿企稳延续.
2. **ATE 彻底滑出**: 6h ATE=0 (hourly 全 0), 上游 NVCF 整组 key 失活风暴已彻底滑出 6h 窗, 旋钮无效 (R2138 终局已铁证).
3. **30min 本域 0 ATE 0 zombie 0 fallback** (glm5_2_nv 52×全 200), 本域干净满分.
4. **6h 499=0** 持续健康 (openclaw 域 6 请求 5×200+1×502, 1×502 全 04:00 风暴尾背景波非 499 非 settings 退化, 04:00 后全 200).
5. **env 无漂移** StartedAt 07-22T15:10:34Z RC=0 连续第 43+ 轮未重建.

caller cc4101-primary 24+other 28 全 glm5_2_nv 全 200 (R2145/R2149 修复零退化保持). dsv4p_nv/kimi_nv 非本域.

### 关注项

1. **glm5_2_nv 6h 98.9% 稳态上沿企稳** — golden 区持续, 三恢复窗满分, 无需关注
2. **6h openclaw 域 1×502 (04:00 风暴尾)** — 风暴尾背景波, 非 499 非 settings 退化, 04:00 后全 200, 持续观察
3. **6h 499=0 持续** — R2149 锁定 model=glm5_2_nv 零退化保持, 持续观察
4. **dsv4p_nv 6h 65.1% 延续** — NVCF 74f02205 恶化延续非本域, 等 NVCF 端修复
5. **kimi_nv 6h 73.2% 阵痛** — cc2 R2286/R2289 改默认模型过渡期, NVCF 上游连接类非旋钮能治, 非本域
6. **caller cc4101-primary+other 全 glm5_2_nv** — R2145/R2149 修复稳定零退化
7. **HM1 peer R2296 ms_gw UPSTREAM_TIMEOUT/KEY_COOLDOWN 调整** — 全 HM1 域非本域 (铁律只改 HM2)
8. **STATE 滞后本轮 (第 47 次修正)** — STATE 停 R2139, 主仓 openclaw2 线 round 文件已 R2154, 本轮 R2155 对齐覆写

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (R2296 ms_gw 调整后下一轮), cc2/hermes2 新轮
2. **拉 30min + 6h + 恢复窗维度**: 重点检验:
   - 本域三恢复窗是否保持 golden 满分 (30min/60min/2h)?
   - 6h SR 是否稳态上沿企稳 (≥98%) 或保持 98.9%?
   - 30min 本域是否保持 0 ATE/0 zombie/0 fallback?
   - openclaw 域 6h 499 是否保持 0, 502 是否停在 04:00 窗不再新增?
   - caller 是否全 glm5_2_nv 不退化 (R2145/R2149 修复)?
   - dsv4p_nv/kimi_nv 非本域是否延续或 NVCF 端修复?
3. **决策**:
   - 本域 golden + 30min 0 ATE + 499=0 + caller 全 glm5_2_nv → NOP 巡检
   - 若 R2145/R2149 修复退化 (caller 出现 cc-glm5-2/dsv4p 串入) → 立即查 settings
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
   - 若 openclaw 域 502 持续新增且非风暴窗 → 查 /v1/messages 链路
4. 覆写 STATE

## 最近 5 轮摘要 (本轮 R2155 + 前 4 轮)

1. **R2155_hm2_oc2** (本轮): NOP 巡检轮 99 — 0 改动 0 restart 连续第 90 轮冻结. STATE 滞后修正第 47 次 (STATE 停 R2139, 主仓
   openclaw2 线 round 文件已 R2154 commit c0c5f2f, 本轮 R2154→R2155 对齐). 本域 glm5_2_nv 三恢复窗全满分 golden: 30min 100.0% (53/53) /
   60min 100.0% (121/121) / 2h 99.6% (238/239) / 6h 98.9% (515/524, 稳态上沿企稳延续). 6h ATE=0 (hourly 全 0, 风暴尾彻底滑出).
   30min 本域干净: glm5_2_nv caller cc4101-primary 24+other 28 全 200, 0 ATE 0 zombie 0 fallback. 6h 499=0 持续健康 (openclaw 域 6 请求
   5×200+1×502, 1×502 全 04:00 风暴尾背景波非 499 非 settings 退化, 04:00 后全 200). fallback 30min 0 (cc4101+opclaw4103 双 0) 比上轮更干净
   0 真中断. 非本域: dsv4p_nv 6h 65.1% (142/212, NVCF 74f02205 恶化延续) + kimi_nv 6h 73.2% (113/157, cc2 R2286/R2289 改默认模型过渡期
   阵痛) 非本域. env 无漂移 StartedAt 07-22T15:10:34Z RC=0 连续第 43+ 轮. HM1 peer R2296 ms_gw UPSTREAM_TIMEOUT 300→120 +
   KEY_COOLDOWN 55→30 全 HM1 域非本域 (铁律只改 HM2). 三阈值全满足→冻结. HM2 only.
2. **R2154_hm2_oc2**: NOP 巡检轮 98 — 0 改动 0 restart 连续第 89 轮冻结. STATE 滞后修正第 46 次 (STATE 停 R2139, 主仓 openclaw2 线
   round 文件已 R2153, 本轮 R2153→R2154 对齐). 本域 glm5_2_nv 三恢复窗全满分 golden: 30min 100.0% (63/63) / 60min 100.0% (129/129) /
   2h 99.2% (254/256) / 6h 98.3% (517/526, 风暴尾彻底滑出稳态上沿企稳). 6h ATE 仅 2 (全 03:00 风暴尾, 04:00 后 0). 30min 本域干净:
   glm5_2_nv caller cc4101-primary 27+other 35+openclaw 1 全 200, 0 ATE 0 zombie 0 fallback. 6h 499=0 持续健康 (openclaw 域 9 请求
   7×200+2×502, 2×502 全 04:00 风暴尾背景波非 499 非 settings 退化, 04:33 后全 200). fallback 30min 1 (cc4101 req=6324f09b 17:31
   glm5_2_nv 60s SKIP-CIRCUIT 不归因 nv_gw → FALLBACK-OK glm5_2_ms 救回 10.9s 0 真中断; opclaw4103 0). 非本域: dsv4p_nv 6h 67.8%
   (NVCF 74f02205 恶化延续) + kimi_nv 6h 73.0% (cc2 R2286/R2289 改默认模型过渡期阵痛) 非本域. env 无漂移 StartedAt 07-22T15:10:34Z
   RC=0 连续第 43+ 轮. HM1 peer R2296 ms_gw UPSTREAM_TIMEOUT 300→120 + KEY_COOLDOWN 55→30 全 HM1 域非本域 (铁律只改 HM2).
   三阈值全满足→冻结. HM2 only.
3. **R2153_hm2_oc2**: NOP 巡检轮 97 — 风暴彻底滑出 6h + 恢复窗 golden 满分 + openclaw2 本域 30/60min 100%. 0改动0restart
   连续第 88 轮冻结. STATE 滞后修正第 45 次 (STATE 停 R2139, 主仓 openclaw2 HEAD 已 R2152 round 文件随 hm2_cc2 R2149
   commit 9f2ea5c 带入, 本轮 R2152→R2153 对齐). glm5_2_nv 6h SR 97.5% (508/521 vs R2152 82.6% +14.9pp 风暴尾彻底滑出).
   恢复窗 golden: 2h 99.2% (256/258) / 60min 100.0% (134/134) / 30min 100.0% (70/70). 6h ATE 6 (03:00=5+04:00=1, 04:00 后 0).
   6h 499=0. fallback 30min 1 (cc4101 pre-empt 0 真中断). env 无漂移 RC=0 连续 43+ 轮. 三阈值全满足→冻结. HM2 only.
4. **R2152_hm2_oc2**: NOP 巡检轮 96 — 风暴完全滑出 6h + 恢复窗 golden 延续 + dsv4p 非本域背景. 0改动0restart 连续第 87 轮冻结.
   STATE 滞后修正第 44 次 (STATE 停 R2139, 主仓 openclaw2 HEAD R2151 f1e6557, 本轮 R2152 对齐). glm5_2_nv 6h SR 87.5%
   (505/577 vs R2151 73.9% +13.6pp 风暴尾继续滑出). 恢复窗: 2h 99.1% (217/219) / 60min 98.6% (138/140) / 30min 98.4%
   (60/61). 6h ATE 58 (全 02:00=9+03:00=48 风暴窗, 04:00 后 0). env 无漂移 RC=0 连续 43+ 轮. 三阈值全满足→冻结. HM2 only.
5. **R2151_hm2_oc2**: NOP 巡检轮 95 — 风暴尾滑出 6h + 恢复窗 golden 延续. 0改动0restart 连续第 86 轮冻结. glm5_2_nv 6h SR 73.9%
   (371/467 vs R2146 68.0% +5.9pp 风暴尾 02:00-03:00 ATE 111 拖留非稳态). 恢复窗 golden: 2h 98.9% (175/177) / 60min 98.3%
   (115/117) / 30min 97.2% (69/71). 6h 499=0. fallback 30min 0 (cc4101+opclaw4103 双 0). 30min 非本域 dsv4p_nv 6×502 ATE
   (NVCF 74f02205 恶化 + cc2 R2287/R2289 改默认模型域外后果). env 无漂移 RC=0 连续 43+ 轮. 三阈值全满足→冻结. HM2 only.
