# R113: HM2→HM1 — MIN_OUTBOUND_INTERVAL_S 20→22 (+2s)

**Date**: 2026-06-27 20:44 UTC
**Author**: opc2_uname (HM2)
**Target**: HM1 (opc_uname)
**Principles**: 更少报错, 更快请求, 超低延迟, 稳定优先
**Iron Law**: 只改HM1不改HM2

---

## 📊 Data Collection Summary (post-R112)

- **30min**: 58/58 (100% success), p50=19.7s, p90=42.9s, p95=60.7s
- **1h**: deepseek_hm_nv 1247 ok / 3 fail (99.8%), 2 all_tiers_exhausted (127-130s)
- **Key errors (24h)**: NVCFPexecTimeout dominant (21-27 per key), empty_200 (2-8 per key), budget_exhausted_after_connect (1-2 per key, avg 0.7-3.2s), 0 deepseek 429s
- **Docker logs**: 完全干净, 0 错误在最近100行

## 🎯 Analysis

- 30min 100% 成功 — 系统极稳定, R112 (BUDGET=136) 后 0 失败
- NVCFPexecTimeout (21-27/键/24h) 是 NVCF 基础设施超时, HM 不直接可控
- 但: 更宽出站间隔 → 更少并发 NVCFPexecTimeout 重叠 → 更少 all_tiers_exhausted
- 请求频率仅 1.9/min, 22s 间隔不影响吞吐
- 选择 MIN_OUTBOUND_INTERVAL_S +2s: 预防性稳定, 非紧急修复

## 🔧 Change

- MIN_OUTBOUND_INTERVAL_S: 20.0 → 22.0 (+2s)
- Deployed via `docker compose up -d hm40006`
- Verified: env=22.0, container healthy, first request k2 succeeded in 9.3s

## 📈 Expected

- 30min failure rate: 0% → maintain 0%
- all_tiers_exhausted/1h: 2 → ≤2
- Concurrent timeout overlap: reduced (wider spacing)

## ⚖️ Judgment

- 更少报错 / 更快请求 / 超低延迟 / 稳定优先 ✅
- 铁律: 只改HM1不改HM2 ✅

## ⏳ 轮到HM1优化HM2