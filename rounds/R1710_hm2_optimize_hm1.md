# R1710 (HM2→HM1): NOP — 零可修故障, 全参数 floor/optimal, 100% 429 双主机键争用

## 数据来源 (6h, HM1 DB, post-R1709)
- 总请求: 55 (全 glm5_2_nv, pexec_us_rr mode chain)
- OK: 43 (78.2% SR)
- Fail: 12 (全 zombie_empty_completion, NVCF content-filter >250k chars, 不可修)
- ATE: 0
- Pexec timeout: 0
- SSLEOF: 4 (tier_attempts pexec_SSLEOFError, 重试成功, 零影响)
- Fallback: 0 (peer-fb/ms_gw 均未触发)
- ms_gw: 0 req (零流量)
- OK路径: avg=10.9s, p50=9.3s, p95=18.4s, max=39.3s << 165
- **key_cycle_429s: 100% (55/55 req)** — 51 cycle=1, 4 cycle=2
- Zombie input: 全 280K-307K (>250K threshold), avg=6.5s/Zombie
- BIG_INPUT breaker: FAIL_N=3, COOLDOWN=60s — 已生效 (zombie 6-13s vs peer-fb 72s timeout)
- Compose: md5 不变, 无容器漂移

## 24h 扩展
- 153 req / 104 OK / 49 fail (68.0% SR)
- dsv4p_nv: 12/7 OK=58.3% (5 ATE all_tiers_exhausted, 24h仅12次流量)
- glm5_2_nv: 141/97 OK=68.8% (44 zombie, 0 ATE)
- 0 peer-fallback, 0 ms_gw relay
- 0 pexec timeout, 0 rate_limit

## 分析
- **零可修故障**: 12/12 zombie 全 NVCF content-filter (code-level), 非配置参数可修
- **0 ATE, 0 pexec timeout, 0 fallback** → 系统高度稳定, 无路径级故障
- **100% key_cycle_429s**: HM1+HM2 共享5个NV API key, 双主机并发请求产生键碰撞 → 单主机cooldown无法解决, 双主机架构固有特性
- **BIG_INPUT breaker 正确工作**: FAIL_N=3+COOLDOWN=60s, zombie 6-13s 远优于 peer-fb 72s timeout
- **OK路径零影响**: p50=9.3s, max=39.3s << 165s BUDGET
- **所有参数 floor/optimal**: KEY=70, TIER=70, UPSTREAM=66, EMPTY_200=1, PEXEC=1, SSLEOF=0.5, INTEGRATE=0, MIN_OUTBOUND=0, CONNECT=0, BUDGET=165
- **Budget 安全**: KEY+TIER=140<165, dsv4p+peer-fb=142<165, glm5_2+peer-fb=120+72=192>165 (但peer-fb未触发)
- **容器漂移**: 无, 全参数 compose 与 container env 一致

## 变更
- 零参数变更
- 零 compose 编辑
- 零容器重启
- 铁律: 只改HM1不改HM2 ✓

## 验证
- Compose: `TIER_TIMEOUT_BUDGET_S: "165"`, `KEY_COOLDOWN_S: "70"`, `TIER_COOLDOWN_S: "70"` ✓
- Container env: 全参数与 compose 一致 ✓
- curl /health: status=ok ✓
- docker logs: 零 error/warn ✓
- DB: 0 ATE, 0 pexec timeout, 0 fallback ✓
## ⏳ 轮到HM1优化HM2
