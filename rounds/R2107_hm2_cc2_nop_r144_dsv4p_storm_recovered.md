# R2107 (hm2_cc2) — NOP 巡检 R144, 连续第 80 轮冻结; 重大状态变化记录 (nv_gw 02:10 重启 + peer R2082 改动生效 + 重启前 dsv4p 连环 429 风暴)

> 本轮 0 改动 0 restart (NOP 巡检)。但状态较 R2051 发生重大变化, 需详记供下一 session 接棒。

## 数据 (本 session 拉取, 当前 CST 2026-07-21 02:24)

### 30min 窗口 (CST 01:52-02:24)
- nv_gw 30min status: 200:59 / 502:102 / 429:11 → **SR = 59/172 = 34.3%** (断崖式暴跌 vs R2051 30min 95.07%)
- 30min error_type (status<>200): **all_tiers_exhausted×110** / zombie_empty_completion×1 → 主导是 all_tiers_exhausted (连环 429 穷尽)
- 30min request_model x status:
  - cc-glm5-2: 200:23 / 429:8 / 502:83 (SR ~21%, 主导失败 = 我自己的请求)
  - dsv4p_nv: 200:13 / 429:1 / 502:13 (SR ~48%)
  - glm5_2_nv: 200:29 / 502:1 (SR ~96.7%, 我自己直连链路健康)
- 30min 时间分桶 (CST): 01:52-02:10 大量 502/429 风暴期; **02:11-02:22 连续全 200 成功** (重启后恢复)
- **502 风暴窗口**: UTC 17:55:56 → 18:18:08 (CST 01:55-02:18), 跨 02:10 重启点; 重启前 (17:52-18:10) 风暴分布: cc-glm5-2 82×502+10×429 / dsv4p_nv 13×502+1×429 / glm5_2_nv 19×200+1×502 → **风暴主要打击 cc-glm5-2/dsv4p 映射, glm5_2_nv 直连受影响小**

### 重启后窗口 (StartedAt 2026-07-20T18:10:28Z 之后, 约 14min)
- status: 200:56 / 502:2 → **SR = 56/58 = 96.6%** (重启后已恢复健康, 远超 95% 稳态线)
- request_model: cc-glm5-2 27×200+1×502 / dsv4p_nv 18×200+1×502 / glm5_2_nv 11×200+0×502 (100%)
- error_type: all_tiers_exhausted×2 (重启后仅 2 条偶发, 非连环)
- → **重启已解决 dsv4p 连环 429 风暴, 当前 nv_gw 健康**

### 6h 窗口
- nv_gw 6h status: 200:247 / 502:1310 / 429:106 → SR = 247/1663 = **14.9%** (大窗被风暴期污染, 不代表当前)
- 6h error_type (status<>200): all_tiers_exhausted×1394 / zombie_empty_completion×16 / stream_absolute_cap×3 / stream_first_byte_timeout×3
- **abs_cap 6h=3 条 (时间: UTC 13:09/13:22/13:24, 即 CST 21:09-21:24, 全在 6h 窗最远端边界, 重启前风暴之前更早的偶发; 30min abs_cap=0 仍归零)** — 非 R1918 方案0 失效重现 (重启后 0), 只是远古偶发滚到 6h 窗边界
- **tier 上浮探测 6h=0 rows** (429/conn/Integrate/empty_200/noncycle 全在 tier retry 内吸收未上浮)

### tier 30min (重启后样本)
- pexec_success×26 / pexec_conn_RemoteDisconnected×5 / NVCFPexecRemoteDisconnected×2
- **已无 R2051 的 429_nv_rate_limit×22 / 429_integrate_rate_limit×12** → peer R2082 的 5 US 代理改动生效, 429 连环被压住

### fallback (cc4101 30min)
- **39 条 FALLBACK-OK** (vs R2051 = 11, +28; 风暴期 fallback 激增)
- **0 真中断** (grep "both failed|ms.*fail|UPSTREAM-ERROR-SEEN" = 0; 全 39 条被 ms_gw 救回)
- 细分: 多条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (cc4101 preempt 层) + **1 条 120107ms 跑满 chain budget 120s** (req=b4db8071 @02:20:41 重启后, glm5_2_nv 主路 120s ttfb 超时, 被 ms 救回 24690ms) — **120s 跑满类重启后再现 1 条** (R2051 说本轮 0 条已滚出, 本轮重启后再现), 单条偶发 ms 救回 0 失败, 不构成动 chain_budget 理由
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**

### breaker / BUG-A
- nv_gw 30min BREAKER (BREAKER-FAIL|OPEN|NV-ANTH-BREAKER-FAIL) = **0**; state CLOSED, 机制正常吸收非恶化
- **BUG-A SKIP-PEXEC2 30min 触发 5 次** (vs R2051 = 3, +2, 持续复活生效)

## 重大状态变化 (vs R2051)

1. **nv_gw StartedAt 漂移**: R2051 记 `2026-07-20T05:57:58Z` → 本轮 `2026-07-20T18:10:28Z` (UTC, = CST 2026-07-21 02:10:28). 漂移 ~12h, 是 **peer compose env 变更触发 up-d 重启** (docker events config-hash=c7385d0b 变, 非 cc2 改, 非 OOM: OOMKilled=false ExitCode=0). 这是 R2046 (03:02→05:57) 之后的第二次漂移.
2. **env 大幅变化** (peer R2082 + 其他改动, 非 cc2 改):
   - KEY_COOLDOWN_S: 25 → **60** (+35)
   - TIER_COOLDOWN_S: 25 → **180** (+155)
   - MIN_OUTBOUND_INTERVAL_S: 0 → **10** (+10, 强制请求间 10s 间隔, 影响 nv 流量密度)
   - 新增 NVU_PROXY_URL1-5 (7900-7904) + NVU_EGRESS_IP1-5 + NV_GLM52_RR_US_PROXIES (7894-7899) + NV_GLM52_MODE_CHAIN=integrate_us_rr,pexec_us_rr (peer R2082 的 dsv4p 5 独立 US socks5 + glm5_2 多 mode 链)
   - NVU_GLM52_EXP_BACKOFF **仍不在 env** = 关, 半成品冻结中 (符合)
3. **重启前 dsv4p 连环 429 风暴** (CST 01:52-02:10): all_tiers_exhausted 主导, cc-glm5-2/dsv4p 大量 502. **根因 = peer R2082 改动前的旧状态** (dsv4p pexec+DIRECT 单 IP → 5 key 连环 429 → 180s 全局 cooldown → all_tiers_exhausted). peer R2082 已改 5 US 代理解决, 02:10 重启后生效, 风暴消失.
4. **重启后 (02:10-02:24, 14min) nv_gw 健康**: SR 96.6%, glm5_2_nv 100%, 0 真中断, fallback 全兜住.

## 决策: NOP 巡检 (连续第 80 轮冻结), 0 改动

**不改的理由**:
1. **当前 nv_gw 健康** (重启后 14min SR 96.6%, glm5_2_nv 直连 100%, 远超 95% 稳态线).
2. **30min/6h 大窗 SR 暴跌是 peer R2082 改动前的 dsv4p 连环 429 风暴 + 重启前累积, 非我能修的网关旋钮** (根因是 NVCF 上游 dsv4p 单 IP 429, peer 已用 5 US 代理解决).
3. **env 已被 peer 大幅调整且正在生效** (KEY/TIER/MIN_OUTBOUND/5 US 代理), 我叠加改动会干扰 peer 的实验, 违反"聚焦 + 不碰别人正在跑的改动".
4. **铁律"改前必有数据"**: 数据显示当前健康 → 不需改. abs_cap 30min=0, breaker CLOSED, fallback 0 失败, BUG-A 持续触发.
5. **冻结理由 (连续第 78→80 轮) 仍成立**: 半成品 NVU_GLM52_EXP_BACKOFF 未 in-vivo 验证 + 激活需同步 3 组件 (chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key) + 24h 观测窗口, 风险/收益不对等.

## 验证

- `curl /health` = ok (proxy_role=passthrough, nv_num_keys=5, models=[kimi_nv,dsv4p_nv,glm5_2_nv], default=dsv4p_nv, port=40006)
- `docker ps`: nv_gw Up 15min (= 02:10 重启) / cc4101 Up 30h (StartedAt 12:10:22Z 未漂) / ms_gw Up 5h / logs_db Up 4 days
- `docker inspect nv_gw`: StartedAt 2026-07-20T18:10:28Z, OOMKilled=false, ExitCode=0, Status=running
- 0 改动 0 restart (本轮 NOP, 未动 compose/env/源码)

## 下一轮建议

- **继续 NOP 巡检 (R145, 连续第 81 轮冻结)**: 重点确认重启后稳态持续 (本轮重启后仅 14min 样本, 下一轮拉 30min 纯重启后数据看 SR 是否稳在 95%+).
- **关注 120s 跑满类 fallback**: 本轮重启后再现 1 条 (req=b4db8071 120107ms), 若持续增多并逼近 fallback 失败才考虑动 chain_budget; 当前 1 条 ms 救回 0 失败不需动.
- **关注 abs_cap**: 6h=3 条 (全在风暴前远古偶发, 30min=0 仍归零). 若 30min 再现 abs_cap>0 才需排查 R1918 方案0 是否失效.
- **关注 peer env 变化**: peer 仍在抢号 (R2082→R2106), HM2 nv_gw env 可能再被 peer 调 (KEY/TIER/MIN_OUTBOUND). 下一轮 docker inspect StartedAt + env 快照对比, 若再次漂移且非 cc2 改, 记录时间点.
- **nv_gw StartedAt 基线**: 本轮起对齐 `2026-07-20T18:10:28Z` (R2051 的 05:57:58Z 已失效). 下一轮核实是否再漂移.
- **轮号**: peer 已到 R2106; cc2 用 R2108+ hm2_cc2 前缀避撞号.

## 铁律遵守

- 改前必有数据 ✅ (30min/6h/重启后/tier/fallback/breaker/BUG-A 全拉)
- 改后必有验证 ✅ (NOP 无改动, /health + docker ps + StartedAt 核实)
- 聚焦 40006 ✅ (0 碰 40007/ms_gw 源码)
- 不碰 40007 ✅ (ms_gw 是重启窗口热备, 本轮 fallback 39 条全靠它兜住 0 失败)
- 写入仓库 ✅ (本 round file + commit push)
- 只改 HM2 ✅ (0 改动, peer 改 HM1 不关我事)
