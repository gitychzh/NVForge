# R2138_hm2_oc2 — NOP 终局观测轮 86 (上游风暴第二波持续 4.5h 终复)

- 轮号: R2138_hm2_oc2 (NOP 终局观测轮 86)
- 日期: 2026-07-23 UTC 04:45 (HM2 本地 12:45)
- 上轮: R2137_hm2_oc2 (commit 待补, NOP 巡检轮 85, 00:00 UTC 时点观测误判"已过境")
- 本轮: 0 改动 0 restart, 连续第 82 轮 NOP 冻结
- STATE 滞后修正第 40 次 (STATE 停 R2131, 主仓 openclaw2 上轮 R2136 commit bdb8d95 已 committed +
  R2137 round 文件本地未 commit, 本轮 R2137→R2138 对齐覆写并补 commit R2137)

## 决策

冻结 NOP. **修正 R2137 误判**: R2137 在 00:00 UTC 时点看到 23:50+ 20min 干净就判"风暴已过境恢复",
**事实是风暴在 00:00 后复发第二波, 持续到 ~03:30 UTC 才真正复** (共 4.5h: 23:27-03:30).
本轮 04:45 观测到终局恢复: 04:00 起 glm5_2_nv 回到 91% (42/46), ATE 仅余 1, 30min 0 ATE.
归因与 R2136/R2137 一致: 上游 NVCF 整组 glm5_2_nv key 失活, **nv+ms 双 tier 同时全挂** (01-02/02-03
两整小时 glm5_2_nv+dsv4p_nv **双 0ok 全 ATE**) 铁证 = 上游端整体故障非 nv_gw 旋钮能治. 改 env 无益有害.

## 数据 (实测当前窗口, UTC 04:45)

### 30min nv_requests (73 req, SR 86.3%)

| tier_model | 200 | 502 | 备注 |
|---|---|---|---|
| dsv4p_nv | 20 | 6 | 6 ATE (unknown default 非本域, NVCF 74f02205 尾巴抖动) |
| glm5_2_nv | 29 | 2 | 1 first_byte_timeout + 1 zombie (背景波级, 0 ATE, 已恢复) |
| glm5_2_ms | 18 | 2 | 1 stream_absolute_cap + 1 zombie (恢复期 tier 跳转残留) |

30min glm5_2_nv ATE=0 (恢复确认). 30min 全 ATE=6 全在 dsv4p_nv (非本域).

### 6h glm5_2_nv (490 req, SR 40.8% — 风暴拖累, 非稳态)

200 ok / 290 bad / 283 ATE. SR=200/490=40.8%. **6h 窗 (22:45-04:45) 正好框住整个风暴**, SR 暴跌 55pp
(vs R2131 的 96.08%) 全因上游风暴, 非 nv_gw 退化. 6h 499=0 (openclaw2 域持续健康, 风暴期也无 499).

### 6h 风暴时间轴 (glm5_2_nv, 关键修正 R2137)

| UTC hour | ok | err | ATE | 状态 |
|---|---|---|---|---|
| 22:00 (22-23) | 25 | 1 | 0 | 健康 (风暴前) |
| 23:00 (23-00) | 70 | 19 | 16 | **第一波起** (R2136/R2137 记录的 23:27 burst) |
| 00:00 (00-01) | 19 | 65 | 65 | 第一波深谷 (R2137 在此 00:00 时点误判"过境") |
| 01:00 (01-02) | **0** | 77 | 77 | **第二波最烈** (0 ok!) |
| 02:00 (02-03) | **0** | 76 | 76 | **第二波持续** (0 ok!) |
| 03:00 (03-04) | 44 | 48 | 48 | 部分恢复 |
| 04:00 (04-05, 当前 04:45) | 42 | 4 | 1 | **终局恢复** (91%) |

**双 tier 同挂铁证** (6h 同窗口): dsv4p_nv 01-02/02-03 两整小时同样 **0 ok 全 ATE** (各 18 ATE).
glm5_2_nv + dsv4p_nv **同时全挂** = 上游 NVCF 整体故障, 非 nv_gw 旋钮/key 轮转能修.

### openclaw caller 6h (38 req, SR 21% — openclaw2 自身吃风暴)

8 ok / 30 bad. openclaw2 在风暴期也大量失败 (23:00-02:00 每 hour dsv4p+glm_nv 全错), 印证 CLAUDE.md
"多走 primary" — openclaw2 跑得越多数据越细, 风暴期数据也留痕. 04:00 起 openclaw 链路 dsv4p 2ok/0 + glm_nv 2ok/2 已恢复.
6h openclaw 499=0 (openclaw2 域健康, 风暴挂的是 502 非 499).

### fallback 30min

- cc4101=4 (含 1 真救回: req=8ad0deb1 12:28 local=04:28 UTC glm5_2_nv 60s header timeout →
  PRIMARY-FAIL-SKIP-CIRCUIT → FALLBACK-OK ms_gw glm5_2_ms 救回 2.7s, 0 真中断; 其余为恢复期瞬时首字节超时)
- opclaw4103=0
- 恢复期 fallback 正常吸收, 0 真中断. breaker 未真 OPEN (R1719 设计正常吸收风暴).

### caller 30min

cc4101-primary 23 (12 glm_nv + 11 glm_ms) + other 23 (16 glm_nv + 7 glm_ms) + unknown 26 (全 dsv4p) +
openclaw 1. caller 维度无 cc-glm5-2/dsv4p 串入 glm5_2_nv 路径 (R2145/R2149 修复零退化保持, 风暴期也未退化).

## 归因结论

**冻结继续 — openclaw2 不该动.** 修正 R2137 误判, 终局观测:

1. 风暴总长 4.5h (23:27-03:30 UTC), 分两波: 第一波 23:27-00:30 (R2136/R2137 记录),
   **第二波 00:30-03:30 更烈 (01-02/02-03 双 0ok)**. R2137 在 00:00 第一波谷间喘息期误判"过境".
2. **glm5_2_nv + dsv4p_nv 双 tier 同时全挂** (01-02/02-03 双 0ok 全 ATE) = 上游 NVCF 整体故障铁证,
   nv+ms 共用上游, 主备双失败, 链路层治不了, 旋钮无效.
3. 04:00 起终局恢复: glm5_2_nv 91% ATE=1, openclaw2 链路恢复, 30min 0 ATE. 非稳态退化.
4. 6h 499=0 持续健康 (cc2 R2199 全局 settings env 改后, R2149 锁 model=glm5_2_nv 后零退化, 风暴期也无 499).
5. env 无漂移, StartedAt 07-22T15:10:34Z RC=0 连续第 43+ 轮未重建 (全程无人改 nv_gw, 正确).
6. dsv4p_nv 6h 67.6% (173/256 vs R2137 的 61.7% +6pp 回升中, 非 openclaw2 域).

真中断全上游瞬时非旋钮. fallback 30min 恢复期正常吸收 0 真中断.

## nv_gw 参数快照 (与 R2136/R2137 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3  NVU_BIG_INPUT_THRESHOLD=250000
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 43 轮 RC=0)
```

health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 下一轮该做什么

1. git pull: 看 HM1 peer (R2284 PEXEC_TIMEOUT_FASTBREAK 1→2 后), cc2/hermes2 新轮
2. 拉 30min + 6h + caller 维度, 重点检验:
   - 终局恢复是否持续 (30min glm5_2_nv 0 ATE 保持? 6h ATE 随风暴滚出窗回 0?)
   - 6h SR 是否随风暴滚出窗回升 (风暴滚出 6h 需 ~03:30+6h=09:30 UTC)
   - 6h 499 是否保持 0
   - caller 是否全 glm5_2_nv 不退化
   - dsv4p_nv 是否继续自愈
3. 决策:
   - 6h SR > 93% (风暴滚出后) + 30min 0 ATE + 499=0 → NOP 巡检
   - 若风暴复发 → 观测不改 (归因上游)
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
4. 覆写 STATE

HM2 only.
