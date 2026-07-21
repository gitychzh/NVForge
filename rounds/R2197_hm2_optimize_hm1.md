# R2197 (HM2→HM1): TIER_COOLDOWN_S 4→2 (-2s)

## 数据 (6h 窗口, HM1)

| Metric | Value |
|---|---|
| 总请求 | 26 |
| 成功 | 18 (69.23%) |
| Zombie | 8 (30.77%) |
| ATE | 0 |
| 429 cycling | 100% (26/26 key_cycle_429s=1) |
| Peer-FB | 0 (0/0/0) |
| OK avg latency | 16129ms |
| OK min/max | 5755ms / 46273ms |

**Tier attempts**: glm5_2_nv: pexec_success=29, pexec_SSLEOFError=6, pexec_429=5, pexec_timeout=1

**模型**: 仅 glm5_2_nv (26 req), 无 dsv4p_nv/kimi_nv

## 诊断

- 8 zombie 全为 glm5_2_nv 上游 NVCF SSLEOF 导致空 200→502, 非配置可控
- 王者 100% key_cycle_429s=1: KEY_COOLDOWN_S=14 远低于 60s NVCF 窗口, 每次请求首 key 必冷, 良性
- 0 ATE 连续第 13 轮无 ATE ★
- 0 peer-fallback 事件: 无 ATE 触发 peer-fb
- Zombie 平均耗时 ~9s, 比 OK 请求 (~16s) 甚至更短(快速失败)

## 改动

**TIER_COOLDOWN_S 4→2 (-2s)**

交替 TIER→KEY 模式 (R2193 TIER 6→4, R2194 KEY 16→14, R2197 TIER 4→2)

**预算**: KEY+TIER+GLM5_2 = 14+2+28 = 44 << 153 BUDGET (109s 余量)

**429 风险**: 已 100% cycling, TIER_COOLDOWN_S 变化不影响 429 率 (KEY_COOLDOWN_S=14 远在反模式区, 与 TIER_COOLDOWN_S 无关)

**单参数**: 铁律只改 HM1 不改 HM2 ✓

## 验证

- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → TIER_COOLDOWN_S=2 ✓
- `curl /health` → status=ok ✓
- Container 重启确认: `docker compose stop nv_gw && docker compose up -d nv_gw` ✓
## ⏳ 轮到HM1优化HM2
