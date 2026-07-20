# R2126 (hm2_cc2) — NOP R160 连续第95轮冻结. 30min SR 72.6% 下滑 (502 风暴簇, 非429非新类)

> 本轮核心事件: 30min SR 72.6% 显著下滑 (vs R2125 86.8% -14.2pp), 由 22:35 UTC 后 502 风暴簇驱动 (bad 5-6/桶, 22:40 桶 SR 25%). 但既有所有核心负向指标均未恶化: tier 429=0 (第4波已彻底滚出非429复发), 502×23 全 all_tiers_exhausted NVCF已知类0新可配类, fallback 6全75s SKIP-CIRCUIT被兜0真中断0失败0条120s跑满, breaker未真OPEN连续第28轮, StartedAt未漂移连续第15轮, BUG-A/CAP-RESET机制正常. 解冻指数退避仍不对症 (本轮问题是NVCF上游all_tiers_exhausted风暴簇, 非429非软挂, 指数退避链路碰不到此错误类). 0改动0restart.

## 数据 (本 session 拉取, 当前 CST 06:47 / UTC 22:47, 窗口起点 22:17 UTC)

### 30min nv_gw 成功率 + 错误分类
- status: 200×61 / 502×23 → SR = 61/84 = **72.6%** (vs R2125 86.8% -14.2pp 显著下滑; vs R2124 92.2% -19.6pp; vs R2118 自愈稳态 91.9% -19.3pp, **已跌出 86-92% 次稳态带**).
- 502 错误分类: **all_tiers_exhausted×23 全部** (NVCF 上游已知类, **0 新可配置类**) ✅.
- vs R2125 502=14 → +9 增多 (但仍全是 NVCF 已知类, 风暴簇驱动非散布).

### 5min 桶完整轨迹 (UTC, 40min)
| bucket | ok | bad | tot | SR |
|--------|----|----|-----|-----|
| 22:05  | 16 |  0 | 16 | 100% |
| 22:10  | 16 |  2 | 18 | 89%  |
| 22:15  | 15 |  4 | 19 | 79%  |
| 22:20  | 14 |  1 | 15 | 93%  |
| 22:25  | 10 |  3 | 13 | 77%  |
| 22:30  | 11 |  3 | 14 | 79%  |
| 22:35  |  9 |  5 | 14 | 64%  |
| 22:40  |  2 |  6 |  8 | 25%  | ← 风暴簇单峰
| 22:45  |  7 |  3 | 10 | 70%  |

- 22:05 桶全 200 (与 R2125 22:05-11 连续 7 桶全 200 稳态一致, 稳态延续到本窗口起点).
- 22:10-22:30 零星 502 散布 (bad 1-4/桶).
- **22:35-22:40 风暴簇抬头**: bad 从 5→6, ok 从 9→2, 22:40 桶 SR 25% (单桶风暴峰).
- 22:45 回落到 bad=3 (风暴簇似收尾).
- 对比 R2120/R2121 风暴主峰 bad 5-10/桶 连续多桶 → 本轮 22:40 单桶 bad=6 非长簇, 暂判短簇风暴.

### tier 30min 错误明细
- pexec_success×39 + NVCFPexecRemoteDisconnected×4 + 500_nv_error×2 + pexec_conn_RemoteDisconnected×1.
- **429_nv_rate_limit = 0** (vs R2125 ×1 → ×0, **第4波 429 已彻底滚出 30min 窗口**) ✅.
- **0 SSLEOFError** ✅.
- vs R2125: pexec_success 42→39 (-3), NVCFPexecRemoteDisconnected 6→4 (-2), 500_nv_error 2→2 (持平), pexec_conn_RemoteDisconnected 3→1 (-2). tier 层整体量略降.

### fallback (cc4101 30min)
- **6 FALLBACK-OK** (vs R2125 5 → +1; 0 真中断, 0 fallback 失败).
- 全 6 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类).
- **0 条 120s 跑满类** (持平 R2125) ✅.
- req 样本: 28c886b4 (06:20) / bd531035 (06:28) / ed23d944 (06:38) / f4b4bf34 (06:40) / b68d84ef (06:43) + 1 (06:47 前的).
- cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认 ✅.

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**.
- nv_gw 30min `grep -cE "BREAKER"` = **0** (state 未 OPEN, **连续第 28 轮**) ✅.

### BUG-A / CAP-RESET / abs_cap (R1913/R1818/R1918 机制)
- BUG-A `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (vs R2125 5 → 5, 持平, 持续复活, 机制真实生效) ✅.
- NV-CAP-RESET-MSFB = **5 条** (R1818 bug7 cap_origin reset 机制 execute→ms_fb path 正常触发, 全被 ms_fb 兜住 0 真中断; vs R2125 5 → 5 持平) ✅.
- abs_cap 30min = **5** (R1918 方案0 机制, 对应 CAP-RESET 5 条, 正常) ✅.

### 健康 + StartedAt + env
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv).
- nv_gw StartedAt = **2026-07-20T18:10:28Z** (R2107 后未再漂移, **连续第 15 轮核实 18:10 稳定**) ✅.
- cc4101 StartedAt = 2026-07-19T12:10:22Z (R1926 step2.0 后未变, 0 restart).
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动. **NVU_GLM52_EXP_BACKOFF 不在 env = 关, 半成品冻结中**.
- docker ps: nv_gw Up 5 hours / cc4101 Up 35 hours (容器创建时刻显示, 非 restart; 精确 StartedAt 已上面核实).

## 决策: NOP R160 连续第95轮冻结, 0 改动 0 restart

### 为何不改 (解冻指数退避仍不对症)
1. **本轮问题是 NVCF 上游 all_tiers_exhausted 502 风暴簇, 非 429 rate limit 复发**:
   - tier 429_nv_rate_limit = 0 (第4波已彻底滚出), 指数退避针对的 per-key 429 退避 + 软挂换 key **根本碰不到 all_tiers_exhausted 这个错误类** (该类是所有 tier 都试过仍失败, 不是单 key 被限流).
2. **502×23 全 all_tiers_exhausted NVCF 已知类, 0 新可配置类**: 不存在网关逻辑缺陷可调.
3. **fallback 0 失败 0 真中断 0 条 120s 跑满**: 用户诉求 "可以报错但不能让 cc2 中断" 仍达成. 6 条 fallback 全被 ms_gw 兜住.
4. **breaker 未真 OPEN 连续第 28 轮**: 没有切流, 不存在死循环请回来的风险.
5. **延长 chain_budget (指数退避激活需 120→420) 会反拖 SR**: all_tiers_exhausted 风暴期每个请求要试遍所有 tier 才失败, 延长 chain_budget 只会让每个失败请求占用更久, SR 反而更低. 九轮论证 (R2111/2116/2119/2120/2121/2122/2123/2124/2125) 仍成立.
6. StartedAt 未漂移连续第 15 轮, env 未变, 无外部扰动.

### 为何 SR 72.6% 下滑但仍 NOP
- STATE 下一步判断线: "若持续 < 85% 且 502 出新可配置类 才考虑评估". 本轮 SR<85% **但 502 仍全 NVCF 已知类 0 新可配类**, 且 fallback 0 失败 0 真中断, breaker 未真 OPEN — **不满足解冻触发条件**.
- 5min 桶显示 22:35-22:40 风暴簇抬头 (bad 5-6/桶), 但 22:45 已回落 bad=3, 暂判短簇风暴非长簇. 需下一轮观察是否延续.

## 下一轮该做什么

- **继续 NOP 巡检 (R161, 连续第 96 轮冻结)**: 重点看:
  1. **30min SR 是否回升回 86-92% 次稳态带或 91-96% 稳态核心区** (本轮 72.6% 跌出次稳态带, 由 22:35-40 风暴簇驱动; 若下一轮 5min 桶风暴簇已过 SR 回升则确认为短簇瞬态).
  2. **22:35-40 风暴簇是否延续/复发** (本轮单桶 bad=6; 若下一轮出现连续多桶 bad≥5 风暴簇, 需观察是否 NVCF 上游新故障期).
  3. **tier 429_nv_rate_limit 是否仍=0** (第4波已彻底滚出; 若再起 ~1h 周期复发需观察).
  4. 502 分类是否仍全 NVCF 已知类 0 新可配置类 (本轮 23 全 all_tiers_exhausted).
  5. fallback 是否仍全 75s SKIP-CIRCUIT 被兜住 0 失败; **关注 120s 跑满类是否再现增多** (本轮 0 条).
  6. breaker 是否仍非真 OPEN (连续第 29 轮); nv_gw StartedAt 是否仍 18:10:28Z (连续第 16 轮).
  7. **⚠️ NV-CAP-RESET-MSFB 是否持续增多** (本轮 5 条, 持平 R2125; 若稳态期持续增多且 SR 被拖低 → 需评估 chain_budget 是否过长耗 SR, 但仍非解冻指数退避理由).
- **若持续恶化才考虑动**: 任一指标恶化 (30min SR 持续 < 85% **非风暴污染** 且 502 出新可配置类 或 fallback 失败 或 breaker 真 OPEN 切流) 才考虑重新评估解冻. 本轮不满足 (502 全已知类 + 0 真中断 + breaker 未 OPEN).
- **轮号**: 下一轮 git pull 看最新, peer hm2_optimize_hm1 抢号很快; cc2 用 R2127 或更大 hm2_cc2 前缀不撞号.
- **若未来要解冻**: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步), 且实现 post-200 软挂换 key, 再 24h 观测. 当前不动.

## 状态变化 (cc2 视角)
- 无 (cc2 视角). nv_gw StartedAt 仍 18:10:28Z (连续第 15 轮核实未漂移), env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动 0 restart.
- 本轮需记录的变化: (1) **30min SR 86.8%→72.6% 显著下滑** (-14.2pp, 跌出 86-92% 次稳态带, 由 22:35-40 502 风暴簇驱动); (2) 502 14→23 (+9, 全 all_tiers_exhausted NVCF 已知类 0 新可配类); (3) **tier 429_nv_rate_limit ×1→×0 第4波 429 已彻底滚出 30min 窗口**; (4) tier pexec_success 42→39 (-3) / NVCFPexecRemoteDisconnected 6→4 (-2) / pexec_conn_RemoteDisconnected 3→1 (-2) 整体量略降; (5) fallback 5→6 (+1) 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满; (6) NV-CAP-RESET-MSFB 5→5 持平 / BUG-A SKIP-PEXEC2 5→5 持平 / abs_cap 5→5 持平; (7) breaker/abs_cap 全部未恶化, breaker 仍未 OPEN 连续第 28 轮, StartedAt 未漂移连续第 15 轮.

HM2 only. R2126
