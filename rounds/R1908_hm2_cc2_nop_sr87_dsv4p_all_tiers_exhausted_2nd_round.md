# R1908 (HM2 cc2): NOP 巡检 R59 — SR 87.3% 回升常态, dsv4p_nv 出口侧 all_tiers_exhausted 续抬头第 2 轮 (未达介入线)

> 铁律: 改前必有数据, 改后必有验证, 聚焦 40006, 不碰 40007 (重启窗口热备), 写入仓库, 改 .py 必须 restart。
> 本轮 0 改动 0 restart (NOP 巡检)。单参数铁律: 只改 HM2, 不碰 ms_gw, 不碰 HM1。

## 1. 数据 (改前必有数据, 本 session ~16:30 拉取, 30min 窗口)

### nv_gw request 层 30min
- status: 200×48 / 502×7 → **SR = 48/55 = 87.3%** (vs R1907 80.0% 回升, 抖动区间中段常态非退化)。
- 502=7 三分类 (全 NVCF 上游侧):
  1. **all_tiers_exhausted×4 (dsv4p_nv)** — **续抬头第 2 轮** (R1907 首抬头 4 条 → R1908 续 4 条)。
     全 dsv4p_nv tier, egress_ip 全空, function_id 全=74f02205-c7ba-438f-b81a-2537955bd7ec,
     duration 70018-129936ms (一条 130s 突出上升, 其余 ~70s 仍在 UPSTREAM_TIMEOUT 66s 上沿附近),
     tiers_tried_count=1, key_cycle_details=[] 空 → dsv4p_nv function 74f02205 在 NVCF 出口侧整体不可达
     (egress 空 = 出口 IP 段问题)。非 nv_gw 单参数可解, 属"换出口 IP 段 / 联系 NVCF 运维 / 核查 function 出口路由"族。
  2. **zombie_empty_completion×2 (glm5_2_nv)** — ttfb 2.4-2.7s 快回空 body, egress 134.195.101.193/.195
     同 134.195.101.0/24 出口 IP 段单点续 (R1907 同段同源)。
  3. **stream_absolute_cap×1 (glm5_2_nv)** — abs_cap 同源首字节慢/空 (NVCF empty200 上游侧)。request 层查询
     返回 0 行 (记在别字段), 但 error_type 计数确为 1, 与 R1907 同族。

### nv_gw tier 层 30min (nv_tier_attempts)
- pexec_success 41 / **500_nv_error×9 (本轮新抬头, 全 dsv4p_nv, 同 function_id 74f02205, egress 全空)** /
  pexec_empty_200 4 / pexec_SSLEOFError 1 / pexec_timeout 1。
- **500_nv_error×9 dsv4p_nv 与 all_tiers_exhausted(dsv4p_nv) 同 function_id 74f02205 + 同 egress 空 = 同源**
  (dsv4p_nv 74f02205 出口侧 NVCF 内部 500 错误)。这 9 个 tier attempt 是**中间态**: 被 nv_gw 内部 fallback/retry
  到其他 key/tier 后最终 200 (request 层 502 仅 7 个, 远少于 tier 层 9 个 500_nv_error → 大多被 retry 吸收)。
  非新可配置类, 属 dsv4p_nv 出口侧问题的不同错误形态, 同 all_tiers_exhausted 族。

### fallback (负向核心指标) 30min
- **5 FALLBACK-OK 全 75s SKIP-CIRCUIT** (primary timeout 75022-75079ms < chain budget 120s, cc4101 bug3 preempt,
  NOT counted toward circuit, 非 nv_gw 旋钮可解)。全被 ms_gw(40007) 兜住, **0 真中断** (用户诉求 "可以报错但不能让 cc2 中断" 仍达成)。
- 抬头持平微降 (R1907=7 → R1908=5)。

### breaker / cap reset / bug8 30min
- NV-ANTH-BREAKER-FAIL **0 次** (vs R1907 2, 回落)。
- breaker **OPEN 0** (连续 12+ 轮)。
- NV-CAP-RESET-MSFB **4 次** (vs R1907 6, 降; bug7 已修路径, abs_cap 同源首字节拖截断甩 ms)。
- bug8 NV-TOOLCALL-JSON-DOWNGRADE **0 触发** (连续 55 轮根除停巡)。

## 2. 拟改 / 预期

**NOP 无据不改**。介入四条全不满足:
1. SR 87.3% 回升至抖动区间中段常态, **非退化**, 未达"连续 3+ 轮跌破 80%"介入线。
2. 502=7 全 NVCF 上游侧 (all_tiers_exhausted dsv4p_nv 出口侧整体不可达 / zombie+abs_cap glm5_2_nv 首字节慢/空),
   非新可配置类。
3. breaker OPEN 0 (连续 12+ 轮), 本轮甚至连 BREAKER-FAIL 都是 0。
4. **all_tiers_exhausted (dsv4p_nv) 续抬头第 2 轮** — STATE 关注线是"连续 3+ 轮续抬头才升级核查",
   当前第 2 轮**未达介入线**。500_nv_error×9 dsv4p_nv 新抬头但同 function_id/egress 空 = 同源 dsv4p_nv
   出口侧问题的中间态, 被 retry 吸收, 不构成新可配置类介入依据。

## 3. 验证 (本轮 0 改动 0 restart, 仅健康确认)

- env 无漂移, 与 R1907 快照完全一致 (UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / MIN_OUTBOUND=0 /
  KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_COOLDOWN=180 /
  NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25)。
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv)。
- docker ps 全 Up; StartedAt 仍 2026-07-18T21:26:29Z (R1836 restart, R1839→R1908 未再 restart → 跑改后字节码)。

## 4. 给监督者方向

- **all_tiers_exhausted (dsv4p_nv) 续抬头第 2 轮 + 500_nv_error×9 dsv4p_nv 同源新抬头**:
  两者同 function_id 74f02205 + 同 egress_ip 空 = dsv4p_nv function 在 NVCF 出口侧整体不可达 (egress 空 = 出口 IP 段问题),
  且出现 NVCF 内部 500 错误 (500_nv_error)。**若 R1909 续抬头 (即连续 3+ 轮)**, 说明 dsv4p_nv function 74f02205
  出口路由持续不可达, 应**升级核查 dsv4p_nv function 的 NVCF 出口可达性** (联系 NVCF 运维 / 换出口 IP 段), 非 nv_gw 旋钮可解。
- 沿用 R1881-R1907: abs_cap/zombie/empty200/all_tiers_exhausted/500_nv_error 同源首字节慢/空/出口侧不可达是
  NVCF 上游侧 + 出口 IP 段 (134.195.101.0/24 zombie 单点续; dsv4p_nv 74f02205 出口 egress 空),
  需换出口 IP 段 / 联系 NVCF 运维 / 核查 dsv4p_nv function 出口路由, 非 nv_gw 单参数可解。

## 5. 结论

NOP 巡检 R59 完成。SR 87.3% 回升常态, 502 全 NVCF 上游侧, breaker OPEN 0 连续 12+ 轮, bug8 0 触发连续 55 轮根除停巡,
fallback 5 全 SKIP-CIRCUIT 0 真中断。**dsv4p_nv 出口侧问题 (all_tiers_exhausted + 500_nv_error 同 function_id 74f02205 egress 空)
续抬头第 2 轮, 距 STATE 关注线"连续 3+ 轮"差 1 轮** — 下一轮重点观察是否续抬头达介入线, 达则升级核查 dsv4p_nv function 出口路由。

单参数铁律: 只改 HM2 不碰 ms_gw 不碰 HM1。
