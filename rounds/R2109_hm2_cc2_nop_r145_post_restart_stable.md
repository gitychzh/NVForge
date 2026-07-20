# R2109 (hm2_cc2) — NOP 巡检 R145, 连续第 81 轮冻结; 重启后稳态持续确认 (24min 窗口 SR 95.6%)

> 本轮 0 改动 0 restart (NOP 巡检)。接 R2107 (R144) 棒, 核实 02:10 peer 重启后稳态是否持续。
> STATE.md 比仓库落后 ~58 轮 (上次记到 R2051, 仓库已到 R2108), 本轮重新对齐真实 env + StartedAt。

## 数据 (本 session 拉取, 当前 CST 2026-07-21 02:34, UTC 18:34)

### 重启后窗口 (StartedAt 2026-07-20T18:10:28Z 之后, 约 24min)
- nv_gw status: 200:109 / 502:5 → **SR = 109/114 = 95.6%** (vs R2107 14min 窗口 96.6%, 样本翻倍后仍稳态, 远超 95% 稳态线)
- request_model x status:
  - **cc-glm5-2** (cc2 自己的请求映射): 200:50 / 502:3 → SR 50/53 = **94.3%**
  - **dsv4p_nv**: 200:31 / 502:2 → SR 31/33 = **93.9%**
  - **glm5_2_nv** (cc2 直连链路): 200:28 / 502:0 → SR 28/28 = **100%** ✅
- error_type (重启后 502): all_tiers_exhausted×4 / zombie_empty_completion×1 → **全 NVCF 上游已知类, 0 新可配置类**
- → **重启后稳态持续 24min, glm5_2_nv 直连 100%, peer R2082 的 5 US 代理改动持续生效**

### 30min 窗口 (CST 02:04-02:34, 含风暴尾段)
- nv_gw status: 200:99 / 502:31 / 429:3 → SR = 99/133 = **74.4%** (被风暴尾段污染, 不代表当前)
- 30min error_type (502): all_tiers_exhausted×31 / zombie_empty_completion×1
- 30min 502 时间分桶 (UTC, 区分重启前后):
  - **18:07-18:10Z (CST 02:07-02:10, 重启前风暴尾)**: 429×3 + 502×22 = 25 条 (dsv4p 连环 429 风暴最后 3 分钟)
  - **18:18-18:30Z (重启后)**: 502×5 (零星散落, 每分钟 1 条, 正常稳态水平)
- → 30min 的 31 条 502 里, 22 条是重启前风暴尾, 仅 5 条是重启后 24min 内偶发, **重启后真实 SR 95.6%**

### 6h 窗口 (大窗被风暴期污染, 不代表当前)
- nv_gw status: 200:267 / 502:1308 / 429:105 → SR = 267/1680 = **15.9%** (01:52-02:10 dsv4p 连环 429 风暴把 6h 大窗彻底污染, 非 nv_gw 当前状态)
- 6h error_type (502): all_tiers_exhausted×1386 / zombie_empty_completion×15 / stream_absolute_cap×3 / stream_first_byte_timeout×3
- → 6h 窗口已被风暴污染无参考价值, **以重启后 24min 窗口为准**

### abs_cap 探测 (严格带括号)
- **abs_cap 30min = 0** ✅ (仍归零)
- **abs_cap 重启后窗口 = 0** ✅
- abs_cap 6h = 3 条 (时间 UTC 13:11/13:24/13:27, 即 CST 7/20 21:11-21:27, **远早于 02:10 重启 ~7h, 风暴前远古偶发滚到 6h 窗边界**, 非 R1918 方案0 失效重现; 重启后 0 确认 cap_origin 重置持续生效)
- → abs_cap 当前仍归零, 无新恶化

### tier 30min / 重启后窗口
- tier 30min: pexec_success×22 / NVCFPexecRemoteDisconnected×5 / pexec_conn_RemoteDisconnected×3
- tier 重启后窗口: pexec_success×19 / NVCFPexecRemoteDisconnected×5 / pexec_conn_RemoteDisconnected×1
- **全 conn 类 (NVCFPexecRemoteDisconnected + pexec_conn_RemoteDisconnected) 在 tier retry 内吸收** (重启后 502 仅 5 条全 all_tiers_exhausted, 0 条 conn 上浮)
- **tier 上浮探测 (重启后 502 含 429/conn/Integrate/empty_200/noncycle) = 0 rows** ✅
- → R2051 的 429_nv_rate_limit×22 + 429_integrate_rate_limit×12 已消失 (peer R2082 5 US 代理压住 NVCF rate limit), tier 层干净

### fallback (cc4101 30min)
- **9 条 FALLBACK-OK** (vs R2107 = 39, -30; 风暴期 fallback 激增已消退, 回到正常水平)
- **0 真中断** (grep "both failed|ms.*fail|UPSTREAM-ERROR-SEEN" = 0; 全 9 条被 ms_gw 救回)
- 细分: 多条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (cc4101 preempt 层, 75s < chain budget 120s, NOT counted toward circuit) + **1 条 120107ms 跑满 chain budget 120s** (req=b4db8071 @02:20:41 重启后, glm5_2_nv 主路 120s ttfb 超时, 被 ms 救回 24690ms)
- → **120s 跑满类重启后仍偶现 1 条** (与 R2107 同一条 req=b4db8071 仍在 30min 窗口内未滚出), 单条偶发 ms 救回 0 失败, 不构成动 chain_budget 理由
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**

### breaker / BUG-A
- nv_gw 30min BREAKER (BREAKER-FAIL|OPEN|NV-ANTH-BREAKER-FAIL) = **0**; state CLOSED, 机制正常吸收非恶化
- **BUG-A SKIP-PEXEC2 30min 触发 7 次** (vs R2107 = 5, +2; vs R2051 = 3, +4; 持续高频复活生效, 机制真实运转)
- nv_gw 30min NV-ANTH-ZOMBIE 触发 1 次 (cc-glm5-2 anth zombie empty, fr=stop content=38c reasoning=0c, 软挂探测正常工作)

## 决策: NOP 巡检 (连续第 81 轮冻结), 0 改动

**不改的理由**:
1. **当前 nv_gw 健康** (重启后 24min SR 95.6%, glm5_2_nv 直连 100%, 远超 95% 稳态线; 比 R2107 的 14min 样本更长更可信).
2. **30min/6h 大窗 SR 暴跌是 peer R2082 改动前的 dsv4p 连环 429 风暴 + 重启前累积, 非我能修的网关旋钮** (根因是 NVCF 上游 dsv4p 单 IP 429, peer 已用 5 US 代理解决, 重启后生效持续).
3. **env 已被 peer 大幅调整且正在生效** (KEY_COOLDOWN 60 / TIER_COOLDOWN 180 / MIN_OUTBOUND 10 / 5 US socks5 代理 NVU_PROXY_URL1-5 / NVU_TIER_BUDGET_DSV4P_NV 180 / NVU_EMPTY_200_FASTBREAK 3 / NVU_PEXEC_TIMEOUT_FASTBREAK 3), 我叠加改动会干扰 peer 实验, 违反"聚焦 + 不碰别人正在跑的改动".
4. **铁律"改前必有数据"**: 数据显示当前健康 → 不需改. abs_cap 30min=0/重启后=0, breaker CLOSED, fallback 0 失败, BUG-A 持续高频触发.
5. **冻结理由 (连续第 78→81 轮) 仍成立**: 半成品 NVU_GLM52_EXP_BACKOFF 未 in-vivo 验证 (env 开关从未激活, 根本不在容器 env 中) + 激活需同步 3 组件 (chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现) + 24h 观测窗口, 风险/收益不对等.

## 验证

- `curl /health` = ok (proxy_role=passthrough, nv_num_keys=5, models=[kimi_nv,dsv4p_nv,glm5_2_nv], default=dsv4p_nv, port=40006)
- `docker ps`: nv_gw Up 22min (= 02:10 CST 重启) / cc4101 Up 30h (StartedAt 12:10:22Z 未漂) / ms_gw Up 5h / logs_db Up 4 days
- `docker inspect nv_gw`: StartedAt 2026-07-20T18:10:28Z (与 R2107 一致, **连续第 2 轮核实未再漂移**), Status=running
- 0 改动 0 restart (本轮 NOP, 未动 compose/env/源码)

## 当前 nv_gw env 快照 (docker exec env, 本轮核实)

```
KEY_COOLDOWN_S=60          (peer 改, R2051 时=25)
TIER_COOLDOWN_S=180        (peer 改, R2051 时=25)
MIN_OUTBOUND_INTERVAL_S=10 (peer 改, R2051 时=0)
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
NVU_TIER_BUDGET_DSV4P_NV=180  (peer 新增)
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_PROXY_URL1-5=socks5h://172.18.0.1:7900-7904  (peer R2082 新增, 5 US socks5)
NVU_EMPTY_200_FASTBREAK=3     (peer 新增)
NVU_PEXEC_TIMEOUT_FASTBREAK=3 (peer 新增)
NVU_GLM52_EXP_BACKOFF  (不在 env = 关, 半成品冻结中)
```

## 下一轮建议

- **继续 NOP 巡检 (R146, 连续第 82 轮冻结)**: 重点确认重启后稳态持续到 1h+ (本轮 24min 样本, 下一轮拉 30min 纯重启后数据看 SR 是否稳在 95%+ 且 glm5_2_nv 持续 100%).
- **关注 120s 跑满类 fallback**: 本轮仍 1 条 (req=b4db8071 120107ms 仍在 30min 窗口未滚出). 若持续增多并逼近 fallback 失败才考虑动 chain_budget; 当前 1 条 ms 救回 0 失败不需动.
- **关注 abs_cap**: 30min=0/重启后=0 仍归零. 若 30min 再现 abs_cap>0 才需排查 R1918 方案0 是否失效.
- **关注 peer env 变化**: peer 仍在抢号 (R2108 d19becc 改 HM1 FASTBREAK 1→2 + BUDGET_DSV4P_NV 20→48, 但那是 HM1 不碰 HM2). 下一轮 docker inspect StartedAt + env 快照对比, 若 HM2 nv_gw StartedAt 再次漂移且非 cc2 改, 记录时间点.
- **nv_gw StartedAt 基线**: 本轮起对齐 `2026-07-20T18:10:28Z` (R2107 已纠正, R2051 的 05:57:58Z 已失效). 下一轮核实是否再漂移.
- **轮号**: peer 已到 R2108 (HM1); cc2 用 R2110+ hm2_cc2 前缀避撞号.

## 铁律遵守

- 改前必有数据 ✅ (30min/6h/重启后24min/tier/fallback/breaker/BUG-A/abs_cap 全拉)
- 改后必有验证 ✅ (NOP 无改动, /health + docker ps + StartedAt 核实)
- 聚焦 40006 ✅ (0 碰 40007/ms_gw 源码)
- 不碰 40007 ✅ (ms_gw 是重启窗口热备, 本轮 fallback 9 条全靠它兜住 0 失败)
- 写入仓库 ✅ (本 round file + commit push)
- 只改 HM2 ✅ (0 改动, peer 改 HM1 不关我事)
