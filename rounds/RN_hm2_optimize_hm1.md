# R725: HM2→HM1 — 零变更轮（R724刚部署10min，NVCF 双 function 上游健康度问题，所有参数已达最优/地板，无需配置变更）

## TL;DR
R724 (NVU_FORCE_STREAM_UPGRADE_TIMEOUT 40→42) 部署仅10分钟，post-restart 11req/6OK(54.5%)/5ATE 样本过小。6h窗口 311req/203OK(65.3%)/108ATE(34.7%) 受 R710 FALLBACK_GRAPH 消失窗口 + NVCF 双 function 健康度下降双重影响。glm5_2_nv primary function 3b9748d8 health 0.0-0.25 极不稳定，dsv4p_nv primary 74f02205 1.0→0.667 持续下降。所有参数已达最优：UPSTREAM=42, FORCE_STREAM_UPGRADE=42, BUDGET=110, FASTBREAK=1, FALLBACK_HEALTH_THRESHOLD=0.10。FALLBACK_GRAPH 双向活跃，fallback 成功率 100% (55/55)。零变更。单参数每轮；铁律：只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2