# R545 (HM1→HM2): ⏸️ NOP — CC定向清单A/B/C三项前提全部被对端实测数据证伪; 另发现孤儿改动PEER_FB 55→50(compose标R545但无round文件)供CC裁决

## 0. 轮次定位
- 本轮执行者=HM1, 对端=HM2(host_machine=opc2sname, opc2_uname@100.109.57.26:222).
- 上轮 R544(HM2→HM1)为 NOP 轮, 称 HM1 网关参数已最优(dsv4p_nv 99.4% 控制组).
- 本轮按 CC 定向清单 HM2-A/B/C 节执行, 优先 A. 经实测三项目标参数前提均不成立(详见 §2), 顺延至 B 亦证伪, 按"三项都已做完或数据证伪"规则执行 NOP 轮, 不搭车任何参数.

## 1. HM2 当前运行态 (docker exec hm40006 env, 改前)
```
UPSTREAM_TIMEOUT=61
TIER_TIMEOUT_BUDGET_S=80                  # 清单C假设=128 → 证伪(R538已降到80)
HM_FORCE_STREAM_UPGRADE_TIMEOUT=61
HM_PEER_FALLBACK_TIMEOUT=50               # ⚠ 孤儿改动, 见 §3
HM_PEER_FALLBACK_ENABLED=1
HM_PEER_FALLBACK_URL=http://100.109.153.83:40006
HM_PEXEC_TIMEOUT_FASTBREAK=1
HM_SSLEOF_RETRY_DELAY_S=1.0
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=22
MIN_OUTBOUND_INTERVAL_S=1.0               # 清单A假设=4.5 → 证伪(R518已降到1.0, 远低于目标2.5)
HM_CONNECT_RESERVE_S=3
```

Routing (env): k0→7894, k1→7894, k2→7894, k3→7895, k4→7897, k5→7896 (compose 第496-500行)
HM2后端模型=glm5.1_hm_nv(不可改, 铁律4).

## 2. CC定向清单逐项数据证伪 (60min窗口 23:40–00:40 UTC = 07:40–08:40 CST)

### 2.1 [HM2-A] MIN_OUTBOUND_INTERVAL_S 4.5→2.5 — 证伪
- 清单假设 HM2 throttle=4.5s, 目标降到2.5.
- 实测 env `MIN_OUTBOUND_INTERVAL_S=1.0` (R518所设, compose 第472行确认), **已远低于清单目标2.5**.
- 60min 零429(§4.3), 无 throttle 压力迹象. 降到2.5 是回退, 非优化. **前提不成立, 跳过.**

### 2.2 [HM2-C] TIER_TIMEOUT_BUDGET_S 128→100 — 证伪
- 清单假设 HM2 BUDGET=128, 目标降到100.
- 实测 env `TIER_TIMEOUT_BUDGET_S=80` (R538所设, compose 第470行确认), **已低于清单目标100**.
- R538 数据: 成功无>80s(gt80_ok=0/159), 降到80 已验证安全. 100 是回退. **前提不成立, 跳过.**

### 2.3 [HM2-B] 失败模式/per-key劣化数据补采 — 证伪(无劣化key)
- 60min per-key 统计(hm_requests, 本地 key idx 0-4):
| nv_key_idx | total | ok | fail | SR | avg_ms | p50 | p95 | max_ms |
|---|---|---|---|---|---|---|---|---|
| 0 | 29 | 29 | 0 | 100% | 13570 | 6071 | 40108 | 50512 |
| 1 | 31 | 31 | 0 | 100% | 12420 | 7605 | 36917 | 55466 |
| 2 | 29 | 29 | 0 | 100% | 12300 | 8782 | 34216 | 77166 |
| 3 | 28 | 28 | 0 | 100% | 12969 | 8712 | 40637 | 50122 |
| 4 | 26 | 26 | 0 | 100% | 11319 | 8590 | 27683 | 30645 |
- **5个本地 key 全部 100% 成功, 无单 key 劣化.** k4(R544刚改7897)反而是 p95/max 最低(27683/30645), 改动有效.
- 失败全在 nv_key_idx IS NULL 路径(23 fail + 3 ok), 即 peer-fallback 转发到 HM1 的请求(HM1端也满载/surge), 非 HM2 本地 key 问题. **无 key 可改路由, 跳过.**

## 3. ⚠ 孤儿改动发现 (供CC裁决, 本轮不搭车)
- **现状**: compose 第486行 `HM_PEER_FALLBACK_TIMEOUT: "50"`, 标注 "R545: HM1→HM2 — 55→50 (-5s)..."; 运行态 env 同样=50.
- **历史**: R542(HM1→HM2)合法改 61→55. R543/R544 均 HM2→HM1 轮(只改HM1, 不应动HM2), 其 round 文件记录的 HM2 PEER_FB 仍是 55/61.
- **矛盾**: compose 现值=50 且标注 "R545", 但 git 历史无 R545 commit, 本轮之前无 R545 round 文件. 即该改动已部署生效(compose+env双源=50)但无 round/commit 记录.
- **推断**: 某个未记录的 session(可能上轮本应是R545但被R544 NOP占位, 或CC托底)提前改了 compose 并预写 "R545" 标注, 但未走 round+commit 流程.
- **本轮处置**: 铁律5(单参数少改多轮)+ 铁律1(只改HM2但不搭车未授权改动). 本轮为 NOP(三项证伪), 不将该孤儿改动"合法化"为本轮成果, 也不回滚(回滚=又一轮两改). 如实记录供 CC 裁决: 若 CC 认可 55→50 方向, 下轮可补 round 文件正式收录; 若不认可, 下轮回滚到55.
- **数据观察(不作为本轮改动依据, 仅供CC参考)**: 60min peer-fb 5条(1 ok ttfb=628ms / 4 fail ~50s), 失败耗时与 peer_fb=50 一致, 方向(省失败空等)与 R542 逻辑延续一致, 无回归迹象.

## 4. 改前数据 (60min窗口 23:40–00:40 UTC, NOP轮基线)

### 4.1 总体
| 指标 | 值 |
|---|---|
| total | 169 |
| success | 146 |
| fail | 23 |
| **SR** | **86.4%** |
| ok_avg | 13105ms |
| ok_p50 | 8547ms |
| ok_p95 | 40872ms |
| 失败类型 | all_tiers_exhausted ×23 (100%) |

### 4.2 NULL路径(peer-fb) 60min
| status | cnt | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| 200 | 3 | 40237 | 12515 | 84720 |
| 502 | 23 | 91909 | 50693 | 100056 |

### 4.3 报错计数 (docker logs --since 60m)
- 429: **0** (throttle=1.0 + KEY_COOLDOWN=38 有效, 无 rate-limit 压力)
- empty_200: 2 (极低, NVCF function 退化, 非参数可修, 同 R544 诊断)
- SSLEOF: 0 (HM_SSLEOF_RETRY_DELAY_S=1.0 稳定)

## 5. 分析与决策
- **dsv4p_nv 控制组逻辑(R544)在 HM2 侧同样成立**: 5个本地 key 全 100% 成功, 零429/零SSLEOF/极低empty_200, HM2 网关参数(MIN_OUTBOUND=1.0, BUDGET=80, KEY_CD=38, PEER_FB=50)已无安全可动空间.
- **失败根源 = peer-fb 路径(HM2本地tier耗尽后转发HM1, HM1端也surge/满载)**: 23/23 失败全 all_tiers_exhausted 来自 NULL key 路径, 与 HM1 侧 kimi_nv function-level surge(R544诊断)同源, 非HM2参数可修.
- **清单A/B/C 三项数据证伪**: A(MIN_OUTBOUND 已1.0<2.5), C(BUDGET 已80<100), B(5key全100%无劣化). 按"三项已做完或数据证伪"规则, 本轮 NOP, 不允许搭车未授权改动.
- **决策**: NOP, 不触任何HM2参数. 记录孤儿改动供CC裁决.

## 6. 执行记录
- **改动**: 无 (NOP 轮, 三项清单证伪).
- **部署**: 无 (无漂移需修, 无参数可动).
- **验证**: compose(第470/472/486行)+env+DB+logs 四源一致, HM2 运行态与各 round 声称一致(除 §3 孤儿改动).

## 7. 给下轮(HM2优化HM1)的建议
- **HM1 侧 R544 已 NOP**, HM2 侧本轮亦 NOP. 双机网关参数均已收敛, 失败根源在 NVCF function-level surge(kimi_nv)与 peer-fb 互救失败(双机同时满载).
- **CC 裁决项**: 孤儿改动 PEER_FB 55→50 是否收录. 若收录, 下轮HM2优化HM1时可补round; 若不认可则回滚HM2到55.
- **未来可探索(非本轮)**: peer-fb 双机同时满载时互救率为0, 可考虑跨机 surge 错峰或 NVCF function 级别 fallback(kimi_nv失败时降级其他function), 但属源码级改动, 风险高, 需CC专项授权.
- **严格铁律**: 下轮只改HM1, 不改HM2. 不搭车 §3 孤儿改动.

## ⏳ 轮到HM2优化HM1
