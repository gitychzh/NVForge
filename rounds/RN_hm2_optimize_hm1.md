# R717: HM2→HM1 — 零变更轮（NVCF dsv4p_nv primary function 74f02205 死亡→自动切换 8915fd28，无需配置变更）

## TL;DR
dsv4p_nv primary NVCF function `74f02205` dead (health=0.0) for entire 6h window. NVCF auto-switched to new function `8915fd28` at ~08:22 UTC. Fallback chain working (NV-FALLBACK-SUCCESS since 08:23). All existing params are optimal — UPSTREAM_TIMEOUT=40 not binding, FASTBREAK=1, BUDGET=110 per-tier safe. Zero-change round. Single param per round policy; iron rule: only change HM1 never HM2.

## ⏳ 轮到HM1优化HM2