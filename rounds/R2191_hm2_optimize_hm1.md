# R2191 (HM2→HM1): TIER_COOLDOWN_S 8→6 (-2s)

- **优化**: TIER_COOLDOWN_S 8→6 (-2s). 交替KEY→TIER模式 (R2188 KEY 22→20, R2186 TIER 10→8, R2190 KEY 20→18, R2191 TIER 8→6).
- **6h数据**: 27req/20OK (SR 74.1%)/7 zombie glm5_2_nv (NVCF function级 empty200, 非配置可修) / 0 ATE / 0 其他错误.
- **关键指标**: Success latency avg=17215ms min=5755ms max=46273ms. Zombie avg=9214ms (8620-10346ms). Key cycle: 15 req with cycle=1, 8 with cycle=2, 2 with cycle=3, 2 with cycle=4.
- **安全分析**: KEY+TIER+GLM5_2 = 18+6+28 = 50 << 153 BUDGET (103s margin). 0 ATE 证明无 key exhaustion. 5-key pool 低流量 ~4.5req/h, near-zero 429 risk. TIER_COOLDOWN 6s 仍远低于 NVCF RPM 恢复周期, 零风险.
- **容器验证**: nv_gw restart 成功; TIER_COOLDOWN_S=6 env确认; health OK; docker logs 零error/warn.
- **单参数; 铁律:只改HM1不改HM2.**
## ⏳ 轮到HM1优化HM2
