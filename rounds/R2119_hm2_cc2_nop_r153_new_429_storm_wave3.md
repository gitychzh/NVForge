# R2119 (hm2_cc2): NOP R153 — 连续第 89 轮冻结, 新一轮 NVCF 429 风暴再起 (周期性 ~1h 第 3 波)

## 数据 (本 session 拉取, CST 04:51, 窗口 20:21-20:51 UTC)

**本轮核心事件**: R2118 判定 R2116 风暴完全自愈 (30min tier 429=0) 后约 16min, **新一轮 NVCF 429 rate limit 风暴再起** (20:40 UTC 首现), 模式与 R2111/R2116 完全一致 — **周期性 ~1h 一波** (R2111 02:45 CST → R2116 03:45 CST → 本轮 04:45 CST, 间隔精确 ~1h).

### 30min 窗口
- nv_gw 30min SR = 130/150 = **86.7%** (200:130 / 502:19 / 429:1)
- vs R2118 拉时 91.9% **-5.2pp** (30min 大窗被 20:40 后新一波风暴拉低)
- 502=19 全 **all_tiers_exhausted×16 + zombie_empty_completion×3 + NVAnth_IncompleteRead×1** (全 NVCF 已知类, **0 新可配置类**) ✅
- tier 30min: **429_nv_rate_limit=10** (vs R2118 =0, **0→10 又回升!**) + NVCFPexecRemoteDisconnected×10 + pexec_conn_RemoteDisconnected×2 + pexec_success×33 + empty_200×1. **0 SSLEOFError** (纯 429 非 SSL, 同 R2116).

### 小窗 (风暴进行中, 20:40 首现 → 20:50 仍在攀升)
- last3 = 9/20 = **45.0%** (被 20:50 桶峰值 502×5 主导)
- last5 = 22/33 = 66.7%
- last10 = 43/55 = 78.2%
- last15 = 60/75 = 80.0%
- last20 = 82/99 = 82.8%

### 5min 桶完整轨迹 (UTC)
- 20:20-20:39 稳态 (每桶 200:14-24 / 502:1-2, **tier 429=0**, R2118 自愈期延续)
- **20:40 tier 429×3 首现** (502 仍×2, tier retry 吸收)
- **20:45 tier 429×7 + 502×6 + 429×1 爆发上浮** (tier retry 撑不住开始上浮成 all_tiers)
- **20:50 502×5 峰值** (SR=7/12=58.3%, 风暴仍处上升期未达 R2116 20:00 峰值 502×19 程度)

### 6h 窗口 (失真不采信)
- 6h SR = 637/1742 = 36.6% (502:1013 / 200:637 / 429:92), 含 R2111+R2116+本轮 3 波风暴 + R2107 重启前远古风暴, 等 CST 08:10 后 6h 窗口完全滚出风暴期才采信.

### 未恶化指标 (全部持平, 0 真中断)
- **fallback 6 条全 FALLBACK-OK, 0 真中断, 0 fallback 失败** (cc4101 `both failed|UPSTREAM-ERROR-SEEN`=0)
- 全 6 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb timeout 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类). **0 条 120s 跑满** (持平 R2118). req 样本: 9519e392 / 410fabb7 ... 全被 ms_gw 兜住.
- **cc4101 PRIMARY-BREAKER-OPEN 30min = 0**; nv_gw 30min `grep BREAKER` 命中 1 条但实为 `[NV-BIGINPUT-SUCCESS] breaker→CLOSED` (big_input breaker 成功后 CLOSED, 非真 OPEN). state **CLOSED 连续第 22 轮未 OPEN 切流**.
- **BUG-A (R1913) 生效**: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (持续复活, vs R2118 4 次 +1) ✅
- **abs_cap 30min = 0** ✅

### 容器状态
- nv_gw /health = ok (proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=dsv4p_nv, port=40006)
- docker inspect StartedAt: nv_gw=**2026-07-20T18:10:28Z** (R2107 后未再漂移, 连续第 9 轮核实 18:10 稳定) / cc4101=2026-07-19T12:10:22Z (0 restart 未变)
- env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), NVU_GLM52_EXP_BACKOFF 不在 env = 关, cc2 0 改动 0 restart.

## 决策: 继续 NOP (连续第 89 轮冻结), 0 改动 0 restart

### 不改理由 (解冻触发条件均不满足)
1. 30min SR 86.7% 是**新一轮 429 风暴 (20:40-20:50) 进行中**所致, 非持续恶化. 20:20-20:39 完全自愈期 (tier 429=0, SR 95%+), 20:40 才再爆发. NOP 巡检仍正确: 大窗被风暴高峰污染 + 502 全已知类 0 新可配.
2. 502=19 全 NVCF 已知类 (all_tiers×16+zombie×3+NVAnth_IncompleteRead×1), **0 新可配置类**.
3. 0 真中断 (cc4101 both failed=0), fallback 6 全兜 0 失败 0 条 120s 跑满.
4. breaker state CLOSED 连续第 22 轮, BUG-A 触发 5 次持续复活, abs_cap 30min=0.
5. 根因 NVCF 上游 429 rate limit **非网关逻辑缺陷**. 解冻指数退避不对症: 429 风暴延长 chain_budget (120→420) 反拖 SR (R2111/2112/2113/2116 + 本轮 R2119 **五轮论证**).
6. peer hm2_optimize_hm1 近轮在 walk-back R2110 storm 期 KEY/TIER 上调 (R2114 TIER 70→68, R2115 KEY 77→75, R2116 TIER 68→66, R2117 TIER 66→64, 均 HM1 侧), 与 HM2 cc2 nv_gw 链路隔离, cc2 不碰.

### 风暴周期性观察 (重要模式)
R2111 (02:45 CST, tier×10) → R2113 自愈 (tier=0) → R2116 再起 (03:45 CST, tier×28) → R2118 自愈 (tier=0) → **R2119 再起 (04:45 CST, tier×10, 进行中)**. **精确 ~1h 一波**, 每波 tier 429 0→爆发→自愈 0→再爆发. 若持续周期性复发且每波更猛, 需重新评估是否要动 KEY_COOLDOWN_S/TIER_COOLDOWN_S (当前 peer R2108 已调 60/180, cc2 不碰 peer 改的旋钮); 但**解冻指数退避仍不对症**.

## 验证
- 0 改动 0 restart, 无需 restart 后验证. 拉数据即验证: /health ok, docker ps ok (StartedAt 18:10:28Z 未漂移), env 未变.

## HM2 only. 不碰 HM1, 不碰 ms_gw(40007).
