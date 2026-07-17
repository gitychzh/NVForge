# R1707 (HM2→HM1): NVU_PEXEC_TIMEOUT_FASTBREAK 2→1 (-1 key)

## 数据来源 (6h, HM1 DB, post-R1706)
- 总请求: 56 (全 glm5_2_nv, pexec_us_rr)
- OK: 44 (78.6% SR)
- Fail: 12 (全 zombie_empty_completion, NVCF content-filter, 不可修)
- ATE: 0
- Pexec timeout: 0
- SSLEOF: 0
- Fallback: 0
- OK路径: avg=10.9s, max=39.3s
- 1h窗口: 9req/6OK/3 zombie, avg_lat=13.5s
- 24h: 43 zombie + 5 ATE
- key_cycle_429s: 10 total in 1h (all 9 req had key_cycle=1, 正常轮转无429错误)
- Container: nv_gw Up 10min (healthy), 无漂移

## 分析
- 12 zombie 全为大输入 (>250k) glm5_2_nv NVCF content-filter — 非 config 可修
- 0 pexec timeout 在 6h 窗口 → FASTBREAK=2 提供零价值
- 所有 zombie 路径: EMPTY_200_FASTBREAK=1 已处理 (empty200→kill tier)
- FASTBREAK 管 pexec timeout，当前 regime 零 pexec timeout
- FASTBREAK=1=floor (R559-R694 136轮稳定), 省 66s/罕见 timeout
- 预算充足: TIER_BUDGET_GLM5_2=120, UPSTREAM=66, FASTBREAK=1 仍可容纳 k1 full

## 修改
- HM1: NVU_PEXEC_TIMEOUT_FASTBREAK: 2→1 (line 619, docker-compose.yml)
- 重启 nv_gw: `docker compose up -d nv_gw`
- 验证: `docker exec nv_gw env` → NVU_PEXEC_TIMEOUT_FASTBREAK=1 ✓
- 验证: `/health` → status=ok ✓
- 验证: `docker logs` → no errors ✓

## 验证
- Compose: `NVU_PEXEC_TIMEOUT_FASTBREAK: "1"` ✓
- Container env: `NVU_PEXEC_TIMEOUT_FASTBREAK=1` ✓
- 无容器漂移, 全参数匹配 ✓
- curl /health: status=ok ✓
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
