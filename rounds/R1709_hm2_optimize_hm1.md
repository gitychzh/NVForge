# R1709 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 170→165 (-5s)

## 数据来源 (6h, HM1 DB, post-R1708)
- 总请求: 55 (全 glm5_2_nv, pexec_us_rr)
- OK: 43 (78.2% SR)
- Fail: 12 (全 zombie_empty_completion, NVCF content-filter >250k, 不可修)
- ATE: 0
- Pexec timeout: 0
- SSLEOF: 4 (tier_attempts, 重试成功)
- Fallback: 0
- OK路径: avg=10.9s, p50=9.3s, p95=18.4s, max=39.3s
- **key_cycle_429s: 100% (55/55 req)** — 51 cycle=1, 4 cycle=2
- Tier attempts: 55 pexec_success, 4 pexec_SSLEOFError
- Container: nv_gw healthy, 无漂移

## 分析
- R1708 KEY_COOLDOWN=70 仍未能消除 key_cycle_429s (100% 持续)
- HM1+HM2 共享5个NV API key → 双主机并发请求产生key碰撞 → 单主机cooldown无法解决
- Key collision是双主机架构固有特性，非预算/cooldown可修
- 0 ATE, 0 pexec timeout, 0 fallback → 系统高度稳定
- OK路径 max=39.3s << 165s → 安全余量充足
- KEY+TIER=140 < 165 (25s headroom) ✓
- dsv4p+peer-fb=70+72=142 < 165 ✓
- -5s 压缩理论失败路径，成功路径零影响

## 修改
- HM1: TIER_TIMEOUT_BUDGET_S: 170→165 (-5s)
- 重启 nv_gw: `docker compose up -d nv_gw`
- 验证: `docker exec nv_gw env` → TIER_TIMEOUT_BUDGET_S=165 ✓
- 验证: `/health` → status=ok ✓
- 验证: `docker logs` → clean startup, no errors ✓

## 验证
- Compose: `TIER_TIMEOUT_BUDGET_S: "165"` ✓
- Container env: `TIER_TIMEOUT_BUDGET_S=165` ✓
- 无容器漂移，全参数匹配:
  - KEY_COOLDOWN_S=70, TIER_COOLDOWN_S=70 ✓
  - UPSTREAM_TIMEOUT=66, MIN_OUTBOUND=0 ✓
  - NVU_EMPTY_200_FASTBREAK=1, NVU_PEXEC_TIMEOUT_FASTBREAK=1 ✓
  - NVU_SSLEOF_RETRY_DELAY_S=0.5, NVU_BIG_INPUT_FAIL_N=3 ✓
  - NVU_STREAM_TOTAL_DEADLINE_S=30, NVU_STREAM_FIRST_BYTE_DEADLINE_S=20 ✓
- curl /health: status=ok ✓
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
