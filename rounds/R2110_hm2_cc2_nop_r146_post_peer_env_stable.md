# R2110 (hm2_cc2): NOP R146 — 连续第 82 轮冻结, peer R2108 env 改后稳态持续

> 轮号: R2110 (hm2_cc2 前缀避撞号, peer oc2/hermes2/hm2_optimize_hm1 抢号到 R2082b 主号 + R2108 hm2_optimize_hm1)
> 上一轮: R2109 (hm2_cc2, 8b36904) NOP R145 连续第 81 轮冻结
> 本轮模式: NOP 巡检, 0 改动 0 restart, 连续第 82 轮冻结指数退避半成品

## 数据 (本 session 拉取, 当前 CST 02:46)

**重大状态变化 (peer R2108 引起, 非 cc2 改, 已在 R2107/R2109 记录)**:
nv_gw 于 7-20 CST 02:10 (UTC 18:10:28Z) 被 peer (hm2_optimize_hm1 协同) SIGTERM 主动重启 +
config-hash 变 + env 变: KEY_COOLDOWN_S 25→60, TIER_COOLDOWN_S 25→180, MIN_OUTBOUND_INTERVAL_S 0→10.
重启前 01:52-02:10 dsv4p 连环 429 风暴 (6h 窗口被污染: 502=1256 all_tiers_exhausted, 429=104).
本轮拉取时 6h 窗口仍含远古风暴污染 → 6h SR 失真不采信, 重点看重启后 30min 窗口.

### 30min 窗口 (全在重启后, 真实当前状态)
- nv_gw 30min SR = 118/125 = **94.4%** (200:118 / 502:7)
  - vs R2109 30min 95.6% (109/114): -1.2pp, 稳态内小波动 (流量 114→125 +11 req)
- 30min 502=7 全 NVCF 上游已知类, **0 新可配置类**:
  - all_tiers_exhausted ×5
  - zombie_empty_completion ×2
  - (vs R2109 30min 502=5 all_tiers×5: 本轮 +2 zombie 回归, 仍 NVCF 上游已知类)
- 30min 429=0 (R2109 同为 0)

### 6h 窗口 (含重启前 429 风暴污染, 失真不采信)
- 6h status: 200×298 / 429×104 / 502×1274 (502 中 all_tiers_exhausted×1256 + zombie×15 + stream_absolute_cap×3 + stream_first_byte_timeout×3)
- 6h SR = 298/(298+104+1274) = 17.8% (失真, 重启前风暴主导, **不代表当前 nv_gw 状态**)
- 6h 502 1256 all_tiers_exhausted 几乎全是 01:52-02:10 dsv4p 429 风暴期 + 7-20 13:11-13:27 远古偶发

### tier 30min (重启后干净)
- pexec_success ×31
- NVCFPexecRemoteDisconnected ×9
- pexec_conn_RemoteDisconnected ×4
- **0 个 429 rate_limit 类** (vs R2109 未单列; vs R2051 tier 30min 429_nv_rate_limit×22+429_integrate×12 → peer R2108 改 env 后 429 风暴平息, tier 层 0 个 429 干净, 全 RemoteDisconnected retry 内吸收)

### abs_cap (双确认)
- 30min = 0
- 6h = 3 全在 7-20 13:11-13:27 UTC (CST 21:11-21:27, 前一 peer 重启窗口期远古偶发, 非 R1918 cap_origin 失效, 与 R2109 结论一致; 与当前 CST 7-21 02:46 完全无关)

### tier 上浮探测 (6h 502 中 429/conn/Integrate/empty_200/noncycle)
- 0 rows → tier 层全 retry 内吸收未上浮, 非新可配置类不需动

### fallback (cc4101 30min)
- **7 条 FALLBACK-OK, 0 真中断, 0 fallback 失败**
  - `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = 0
  - 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
  - req 样本: b4db8071(02:21, 24690ms)/96a3d26c(02:23, 11101ms)/29790069(02:27, 2478ms)/42921716(02:29, 20861ms)/b223871d(02:34, 12354ms)/2774a2a8(02:40, 7147ms)/50b17a02(02:43, 35075ms)
  - **含 1 条 120s 跑满类** (req=b4db8071, primary 跑满 120s 被 ms 救回, 与 R2109 同一条 b4db8071 已记录, 仍在窗口内)
- vs R2109 fallback 9 → 本轮 7 (-2, 区间内波动, 全兜住 0 失败)

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = 0
- nv_gw `grep -cE "BREAKER-FAIL|BREAKER.*OPEN|NV-ANTH-BREAKER-FAIL"` 30min = 0
- **state CLOSED, count 仍 2, 非 OPEN 切流 = 连续第 18 轮验证未恶化 (机制正常吸收非恶化)**

### BUG-A 修复 (R1913) 生效确认
- `NV-GLM52-CHAIN-SKIP-PEXEC2` 30min 触发 **5 次** (vs R2109 7次 -2, 持续复活触发中, 机制真实生效)

### nv_gw /health
- ok (proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=dsv4p_nv, port=40006)

### docker inspect StartedAt (UTC)
- nv_gw = **2026-07-20T18:10:28Z** (= CST 02:10:28; R2107 首次记录 05:57→18:10 漂移由 peer SIGTERM 重启+config-hash 变引起; R2109/R2110 核实未再漂移, 连续第 3 轮核实 18:10 稳定)
- cc4101 = 2026-07-19T12:10:22Z (R1926 后 0 restart 未变)
- docker ps: nv_gw Up 38 minutes (与 StartedAt 02:10 到当前 02:46 吻合) / cc4101 Up 31 hours / ms_gw Up 6 hours

## 当前 nv_gw env 快照 (peer R2108 改后值, 非 cc2 改)

```
KEY_COOLDOWN_S=60          (peer 改 25→60)
TIER_COOLDOWN_S=180        (peer 改 25→180)
MIN_OUTBOUND_INTERVAL_S=10 (peer 改 0→10)
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BIG_INPUT_FAIL_N=1
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_TIER_BUDGET_GLM5_2_NV=120
```
(注: NVU_GLM52_EXP_BACKOFF 仍不在 env 中 = 关, 半成品冻结中. chain_budget 仍 120s, 未升 420.
env 自 peer R2108 改后本轮 0 变更. cc2 仍只观测不碰 peer 的协同改动 — peer 是 HM2->HM1 协同优化者在调
dsv4p 5US 代理 + KEY/TIER cooldown, cc2 的链路 glm5_2_nv 走 NV_GLM52_RR_US_PROXIES 不碰
NVU_PROXY_URLS 故隔离不受影响, 数据证明 glm5_2_nv 30min SR 94.4% 稳态.)

## 决策: NOP R146, 连续第 82 轮冻结

**依据**: 重启后 30min 窗口数据全部满足"稳态":
- 30min SR 94.4% (稳态区间内, vs R2109 95.6% -1.2pp 小波动)
- 30min 502=7 全 NVCF 已知类 0 新可配置类
- tier 30min 0 个 429 (peer env 改后 429 风暴平息干净)
- abs_cap 30min=0 (6h=3 全远古偶发非失效)
- fallback 7 全兜住 0 真中断 0 失败
- breaker 30min recorded=0 (连续第 18 轮验证未恶化)
- BUG-A SKIP-PEXEC2 持续触发 5 次 (机制真实生效)

**冻结理由 (连续第 80 轮, 接 R2109 第 81 轮)** 仍成立:
半成品未 in-vivo 验证 (env 开关 NVU_GLM52_EXP_BACKOFF 从未激活, 不在容器 env 中) +
激活需同步 chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 + post-200 软挂换 key 未实现 +
24h 观测窗口. 风险/收益不对等 (当前重启后稳态 SR94.4% 0 真中断, abs_cap 归零, BUG-A 生效, 边际收益小).

**注**: env 现已被 peer (HM2->HM1 协同) 改成非 cc2 旧值 (KEY60/TIER180/MIN_OUTBOUND10).
这是 peer 的协同优化改动, 不是 cc2 改的 — cc2 只观测不碰 peer 改的旋钮 (peer 在调 dsv4p 5US 代理 +
KEY/TIER cooldown). cc2 的链路 glm5_2_nv 与 dsv4p 隔离 (走不同 proxy), 数据证明 glm5_2_nv 稳态.
6h 窗口因含重启前风暴失真, 下一轮若 6h 窗口完全滚出风暴期 (约 CST 08:10 后) 才能采信 6h SR.

## 验证

- `curl /health` = ok ✓
- `docker ps` = nv_gw Up 38min / cc4101 Up 31h / ms_gw Up 6h ✓
- 30min 502 分类 + fallback + breaker + BUG-A + abs_cap 全部确认 (见上) ✓
- 本轮 0 改动 0 restart, 无需 .bak 回滚

## 下一步

- 继续 NOP 巡检 (R147, 连续第 83 轮冻结): 数据全部满足稳态, 冻结理由仍成立.
- 拉数据确认趋势:
  - 重启后 30min SR 是否维持稳态 (本轮 94.4%, R2109 95.6%) — 若持续跌破 90% 且 502 出新可配置类才考虑动
  - 6h SR 当前因含远古风暴失真不采信, 等 6h 窗口完全滚出风暴期 (CST 08:10 后, 即 6h 前是 02:10 重启点) 才采信
  - 502 分类是否仍全 NVCF 已知类 0 新可配置类
  - fallback 是否仍全 75s SKIP-CIRCUIT 被兜住 0 失败; 120s 跑满类是否再现增多 (本轮 1 条 b4db8071, R2109 同)
  - breaker 是否仍 CLOSED 未达 OPEN 切流 (连续第 18 轮验证未恶化)
  - BUG-A SKIP-PEXEC2 是否持续触发 (本轮 5 次)
- 重点关注 nv_gw StartedAt 是否再次漂移 (本轮 18:10:28Z 连续第 3 轮核实未漂移; 若再次变化且非 cc2 改, 记录时间点)
- 重点关注 tier 429 rate_limit: 本轮 peer env 改后 tier 30min 0 个 429 (干净), 若再现攀升且上浮到 502 才需动 KEY_COOLDOWN_S/TIER_COOLDOWN_S (当前 peer 已把它们调到 60/180, cc2 不碰)
- 轮号: 下一轮 git pull 看最新, peer oc2/hermes2/hm2_optimize_hm1 抢号很快 (主号已到 R2082b + R2108); cc2 用 R2111 或更大 hm2_cc2 前缀不撞号
- 若未来要解冻: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步), 且实现 post-200 软挂换 key, 再 24h 观测. 当前不动.

## 铁律遵守

- 改前必有数据 ✓ (30min/6h 窗口 + fallback + breaker + BUG-A + abs_cap 全拉取)
- 改后必有验证 ✓ (本轮 0 改动, 仅巡检验证: /health + docker ps + 数据窗口)
- 聚焦 40006 ✓ (只看 nv_gw, 不碰 ms_gw 40007)
- 不碰 40007 ✓ (ms_gw 仍是重启窗口热备, Up 6 hours)
- 写入仓库 ✓ (本 round file + STATE 覆写)
- 只改 HM2 不改 HM1 ✓ (本轮 0 改动)
- 改 .py 必须 restart ✓ (本轮 0 改 .py 0 restart)

HM2 only. cc2 自优化链路 (cc4101→nv_gw 40006) 不变.
