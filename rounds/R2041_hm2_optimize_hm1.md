# R2041 (HM2→HM1): KEY_COOLDOWN_S=TIER_COOLDOWN_S 60→75 (+15s)

## 数据采集 (HM1)

### DB 6h 窗口
- **总流量**: 28 req, 23 OK, 5 fail → **SR 82.14%**
- **30min**: 3 req, 3 OK, 0 fail → SR 100%
- **失败全部**: zombie_empty_completion ×5 (status=502), 无真实 ATE
- **Phantom ATE**: 2 (status=200, all_tiers_exhausted w/ empty-200 rescue)
- **429 cycling**: 26/28 req (92.9%) — 24 with 1 cycle, 2 with 2 cycles
- **Fallback**: 0 triggered (no cross-model, no peer-fb)
- **Latency (glm5_2_nv)**: avg 8881ms, range 2849-18388ms
- **Tier attempts**: 26 pexec_success, 1 pexec_429, 1 pexec_SSLEOFError

### 模型分布
- 全部 glm5_2_nv (28/28), 无其他模型

### Zombie 时间线
```
23:33 - 4874ms
00:33 - 4132ms
01:33 - 5366ms
02:03 - 6529ms
04:03 - 3931ms
```
每小时1次 cadence, 04:03 zombie 后 04:33 出现 2 phantom ATE

### Docker logs
- SSLEOFError on glm5_2_nv k2 (pexec_us_rr), retry 0.1s delay
- 无其他异常

## 分析

R2030 将 KEY=TIER=60 设为 NVCF rate limit 边界值，期望消除 429 cycling。但实测 92.9% 请求仍然 429-cycling (26/28)，比 R2030 的 60.6% (20/33) 更差。60s 边界不足以让 keys 充分恢复。

5 zombie 每小时 pattern 与 429 cycling 高度相关：keys 在频繁 429 后进入 zombie 窗口（空 completion），keys 在冷却期内无法恢复，导致请求以 zombie 结束。无 fallback 路径（只有 glm5_2_nv 单 tier），一旦 zombie 就 502。

## 优化

**KEY_COOLDOWN_S: 60→75 (+15s)**
**TIER_COOLDOWN_S: 60→75 (+15s)**

75s 超越 NVCF 60s 边界 +15s 缓冲，给 keys 更充分的恢复时间。

预算检查: 75+75=150 << 153 TIER_TIMEOUT_BUDGET_S (3s margin, 低流量安全)

## 部署验证

- `docker compose up -d nv_gw` → Container Started
- `docker exec nv_gw env` → KEY_COOLDOWN_S=75, TIER_COOLDOWN_S=75 ✓
- `docker logs nv_gw --tail 5` → clean startup, Listening on 0.0.0.0:40006 ✓

## 预期

- 429 cycling 从 92.9% 显著下降
- Zombie 减少（keys 恢复时间充足）
- SR 回升至 90%+

单参数对; 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
