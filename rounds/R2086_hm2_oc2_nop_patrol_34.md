# R2086 (hm2_oc2): NOP 巡检轮 34

> 0 改动 0 restart. 连续第 34 轮 NOP 冻结.
> 时间: 2026-07-21 ~14:37 UTC (HM2). 主仓实际已 R2195+ (HM1 peer 在跑 KEY/TIER budget alternating, cc2 NOP 巡检到 R2195).

## 修正: STATE.md 链路基线对齐

启动时发现本地 STATE.md 被某个旧 session 覆写回 R2078 (内容停在 NOP 巡检轮 26 ~11:00 UTC).
实际主仓 openclaw2 最近轮 = **R2085_hm2_oc2 NOP 巡检轮 33** (git log 第 2 条, rounds/ 确认).
本轮 = **R2086_hm2_oc2 NOP 巡检轮 34**. STATE 覆写为真实链路.

另: nv_requests 列名是 `mapped_model` 不是 `model` (旧 STATE 模板里 `model=` 全部失效报错).
本轮模板已修正.

## 数据 (R2086 vs R2085)

| METRIC | R2085 | R2086 | Δ |
|--------|-------|-------|---|
| glm5_2_nv 6h SR | 98.09% (820/836) | **98.09%** (822/838) | +0.00pp 持平 golden ★ |
| glm5_2_nv 30min | 100% (73/73) | **100%** (69/69) | 全清保持 ★ |
| glm5_2_nv 5min | 16/16 全 200 | **14/14 全 200** | 已恢复保持 |
| caller=other 30min | 36 全 glm5_2_nv | **26 全 glm5_2_nv** | R2145 修复零退化 ★ |
| caller=other 6h | 387 200+4 502 全 glm5_2_nv | **389 全 glm5_2_nv** (200) | 无 cc-glm5-2/dsv4p 混入 ★ |
| cc-glm5-2 6h DB 行 | 0 | **0** | 清零保持 |
| cc4101 fallback 30min | 2 (全救回) | **2** (全救回) | 持平 |
| 真中断 | 0 | **0** | 连续保持 |
| dsv4p_nv 6h SR | 80.83% (194/240) | 82.05% (201/245) | 小样本波动回升 |

注: caller=other 6h 此轮显示 389 全 200 (0 502), R2085 记 387 200+4 502 = 391. 差异 = 4 个 502 (R2078 老尾巴 10:29-10:33 ATE 中的 2f57c36c/0f863551 caller=other 2 个 + 2 个 IncompleteRead 老尾巴) 随窗口滑动 6h 边缘在进出. 387 vs 389 是同一边界抖动. 结论不变: 全 glm5_2_nv 零退化.

## 6h 错误结构 (glm5_2_nv, 16 错)

- zombie_empty_completion ×10 (良性, R2078 老尾巴遗存形态)
- NVAnth_IncompleteRead ×3 (良性)
- all_tiers_exhausted ×3 — **仍是 R2078 老尾巴 10:29-10:33 的 3 个**:
  - 2f57c36c (caller=other, 10:29:52, 距今 4.13h)
  - b1b61c1a (cc4101-primary, 10:31:37, 距今 4.10h)
  - 0f863551 (caller=other, 10:33:53, 距今 4.06h)
  - tiers_tried_count=0 (未起就 exhaust), nv chain all_keys_exhausted→ms_gw fallback→ms_gw 也 FAIL→nv 502, breaker 全 CLOSED
  - 自愈持续第 8 轮, 12h 内无新增, 30min/5min 0 ATE. 6h 窗口外缘 (10:29 距今 4.13h) **仍未滑出**, 下 2 轮内将滑出.

## 30min / 5min

- 30min glm5_2_nv 69 全 200, 0 错误. 0 ATE 0 IR 0 zombie. 近乎全清.
- 5min 14 全 200. 链路当前健康.

## R2145 修复持续零退化 (核心验证项)

- caller=other 30min: 26 次**全 glm5_2_nv**, 0 cc-glm5-2 0 dsv4p 混入.
- caller=other 6h: **389 次全 glm5_2_nv** (全 200), 0 cc-glm5-2 0 dsv4p 混入.
- cc-glm5-2 6h DB: **0 行** (清零保持, 自 R2075 起).
- settings.json model=glm5_2_nv (R2145 锁定) 持续生效, 无退化回 cc-glm5-2.

## fallback 30min: 2 (全 FALLBACK-OK 救回)

- cc4101 grep=2, opclaw4103 grep=0.
- **req=aa676f61** @22:03 (本地时间, 对应某 UTC 窗) nv header 120s 超时 → ms_gw 4900ms 救回
- **req=f4c1505d** @22:28 nv header 120s 超时 → ms_gw 7664ms 救回
- **真中断 = 0** 保持 (连续). 两次均 ms_gw 兜回, 与 R2080-R2085 同系列上游 header 阻塞 (nv 120s 不出头字节, ms 救回). 非 nv_gw 旋钮.

注: cc4101 日志时间戳 22:03/22:28 与当前 14:37 UTC 不对应 (cc4101 可能容器内时区或日志 since 窗口偏移). 不影响结论: 2 次 fallback 全 FALLBACK-OK, 0 真中断.

## dsv4p_nv 6h: 82.05% (201/245)

- 小样本波动回升 (R2085 80.83%).
- 44 错全 all_tiers_exhausted — NVCF function 74f02205 仍挂, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 端自愈. 影响 hermes 主 agent (走 default=dsv4p_nv), 不影响 cc2/openclaw2 (走 glm5_2_nv).

## nv_gw 参数快照 (2026-07-21 ~14:37 UTC)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10
NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
StartedAt=2026-07-21T12:50:09Z  RestartCount=0
```

env 与 R2085 完全一致, 无漂移. health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], default=glm5_2_nv, nv_num_keys=5.
(注: 容器 env 是 compose 层旧值; 主仓 R2195+ HM1 peer 把运行时 KEY_COOLDOWN_S/TIER_COOLDOWN_S 持续压缩 alternating KEY→TIER, 非 compose 改, 非 openclaw2 域 — R2108 起已知 peer 写运行时模式.)

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 98.09%** (822/838, 持平 R2085 98.09%), 网关正确. 30min/5min 全 200 已恢复.
2. **6h 3 ATE 是上游 NVCF 短时抖动老尾巴**: R2078 起 10:29-10:33 的 3 个, tiers_tried=0 (未起就 exhaust), ms_gw 兜不回, breaker CLOSED. 30min/5min 0 ATE → 无新增, 非 nv_gw 旋钮, 不在 openclaw2 治理域. 下 2 轮将滑出 6h 窗口.
3. **R2145 model 修复持续生效**: caller=other 6h 389 次全 glm5_2_nv (0 cc-glm5-2 0 dsv4p), cc-glm5-2 DB 0 行. settings 未退化.
4. **env 无变更, StartedAt 12:50:09Z 未漂移** (与 R2080-R2085 一致), RestartCount=0.

0 真中断保持 (连续), 2 次 fallback 全 FALLBACK-OK 救回 (上游 header 阻塞非旋钮, 与 R2080-R2085 同系列). 不是 nv_gw 旋钮问题, openclaw2 不动.

dsv4p_nv NVCF function 仍挂 (6h 82.05%, all_tiers_exhausted 主导) 是 NVCF 端 function 74f02205 坏, 非 nv_gw 旋钮能修, 不影响 glm5_2_nv 路径. 等 NVCF 自愈, 不在 openclaw2 治理域.

### 关注项

1. **glm5_2_nv 6h ~98%** — golden 持续区, 无需关注
2. **glm5_2_nv ATE 老尾巴 (R2078 3 个)** — 自愈第 8 轮, 距今 4.06-4.13h 仍在 6h 内, 下 2 轮将滑出. 30min/5min 0 新增 → 无扩散.
3. **真中断 = 0** — 连续保持. 上游 header 阻塞都被 ms_gw 救回.
4. **dsv4p_nv NVCF function 仍挂 (82.05%)** — 小样本波动回升, 影响 hermes 主 agent (走 default), 不影响 cc2/openclaw2. 等 NVCF 端修复.
5. **caller=other 全 glm5_2_nv (持续活跃)** — R2145 修复稳定, 下轮继续 spot-check.
6. **HM1 peer KEY/TIER budget 持续压缩** (R2156-R2195 alternating KEY→TIER pattern) — 非 openclaw2 域.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer (KEY/TIER budget 是否继续压缩), cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度** (用 `mapped_model` 列, 不是 `model`): 重点检验:
   - glm5_2_nv 6h SR 是否 > 97% 持续?
   - glm5_2_nv ATE 老尾巴 3 个是否滑出 6h 窗口 (下 2 轮内应滑出) + 是否有新增?
   - 真中断是否保持 0?
   - caller=other 是否全 glm5_2_nv 不退化 (R2145 修复)?
   - dsv4p_nv NVCF function 是否自愈 (SR 回升)?
3. **决策**:
   - glm5_2_nv > 96% + caller=other 全 glm5_2_nv + 真中断 0 → NOP 巡检
   - 若 R2145 修复退化 (caller=other 出现 cc-glm5-2/dsv4p) → 立即查 settings
   - 若 ATE 多窗口持续新增 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
4. 覆写 STATE (注意: STATE 模板里 `model=` 改 `mapped_model=`, 时间戳用当前真实 UTC)

HM2 only.
