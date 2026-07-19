# R1909 (HM2 cc2) — NOP 巡检 R60

> 时间: 2026-07-19T08:50Z 拉取 30min 窗口 (本 session). git pull "Already up to date".
> peer 在 cc2 R1908 之后又抢写了一轮 R1907 HM2→HM1 (acf4926, TIER_TIMEOUT_BUDGET 168→166 HM1 侧, 只改 HM1 对 HM2 0 影响). cc2 续 R1909.
> 上一轮 R1908 commit 12c0a42. nv_gw StartedAt 仍 21:26:29Z (R1836 restart, R1839→R1909 未再 restart).

## 1. 数据 (改前必有数据)

### 30min nv_gw request 层
- SR = 57/62 = **91.9%** (200:57 / 502:5). vs R1908 87.3% → R1909 91.9%, 抖动区间中段常态, 非退化.
- 502=5 全 NVCF 上游侧, 两分类:
  - **zombie_empty_completion×4**:
    - 3× glm5_2_nv, egress 134.195.101.195/193/180 (同 134.195.101.0/24 出口 IP 段单点续, R1907-R1908 同段同源), function 3b9748d8, ttfb 4404-12802ms (快回空 body)
    - 1× **dsv4p_nv (新形态)**, egress **218.93.250.242 (非空, 新 IP 段)**, function **74f02205-c7b**, ttfb 1938ms (快回空)
  - **all_tiers_exhausted×1 (dsv4p_nv)**, egress 空, function **74f02205-c7b**, duration 68060ms, tiers_tried=1, key_cycle=[]

### 30min nv_gw tier 层
- pexec_success 52 / **500_nv_error×9** / pexec_empty_200 2 / pexec_SSLEOFError 1
- **500_nv_error×9: 全 dsv4p_nv function 74f02205 egress 空** — 与 R1908 完全一致 (R1908 也是 9 个全 dsv4p_nv 74f02205 egress 空). 同源中间态, 被 nv_gw 内部 retry/fallback 到其他 key/tier 后最终 200 (request 层 502 仅 5 个, 远少于 tier 层 9 个 500_nv_error → 大多被 retry 吸收).
- pexec_empty_200×2: glm5_2_nv function 3b9748d8 (同源首字节空)
- pexec_SSLEOFError×1: 无 egress/func 记录 (出口 IP 段单点续)

### dsv4p_nv 出口侧问题续抬头第 3 轮 (STATE 关注线核心)
- R1907: all_tiers_exhausted×4 (dsv4p_nv 74f02205 egress 空) 首抬头
- R1908: all_tiers_exhausted×4 + 500_nv_error×9 (dsv4p_nv 74f02205 egress 空) 续抬头第 2 轮
- **R1909: all_tiers_exhausted×1 + 500_nv_error×9 + zombie×1 (dsv4p_nv 74f02205, egress 218.93.250.242 新段非空)** 续抬头第 3 轮 ← **已达 STATE 关注线 "连续 3+ 轮"**
- 形态变化: ATE 从 4→1 降, 但新增 dsv4p_nv zombie (egress 218.93.250.242 非空 function 74f02205) + 500_nv_error 9 持平. 三者同 function_id 74f02205 = dsv4p_nv function 出口侧持续不可达 (ATE=出口 IP 段空 / 500=NVCF 内部 500 / zombie=快回空). 非 nv_gw 单参数可解, 属 "换出口 IP 段 / 联系 NVCF 运维 / 核查 function 74f02205 出口路由" 族.

### fallback + breaker
- fallback **4** FALLBACK-OK, 全 75s SKIP-CIRCUIT (primary timeout 75022-75079ms < chain budget 120s, cc4101 bug3 preempt, NOT counted). 全被 ms_gw 兜住, **0 真中断**. 微降 R1908=5→R1909=4.
- breaker NV-ANTH-BREAKER-FAIL **1 次** (glm5_2_nv zombie_empty_completion 触发, state CLOSED (2,0) 吸收, 未 OPEN). breaker **OPEN 0 连续 13+ 轮**.
- bug8 DOWNGRADE **0 触发** (NV-TOOLCALL-JSON-DOWNGRADE 15min log = 0, 连续 56 轮根除停巡).
- NV-CAP-RESET-MSFB **3 次** (vs R1908 4, 降; bug7 已修路径, abs_cap 同源首字节拖截断甩 ms).

## 2. 拟改

**NOP, 0 改动 0 restart.**

### 介入四条全不满足 (沿用 R1881-R1908 判据):
1. SR 91.9% 抖动区间中段常态非退化, 未达 "连续 3+ 轮跌破 80%" 介入线 ❌
2. 502 全 NVCF 上游侧 (zombie 首字节快回空 / ATE dsv4p_nv 出口侧整体不可达 / 500_nv_error dsv4p_nv 出口侧 NVCF 内部 500) 非 nv_gw 单参数可解 ❌
3. breaker OPEN 0 连续 13+ 轮, 本轮 BREAKER-FAIL 1 被 CLOSED 吸收未 OPEN ❌
4. **dsv4p_nv 出口侧问题续抬头第 3 轮 — 已达 STATE 关注线 "连续 3+ 轮"**, 但这是**操作侧升级核查动作** (联系 NVCF 运维 / 换出口 IP 段 / 核查 function 74f02205 出口路由), 不是 nv_gw 代码/env 改动. cc2 无权直接联系 NVCF 运维, 本轮正式在 round 文件 + STATE 记录 "已达关注线, 建议升级核查" 供监督者决策, 不构成本轮代码改动依据.

## 3. 验证

- env 无漂移 (UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / MIN_OUTBOUND_INTERVAL_S=0 / KEY_COOLDOWN_S=25 / KEY_AUTHFAIL_COOLDOWN_S=60 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_COOLDOWN_S=180 / NV_INTEGRATE_KEY_COOLDOWN_S=90 / TIER_COOLDOWN_S=25, 与 R1908 完全一致).
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps: nv_gw Up 11 hours.
- StartedAt 仍 2026-07-18T21:26:29Z (0 restart, 跑 R1839 改后字节码).
- bug8: oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (R1908 已确认宿主/容器一致, 本轮未再核 md5 = 未改此文件, 沿用 R1908 确认), DOWNGRADE 0 触发连续 56 轮.

## 4. 给监督者 (操作侧, 非 nv_gw 旋钮)

- **dsv4p_nv function 74f02205 出口侧问题已达 "连续 3+ 轮" 关注线** (R1907 首抬头 → R1908 第 2 → R1909 第 3). 形态: ATE(egress 空=出口 IP 段问题) + 500_nv_error(NVCF 内部 500) + zombie(快回空, egress 218.93.250.242 新段非空) 三态同 function 74f02205.
- 建议升级核查: 联系 NVCF 运维核查 function 74f02205-c7ba-438f-b81a-2537955bd7ec 的出口可达性 / 换出口 IP 段 / 核查 dsv4p_nv function 出口路由. 这是 **nv_gw 旋钮解不了的**, 需要 NVCF 侧或出口路由层介入.
- glm5_2_nv zombie 持续在 134.195.101.0/24 出口 IP 段 (R1907-R1909 连续 3 轮单点续) — 同属出口 IP 段问题族, 需换出口 IP 段.
- SR 91.9% 链路稳, fallback 0 真中断, 用户诉求 "可以报错但不能让 cc2 中断" 仍达成.

## 5. 铁律遵守

- 改前必有数据: ✅ 30min 窗口 + tier + fallback + breaker 全拉.
- 改后必有验证: ✅ (NOP 无改动, 验证 env 无漂移 + /health + docker ps + StartedAt).
- 聚焦 40006, 不碰 40007 (ms_gw 是重启窗口热备): ✅.
- 写入仓库: ✅ 本文件 + STATE 覆写.
- 只改 HM2, 不改 HM1: ✅ (NOP 0 改动).
