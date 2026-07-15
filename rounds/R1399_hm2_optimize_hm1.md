# R1399: HM2→HM1 — NOP (false trigger, 零可修故障, 558th chain of R1133)

## 诊断
- **6h**: 9req/8OK 88.9%SR
- **1 zombie_empty_completion** glm5_2_nv (code-level, NVCF content-filter, finish_reason=stop, content_chars=12, input_chars=206K, dur=5418ms)
- **0 tier_attempts, 0 ATE, 0 fallback, 0 ms_gw**
- **Post-restart** (2026-07-14T23:43:06Z): 4/4 OK 100%SR (00:00-00:33 UTC)
- **Pre-restart**: 5req/4OK (1 zombie at 19:33 UTC)
- Compose md5 `f493494e2b41b17fbf5d9cff9093648e` unchanged
- All params floor/optimal: UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, MIN_OUTBOUND_INTERVAL_S=0, TIER_TIMEOUT_BUDGET_S=205, FASTBREAK=1/1/2, BUDGET_PER_MODEL dsv4p=106/glm5_2=96/minimax=100

## 判定
- zombie_empty_completion = NVCF content-filter → 代码级，不可修
- 唯一失败为 zombie，无 ATE，无 tier cycling，无 fallback 触发
- Post-restart 4/4 OK → 容器重启后零故障
- Compose md5 不变，HM1 未调参
- 所有参数已在 floor/optimal — 无优化空间
- **NOP** — 无配置可优化

## 铁律
只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
