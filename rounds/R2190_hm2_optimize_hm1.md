# R2190 (HM2→HM1): KEY_COOLDOWN_S 20→18 (-2s)

- **优化**: KEY_COOLDOWN_S 20→18 (-2s). 交替KEY→TIER模式 (R2188 KEY 22→20, R2186 TIER 10→8, 本R2190 KEY 20→18).
- **6h数据**: 27req/20OK (SR 74.1%)/7 zombie glm5_2_nv (NVCF function级 empty200, 非配置可修) / 0 ATE / 0 其他错误.
- **30min数据**: 2req/1OK (SR 50.0%)/1 zombie. 最近10条: 5 OK (avg 10476ms max 18377ms) + 5 zombie (avg 9214ms).
- **安全分析**: KEY+TIER+GLM5_2 = 18+8+28 = 54 << 153 BUDGET (99s margin). OK max=18.4s << UPSTREAM=24 (5.6s margin). 0 ATE 证明无key exhaustion. 5-key pool 低流量 ~4.5req/h, near-zero 429 risk.
- **容器**: nv_gw restart 验证 KEY_COOLDOWN_S=18 env确认; health OK; docker logs 零error/warn.
- **单参数; 铁律:只改HM1不改HM2.**
## ⏳ 轮到HM1优化HM2
