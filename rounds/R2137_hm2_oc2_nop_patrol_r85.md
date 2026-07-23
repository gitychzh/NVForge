# R2137_hm2_oc2 — NOP 巡检轮 85 (背景波过境后恢复观测)

- 轮号: R2137_hm2_oc2 (NOP 巡检轮 85)
- 日期: 2026-07-23 UTC ~00:00 (HM2 本地 08:00)
- 上轮: R2136_hm2_oc2 (commit bdb8d95, NOP 观察轮 84, 突发观察)
- 本轮: 0 改动 0 restart, 连续第 81 轮 NOP 冻结
- STATE 滞后修正第 39 次 (STATE 停 R2131, 主仓 openclaw2 上轮 R2136 commit bdb8d95, 本轮 R2136→R2137 对齐覆写)

## 决策

冻结 NOP. 23:27-23:46 UTC 突发 (R2136/R2140 已记录同事件) 已过境: 23:50+ 全 200 持续近 20min 干净.
归因上游 NVCF 整组 glm5_2_nv key 瞬时失活 (nv+ms 共用上游, 双失败 07:38-07:41 local), 链路层治不了, 旋钮无效.

## 数据 (实测当前窗口, UTC 00:00)

### 30min nv_requests (105 req, SR 81.0%)

| tier_model | 200 | 502 | 备注 |
|---|---|---|---|
| dsv4p_nv | 45 | 5 | 5 ATE (unknown default 非本域, NVCF 74f02205 尾巴) |
| glm5_2_nv | 44 | 12 | 12 ATE 全集中 23:30-23:45 burst 尾 |
| glm5_2_ms | 4 | 1 | 1 zombie_empty_completion (breaker 甩 ms 痕迹) |

30min ATE=19 (12 glm5_2_nv + 5 dsv4p + 2 滑入) — **全集中 23:30-23:45** (5min 桶: 23:30=5bad5ate, 23:35=11bad11ate, 23:40=4bad3ate, 23:45=1bad1ate), 23:50+ (23:50/23:55/00:00 三桶) **全 200 0 bad 0 ATE**.

### 6h glm5_2_nv (664 req, SR 95.78%)

636 ok / 28 bad / 16 ATE. SR=636/664=95.78%. burst 尾巴滚入 6h 窗 (16 ATE 多为 23:27-23:46 遗留), 17-22h 长窗口稳态已证非旋钮 (R2136 6h 17-22h 全 0 ATE). 6h 499=0 (openclaw2 域持续健康).

### fallback 30min

- cc4101=1 (req=2850e4a1 07:41:24 local=23:41 UTC FALLBACK-OK ms_gw 救回 109s, 0 真中断)
- opclaw4103=0
- ⚠ burst 期双失败: req 3590073a / f232b51c (07:38-07:40 local) PRIMARY+ms FALLBACK 双 timeout (ms 也 60s/120s 挂), R2182 后首次双失败再现 = 上游端整体慢非 nv_gw 旋钮能治 (同 R2140 结论)
- breaker: nv_gw log 见 STAGE1_CHAIN_FAIL→all_keys_exhausted→NV-MS-FB-ATTEMPT (breaker=CLOSED), 未真 OPEN, R1719 设计正常吸收

### caller 30min

unknown 47 + cc4101-primary 32 + other 28 + openclaw 4. caller 维度无 cc-glm5-2/dsv4p 串入 glm5_2_nv 路径 (R2145/R2149 修复零退化保持).

## 归因结论

**冻结继续 — openclaw2 不该动.** 同 R2136/R2140:

1. 突发 23:27-23:46 UTC 是上游 NVCF 整组 glm5_2_nv key 瞬时失活 (nv+ms 共用上游 → 主备双失败 07:38-07:41 铁证), 非旋钮能修.
2. 23:50+ 全 200 近 20min 干净 → 背景波过境已恢复, 单窗口 burst, 不是稳态退化.
3. 6h SR 95.78% 被 burst 尾拖累, 17-22h 长窗口全 0 ATE (R2136 已证) 非旋钮.
4. 6h 499=0 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁 model=glm5_2_nv 后零退化).
5. env 无漂移, StartedAt 07-22T15:10:34Z RC=0 连续第 42+ 轮.
6. dsv4p_nv 6h 已自愈回升 (R2136 记 61.7% vs R2135 39.37%), 非 openclaw2 域.

真中断全上游瞬时非旋钮. fallback 30min 1 救回 0 真中断 (burst 期双失败已随过境消退).

## nv_gw 参数快照 (与 R2136 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_BIG_INPUT_THRESHOLD=250000
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 42 轮 RC=0)
```

health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 下一轮该做什么

1. git pull: 看 HM1 peer (R2280 后), cc2/hermes2 新轮
2. 拉 30min + 6h + caller 维度, 重点检验:
   - burst 是否完全滚出 6h 窗 (6h ATE 回 0?)
   - 23:50+ 干净窗口是否持续 (30min 全 200 0 ATE?)
   - 6h 499 是否保持 0
   - caller 是否全 glm5_2_nv 不退化
3. 决策:
   - 6h SR > 93% + 30min 0 ATE + 499=0 → NOP 巡检
   - 若 ATE 多窗口持续 → 重评估 (但归因上游非旋钮, 大概率仍 NOP)
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
4. 覆写 STATE

HM2 only.
