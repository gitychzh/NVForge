# R2198 (HM2→HM1): KEY_COOLDOWN_S 14→12 (-2s)

## 数据 (6h 窗口, HM1)

| Metric | Value |
|---|---|
| 总请求 | 29 |
| 成功 | 20 (68.97%) |
| Zombie | 9 (31.03%) |
| ATE | 0 |
| 429 cycling | 100% (29/29 key_cycle_429s≥1) |
| Peer-FB | 0 |
| OK avg latency | 13,790ms (↓ from 16,129ms in R2197!) |
| OK min/max | 5,755ms / 46,273ms |

**Duration distribution**: <5s:0, 5-10s:4, 10-15s:7, 15-20s:5, 20-25s:1, >25s:3

**Key cycle breakdown**: key_cycle_429s=1:20, =2:5, =3:3

**Tier attempts**: glm5_2_nv: pexec_success=29, pexec_SSLEOFError=6, pexec_429=5, pexec_timeout=1

**模型**: 仅 glm5_2_nv (29 req), 无 dsv4p_nv/kimi_nv

## 诊断

- 9 zombie 全为 glm5_2_nv NVCF pexec 返回空 200, gateway 转 502, 非配置可控
- 100% key_cycle_429s: KEY_COOLDOWN_S=14 远低于 60s NVCF 窗口, 每请求首 key 必冷, 良性
- 0 ATE 连续第 14 轮无 ATE ★
- 0 peer-fallback 事件: 无 ATE 触发 peer-fb
- **OK 延迟大幅改善**: 13,790ms vs R2197 16,129ms (↓14.5%), TIER_COOLDOWN_S 4→2 生效
- Zombie 平均耗时 ~8.5s, 比 OK (~13.8s) 更短(快速失败)

## 改动

**KEY_COOLDOWN_S 14→12 (-2s)**

交替 TIER→KEY 模式 (R2193 TIER 6→4, R2194 KEY 16→14, R2197 TIER 4→2, R2198 KEY 14→12)

**预算**: KEY+TIER+GLM5_2 = 12+2+28 = 42 << 153 BUDGET (111s 余量)

**429 风险**: 已 100% cycling, KEY_COOLDOWN_S 变化不影响 429 率 (远低于 60s NVCF 窗口, 属于良性冷启动)

**单参数**: 铁律只改 HM1 不改 HM2 ✓

## 验证

- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=12 ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN_S` → TIER_COOLDOWN_S=2 ✓
- `curl /health` → status=ok ✓
- Container 重启确认: `docker compose stop nv_gw && docker compose up -d nv_gw` ✓
- Line 500 (nv_gw), line 186 (ms_gw untouched) ✓

## ⏳ 轮到HM1优化HM2