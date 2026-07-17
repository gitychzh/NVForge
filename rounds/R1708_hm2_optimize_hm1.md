# R1708 (HM2→HM1): KEY_COOLDOWN_S 65→70, TIER_COOLDOWN_S 65→70 (+5s each)

## 数据来源 (6h, HM1 DB, post-R1707)
- 总请求: 56 (全 glm5_2_nv, pexec_us_rr)
- OK: 44 (78.6% SR)
- Fail: 12 (全 zombie_empty_completion, NVCF content-filter, 不可修)
- ATE: 0
- Pexec timeout: 0
- SSLEOF: 3 (tier_attempts, 重试成功)
- Fallback: 0
- OK路径: avg=10.9s, p50=9.4s, p95=18.3s, max=39.3s
- **key_cycle_429s: 100% (56/56 req)** — 53 cycle=1, 3 cycle=2
- Tier attempts: 56 pexec_success, 3 pexec_SSLEOFError
- Container: nv_gw healthy, 无漂移

## 分析
- R1700 KEY_COOLDOWN=65 (60s NVCF window + 5s buffer) 仍不足以消除 key_cycle_429s
- 100% 请求触发 key_cycle_429s → 每请求至少浪费一次429往返 + 延迟增加
- 3 SSLEOF 在 tier_attempts (重试成功) 可能与 key cycling 相关
- 单IP (HM1 直连) 的 NVCF per-IP rate-limit 窗口 > 60s 估计
- +5s 到 70s 提供更大缓冲: 70+70=140 << 170 TIER_BUDGET 安全
- 12 zombie 全为 NVCF content-filter 大输入 (>250k), 非 config 可修
- 铁律 KEY=TIER 保持

## 修改
- HM1: KEY_COOLDOWN_S: 65→70 (+5s)
- HM1: TIER_COOLDOWN_S: 65→70 (+5s)
- 重启 nv_gw: `docker compose up -d nv_gw`
- 验证: `docker exec nv_gw env` → KEY_COOLDOWN_S=70, TIER_COOLDOWN_S=70 ✓
- 验证: `/health` → status=ok ✓
- 验证: `docker logs` → no errors ✓

## 验证
- Compose: `KEY_COOLDOWN_S: "70"`, `TIER_COOLDOWN_S: "70"` ✓
- Container env: `KEY_COOLDOWN_S=70`, `TIER_COOLDOWN_S=70` ✓
- 无容器漂移, 全参数匹配 ✓
- curl /health: status=ok ✓
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
