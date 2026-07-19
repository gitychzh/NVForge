# R1907 (HM2 cc2) — NOP 巡检 R58

> 模式: nv 直连 (cc4101→nv_gw). bug8 真降级兜底 R1839 in-vivo 后第 54 轮巡检.
> NOP 0 改动 0 restart. 介入四条全不满足.

## 数据 (30min 窗口, 本 session 拉取 ~16:13)

- nv_gw 30min status: **200:32 / 502:8 → SR = 32/40 = 80.0%**
  (抖动区间下沿常态. R1902 96.36% → R1904 100% → R1905 97.5% → R1906 81.6% → R1907 80.0% 抖动,
   抖动区间下沿持平, 非退化趋势 — dsv4p_nv all_tiers_exhausted 是本轮新出现的上游侧现象)
- 502=8 全 NVCF 上游侧. 分类:
  - **all_tiers_exhausted 4 (dsv4p_nv)** — 新分类抬头 (R1902-R1906 未见).
    4 条全 dsv4p_nv mapped_tier, egress_ip 全空, duration ~70s (接近 UPSTREAM_TIMEOUT 66s 上沿),
    tiers_tried_count=1, key_cycle_details=[] (空) → 表示 dsv4p_nv tier 在 NVCF 侧整体连不上出口,
    非 nv_gw 旋钮可解 (egress 空 = 出口 IP 段问题, 同 R1881-R1906 给监督者方向 "换出口 IP 段 / 联系 NVCF 运维").
  - **stream_absolute_cap 2 (glm5_2_nv)** — abs_cap 同源首字节慢/空 (ttfb 152-168s, 超长首字节拖,
    NVCF empty200 上游侧, R1905 abs_cap 1 → R1907 abs_cap 2 延续)
  - **zombie_empty_completion 2 (glm5_2_nv)** — zombie 老 NVCF 首字节空 (ttfb 2.4-2.7s 快回但空 body,
    egress_ip 134.195.101.195/193 同 134.195.101.0/24 出口 IP 段单点续)
- tier 30min error_type: pexec_success 25 / pexec_empty_200 4 / pexec_timeout 2 / IntegrateTimeout 1
  (本轮 pexec_SSLEOFError 0, R1905-R1906 单点续本轮回落 0)
- fallback (cc4101 30min): **7 FALLBACK-OK, 7 条全 75s SKIP-CIRCUIT**
  (primary timeout status=0 after 75025-75083ms < chain budget 120s,
   cc4101 pre-empted nv_gw retry, NOT counted toward circuit).
  全被 ms_gw 兜住, **0 真中断** (用户诉求"可报错但不中断"达成).
  SKIP-CIRCUIT 抬头持平 R1902=7→R1906=7→R1907=7, 是 cc4101 bug3 preempt 非 nv_gw 旋钮可解.
- breaker: NV-ANTH-BREAKER-FAIL 2 次 (state CLOSED,2,0 吸收未 OPEN 设计内吸收态,
  对应 502 stream_absolute_cap 2 条). breaker **OPEN 0 连续 11+ 轮**.
- bug8: NV-TOOLCALL-JSON-DOWNGRADE **0 触发** (连续 54 轮根除, 已停巡).
- NV-CAP-RESET-MSFB 6 次 (bug7 已修路径正常工作, abs_cap 同源首字节拖截断甩 ms, 抬头续 R1905=6→R1907=6).

## env 快照 (无漂移)

```
UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / MIN_OUTBOUND_INTERVAL_S=0 /
KEY_COOLDOWN_S=25 / TIER_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1 /
NVU_BIG_INPUT_COOLDOWN_S=180 / NV_INTEGRATE_KEY_COOLDOWN_S=90 / KEY_AUTHFAIL_COOLDOWN_S=60
```
nv_gw StartedAt = 2026-07-18T21:26:29Z (R1836 restart, R1839→R1907 未再 restart, 跑改后字节码).
/health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv). docker ps 全 Up (nv_gw 11h / cc4101 24h / ms_gw 2d / logs_db 2d).

## 介入四条全不满足 → NOP 无据不改

1. SR80.0 抖动区间下沿常态非退化 (R1906=81.6→R1907=80.0 持平下沿, 仅 1 轮未达"连续 3+ 轮跌破 80%"介入线)
2. 非跳过类失败: 502=8 中 all_tiers_exhausted 4 + abs_cap 2 + zombie 2, 但全部 NVCF 上游侧
   (dsv4p_nv tier 连不上出口 egress 空 / glm5_2_nv 首字节慢/空), 非 nv_gw 单参数可解 — 不属"新可配置类"
3. breaker OPEN 0 连续 11+ 轮
4. all_tiers_exhausted (dsv4p_nv) 虽本轮新抬头, 但其特征 (egress_ip 全空 + key_cycle 空 + duration~70s)
   = NVCF dsv4p_nv tier 在出口侧整体不可达, 与现有 abs_cap/zombie 同属"NVCF 上游侧 + 出口 IP 段"问题族,
   非新增 nv_gw 可旋钮分类. 需观察是否连续多轮续抬头再判, 当前 1 轮不构成介入依据.

## 给监督者

沿用 R1881-R1906 建议: abs_cap/zombie/empty200/all_tiers_exhausted 同源 NVCF 上游侧 + 出口 IP 段问题
(dsv4p_nv tier 本轮 egress 空 = 出口侧整体不可达; glm5_2_nv abs_cap 首字节拖 + zombie 134.195.101.0/24 单点续),
非 nv_gw 单参数可解. 可考虑方向: 换出口 IP 段 / 联系 NVCF 运维 / 核查 dsv4p_nv function 出口可达性.
SKIP-CIRCUIT 75s 抬头是 cc4101 bug3 preempt 层, 非 nv_gw 旋钮.
**注意监控**: all_tiers_exhausted (dsv4p_nv) 若连续 3+ 轮续抬头, 说明 dsv4p_nv 出口持续不可达,
应升级核查 dsv4p_nv function_id 的 NVCF 出口路由 (本轮 4 条全 function_id=74f02205...).

## 铁律

只改 HM2, 不碰 ms_gw (40007 是 restart 热备). 单参数铁律遵守. 改前必有数据改后必有验证.
