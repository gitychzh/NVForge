# R1906 (HM2 cc2) — NOP 巡检 R57

> 模式: nv 直连 (cc4101→nv_gw). bug8 真降级兜底 R1839 in-vivo 后第 53 轮巡检.
> NOP 0 改动 0 restart. 介入四条全不满足.

## 数据 (30min 窗口, 本 session 拉取 ~16:10)

- nv_gw 30min status: **200:31 / 502:7 → SR = 31/38 = 81.6%**
  (抖动区间下沿常态. R1902 96.36% → R1904 100% → R1905 97.5% → R1906 81.6% 抖动,
   abs_cap/zombie 在 NVCF empty200 上游侧来回切, 同源首字节慢/空, 非我旋钮可解)
- 502=7 全 NVCF 上游侧. tier 30min error_type 分类:
  - pexec_success 24 / pexec_empty_200 4 (NVCF 首字节空 200 老面庞) /
    pexec_timeout 2 / IntegrateTimeout 1 / pexec_SSLEOFError 1 (出口 IP 段 134.195.101.0/24 同源单点续)
- fallback (cc4101 30min): **8 FALLBACK-OK, 7 条是 75s SKIP-CIRCUIT**
  (primary timeout status=0 after 75000-75083ms < chain budget 120s,
   cc4101 pre-empted nv_gw retry, NOT counted toward circuit).
  全被 ms_gw 兜住, **0 真中断** (用户诉求"可报错但不中断"达成).
  SKIP-CIRCUIT 抬头持平 R1902=7→R1904=7→R1905=7→R1906=7, 是 cc4101 bug3 preempt 非 nv_gw 旋钮可解.
- breaker: NV-ANTH-BREAKER-FAIL 2 次 (state CLOSED,2,0 吸收未 OPEN 设计内吸收态).
  breaker **OPEN 0 连续 10+ 轮**.
- bug8: NV-TOOLCALL-JSON-DOWNGRADE **0 触发** (连续 53 轮根除, 已停巡).
- NV-CAP-RESET-MSFB 5 次 (bug7 已修路径正常工作, abs_cap 同源首字节拖 242-268s 截断甩 ms).

## env 快照 (无漂移)

```
UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / MIN_OUTBOUND_INTERVAL_S=0 /
KEY_COOLDOWN_S=25 / TIER_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1 /
NVU_BIG_INPUT_COOLDOWN_S=180 / NV_INTEGRATE_KEY_COOLDOWN_S=90 / KEY_AUTHFAIL_COOLDOWN_S=60
```
nv_gw StartedAt = 2026-07-18T21:26:29Z (R1836 restart, R1839→R1906 未再 restart, 跑改后字节码).
/health ok. docker ps 全 Up (nv_gw 11h / cc4101 24h / ms_gw 2d / logs_db 2d).

## 介入四条全不满足 → NOP 无据不改

1. SR81.6 抖动区间常态非退化 (上沿 100% 下沿 80% 长期确认)
2. 非跳过类失败 0 < 4 (SKIP-CIRCUIT 不计入)
3. breaker OPEN 0 连续 10+ 轮
4. 无新可配置 error 分类

## 给监��者

沿用 R1881-R1905 建议: abs_cap/zombie/empty200 同源首字节慢/空是 NVCF 上游侧 + 出口 IP 段问题,
非 nv_gw 单参数可解. 可考虑方向: 换出口 IP 段 / 联系 NVCF 运维. SKIP-CIRCUIT 75s 抬头是 cc4101 bug3
preempt 层, 非 nv_gw 旋钮.

## 铁律

只改 HM2, 不碰 ms_gw (40007 是 restart 热备). 单参数铁律遵守. 改前必有数据改后必有验证.
