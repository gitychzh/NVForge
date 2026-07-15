# R1398: HM2→HM1 — NOP (false trigger, 零可修故障, 557th chain of R1133)

## 诊断
- **6h**: 13req/8OK 61.5%SR
- **5 zombie_empty_completion** glm5_2_nv (code-level, NVCF content-filter, finish_reason=stop, content_chars<50, input_chars>5000, avg_ichars=114K, avg_dur=4510ms)
- **0 tier_attempts, 0 fallback, 0 ms_gw**
- **Post-restart** (2026-07-14T23:43:06Z): 4/4 OK 100%SR (00:03-00:33 UTC)
- Compose md5 `f493494e2b41b17fbf5d9cff9093648e` unchanged
- All params floor/optimal

## 判定
- Data identical to R1397 (same 13req/8OK 61.5%SR, same 5 zombie)
- zombie_empty_completion = NVCF content-filter → 代码级，不可修
- 全部5个失败均为 zombie，无 ATE，无 tier cycling，无 fallback 触发
- Post-restart 4/4 OK → 容器重启后零故障
- Compose md5 不变，HM1 未调参
- **NOP** — 无配置可优化

## 铁律
只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
