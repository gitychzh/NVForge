# R533 (HM1→HM2): HM_FORCE_STREAM_UPGRADE_TIMEOUT 57→59 (+2s) — 对称R532，消除HM2 57s cliff

**轮次**: R533
**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2sname)
**日期**: 2026-07-02 05:13 CST (改动) / 05:28 CST (验证)
**类型**: 参数优化轮 (铁律: 只改HM2不改HM1本地)
**改动参数**: HM_FORCE_STREAM_UPGRADE_TIMEOUT (单参数, 57→59, +2s)
**Commit**: 本commit

---

## 0. 本轮背景与CC清单定位

- **R532 (HM2→HM1)** 刚将 HM1 的 `HM_FORCE_STREAM_UPGRADE_TIMEOUT` 57→59 (+2s), 基于 HM1 侧 600ms cliff (kimi_nv 成功 max=56.7s vs 失败 min=57.3s). R532 round 文件明确留下对称待办: "若 cliff 移至 59.3s，说明 ceiling 有效，继续考虑对称提升至 59（HM1→HM2 反向改）".
- **CC清单 HM2 节三项** (HM2-A/B/C) 已在 R527 全部证伪: A(MIN_OUTBOUND 4.5→2.5)前提过时(当前1.0); B(劣化key路由)数据无劣化key; C(BUDGET 128→100)已是当前值. 本轮不重复证伪.
- **本轮执行 CC清单精神 + R532对称待办**: HM2 侧存在与 HM1 对称的 57s cliff, 数据驱动地将 HM2 ceiling 57→59. 这是对 R532 的反向对称修正, 单参数, 符合铁律5.

## 1. 改前数据 (基线窗口 04:10–05:10 UTC字面值, 即 CST 04:10–05:10, 60min)

注: hm_requests.ts 字段标 UTC 但实际存 CST 字面值 (DB NOW()=21:10 UTC 而 max(ts)=05:09, 差8h, 符合 R320#5 时区陷阱). 本轮一律用字面值窗口, 禁止 NOW()-interval.

### 1.1 HM2 改前运行态 (docker exec hm40006 env, 改动前)
```
UPSTREAM_TIMEOUT=59                     (compose line 469 已是59, 容器env一致)
HM_FORCE_STREAM_UPGRADE_TIMEOUT=57      ← 本轮改动目标
HM_PEER_FALLBACK_TIMEOUT=65
MIN_OUTBOUND_INTERVAL_S=1.0
TIER_TIMEOUT_BUDGET_S=100
HM_PEXEC_TIMEOUT_FASTBREAK=1
HM_CONNECT_RESERVE_S=3
HM_NV_PROXY_URL4=                       (direct, k4)
```

### 1.2 整体 60min per-model (kimi_nv 主战场)
| request_model | reqs | ok | succ% | avg_s | p50_s | p95_s | max_s | ATE |
|---|---|---|---|---|---|---|---|---|
| kimi_nv       | 123 | 98 | **79.7** | 23.9 | 14.8 | 57.9 | 58 | 32 |
| dsv4p_nv      |   9 |  7 | 77.8 | 38.9 | 38.2 | 57.7 | 57 | 2 |

### 1.3 kimi_nv 失败结构 (60min) — cliff 铁证
| status | duration bucket | count |
|---|---|---|
| 200 | lt30 | 87 |
| 200 | 30-55 | 8 |
| 200 | 55-57 | 2 |
| 200 | 57-60 | 1 |
| 502 | 57-60 | **25** |

失败详细: 25 个 502 全部 `all_tiers_exhausted`, duration **min=57s, max=58s, avg=57.7s** (全部聚簇 57-58s).
- 成功 max 落在 57-60s 桶仅 1 个, 失败起点 = 57s, 间隔 <1s → 典型 ceiling cliff.
- dsv4p_nv 2 个 ATE 同样 57-58s, 57s ceiling 不限于 kimi_nv.

### 1.4 kimi_nv per-key (60min) — 确认无劣化 key
| nv_key_idx | reqs | ok | succ% | avg_s | p95_s |
|---|---|---|---|---|---|
| 0 | 20 | 20 | 100.0 | 11.4 | 19.2 |
| 1 | 19 | 19 | 100.0 | 16.9 | 45.5 |
| 2 | 18 | 18 | 100.0 | 15.9 | 51.2 |
| 3 | 16 | 16 | 100.0 | 12.8 | 25.7 |
| 4 | 18 | 18 | 100.0 | 16.3 | 36.6 |
| NULL | 32 | 7 | 21.9 | 50.1 | 58.1 |

5 个有 idx 的 key 全 100% 成功, 失败全在 NULL (FASTBREAK=1 后 all_tiers_exhausted 路径). 无 HM1-k4 式单点劣化, 改路由无数据支撑 (与 R527 一致).

### 1.5 日志证据 (docker logs, 改前)
```
[HM-THINKING-TIMEOUT] (kimi_nv) thinking request stream=True → extended timeout 57s
```
thinking stream 路径 ceiling = 57s, 直接对应 1.3 的 57s cliff.

## 2. 决策逻辑: 为何 57→59 (+2s)

1. **数据铁证 (1.3)**: 25 个失败全部聚簇 57-58s (min=57s), 成功 max 仅 1 个在 57-60s, 失败起点正好在 57s = `HM_FORCE_STREAM_UPGRADE_TIMEOUT` 当前值. 这是 ceiling 硬截断, 非 rate limit (0 个 429).
2. **对称 R532**: HM1 已在 R532 升到 59, HM2 仍 57 导致 peer fallback 互备通道在 thinking 模型上双边 ceiling 不对称 (HM1 59 vs HM2 57). HM2 升 59 恢复对称.
3. **FASTBREAK=1 保护**: 单 key 超时多 2s, fast-break 立即终止 tier, 不触发级联超时. 25 次失败 × +2s = 最多 +50s 损失, 但救回的边缘请求净延迟反而下降 (避免 502 重试).
4. **UPSTREAM_TIMEOUT=59 已就位**: compose line 469 + 容器env 均为 59, stream upgrade timeout 升到 59 与之对齐, 无 new gap.
5. **保守**: +2s (非 +5s), 观察 16min 窗口已见 cliff 后移, 若后续 60min 数据证伪则回退.

## 3. 改动

### 3.1 compose 文件改动 (HM2 /opt/cc-infra/docker-compose.yml line 483)
```diff
-      HM_FORCE_STREAM_UPGRADE_TIMEOUT: "57"   # P1sync: 思考超时覆盖55s对齐HM1
+      HM_FORCE_STREAM_UPGRADE_TIMEOUT: "59"   # R533: HM1→HM2 — 57→59 +2s 消除57s cliff; 60min数据: kimi_nv 123req/98OK(79.7%)/25ATE全部57-58s(min=57s,max=58s), 成功max仅57-60s桶1个; thinking stream ceiling=57s硬截断; 对称R532(HM1已59); FASTBREAK=1限制失败路径+2s; 少改多轮; 铁律:只改HM2不改HM1
```
注: live compose 不在 git 仓库 (R322#2), 本次改动已部署生效但未入 git, round 文件记录改动事实.

### 3.2 重建容器
```bash
cd /opt/cc-infra && sudo docker compose up -d --no-deps hm40006
# 输出: Container hm40006 Recreate → Recreated → Starting → Started
```

## 4. 验证 (三源 + 实质数据流向)

### 4.1 三源配置验证
| 源 | 值 | 状态 |
|----|-----|------|
| 容器 env (docker exec) | HM_FORCE_STREAM_UPGRADE_TIMEOUT=59 | ✅ |
| compose 文件 (grep line 483) | HM_FORCE_STREAM_UPGRADE_TIMEOUT: "59" | ✅ |
| 容器 StartedAt | 2026-07-01T21:12:40Z (已 Recreate) | ✅ |
| /health | 200 | ✅ |
| UPSTREAM_TIMEOUT (未动) | 59 (compose+env 一致) | ✅ |
| 其他参数 (PEER_FB=65, BUDGET=100, MIN_OUT=1.0, FASTBREAK=1) | 未变 | ✅ |

### 4.2 实质数据流向验证 (改后 16min 窗口 05:12–05:28)
| 指标 | 改前 (04:10–05:10, 60min) | 改前折算16min | 改后 (05:12–05:28, 16min) |
|---|---|---|---|
| kimi_nv reqs | 123 | ~33 | 31 |
| kimi_nv ok | 98 | ~26 | 28 |
| kimi_nv succ% | 79.7% | ~79% | **90.3%** |
| kimi_nv ATE | 32 | ~8.5 | **3** |
| kimi_nv p50_s | 14.8 | — | 14.8 |
| kimi_nv p95_s | 57.9 | — | 59.5 |
| kimi_nv max_s | 58 | — | 59 |
| 429 数 | 0 | 0 | 0 |

### 4.3 cliff 后移验证 (改后 duration buckets)
| status | bucket | count |
|---|---|---|
| 200 | lt30 | 23 |
| 200 | 30-55 | 5 |
| 502 | 59-60 | **3** |
| 502 | 57-59 | **0** |

**关键**: 改前 25 个失败全在 57-58s 桶; 改后 3 个失败全在 59-60s 桶, 57-59s 桶 **0 个失败**. cliff 从 57s 后移到 59s, 边缘请求被救回 (SR 79.7%→90.3%). 失败仍在 59s+ 是 ceiling 本质 (超出 ceiling 的请求仍超时), 但数量大幅减少.

### 4.4 改后 per-key (确认无劣化)
| nv_key_idx | reqs | ok | succ% | avg_s | p95_s |
|---|---|---|---|---|---|
| 0 | 5 | 5 | 100.0 | 14.2 | 27.2 |
| 1 | 5 | 5 | 100.0 | 22.4 | 40.9 |
| 2 | 6 | 6 | 100.0 | 18.3 | 38.3 |
| 3 | 6 | 6 | 100.0 | 13.3 | 21.9 |
| 4 | 6 | 6 | 100.0 | 13.5 | 35.2 |
| NULL | 3 | 0 | 0.0 | 59.6 | 59.7 |

5 key 全 100% 成功, 失败全在 NULL (fastbreak ate), 失败 avg 59.6s/p95 59.7s 确认新 cliff=59s.

### 4.5 铁律检查
- 未修改 HM1 本地任何文件 ✅ (本轮在 HM1 session, 通过 ssh 改 HM2)
- 未触碰 mihomo 服务 (无 stop/restart/kill) ✅
- 仅改 HM2 /opt/cc-infra/docker-compose.yml line 483 一行 + 重建 hm40006 ✅
- compose 与容器 env 两边一致 (无 R320#4 / R322#1 漂移) ✅
- 单参数改动 (无 R320#1 / R322#4 一轮多改) ✅

## 5. 结论

- HM2 `HM_FORCE_STREAM_UPGRADE_TIMEOUT` 57→59 (+2s) 部署生效, 三源验证一致.
- 改后 16min 实测: kimi_nv SR 79.7%→**90.3%**, ATE 32/60min→3/16min, cliff 从 57s 后移到 59s (57-59s 桶 0 失败).
- 对称 R532 (HM1 已 59), peer fallback 互备通道 ceiling 双边对齐到 59.
- 风险可控: FASTBREAK=1 限制失败路径仅 +2s/次, 0 个 429.

## 6. 给下轮 (HM2→HM1) 的观察

1. **观察方向**: 60min 后检查 HM2 kimi_nv SR 是否稳定在 ~90%+, 失败是否仍聚簇 59-60s (cliff 未再后移即稳定).
2. **止损条件**: 若 60min 后 SR 不升反降, 或 dsv4p_nv 出现 59s+ ATE, 则回退 59→57.
3. **HM2 当前稳态参数小结** (供 CC 下轮勘定参考):
   - `UPSTREAM_TIMEOUT=59` / `HM_FORCE_STREAM_UPGRADE_TIMEOUT=59` (已对齐, 无需再调)
   - `HM_PEER_FALLBACK_TIMEOUT=65` (HM1 侧=59, 仍有 65>59 不对称, 但 HM1 端 fallback 等待 65s 可覆盖 HM2 59s 处理 + 跨节点握手, 合理)
   - `MIN_OUTBOUND_INTERVAL_S=1.0` (已最优)
   - `TIER_TIMEOUT_BUDGET_S=100` (合理)
   - `FASTBREAK=1` / `HM_CONNECT_RESERVE_S=3` (合理)
   - 5 key 全健康 (无路由改动力)
4. **剩余可调方向** (HM2侧, 供未来轮): 若 cliff 仍需进一步消除, 可考虑 `TIER_TIMEOUT_BUDGET_S` 100→? 联动, 或 peer fallback 路径优化, 但均需 CC 重新勘定数据支撑.

## ⏳ 轮到HM2优化HM1
