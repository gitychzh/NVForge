# R2042 (HM2→HM1): KEY_COOLDOWN_S=TIER_COOLDOWN_S 75→0

## 数据采集 (HM1)

### DB 6h 窗口
- **总流量**: 28 req, 23 OK, 5 fail → **SR 82.14%**
- **30min**: 3 req, 3 OK, 0 fail → SR 100%
- **失败全部**: zombie_empty_completion ×5 (status=502), 无真实 ATE
- **Phantom ATE**: 2 (status=200, all_tiers_exhausted w/ empty-200 rescue, 04:33)
- **429 cycling**: 26/28 req (92.9%) — 24 with 1 cycle, 2 with 2 cycles
- **Fallback**: 0 triggered (no cross-model, no peer-fb)
- **Latency (glm5_2_nv)**: avg 8881ms, range 2849-18388ms
- **Tier attempts**: 26 pexec_success, 1 pexec_429, 1 pexec_SSLEOFError

### 模型分布
- 全部 glm5_2_nv (28/28), 无其他模型

### Docker logs
- 容器最后重启 03:02:10Z, clean startup, 无运行时 error/warn
- health check: Listening on 0.0.0.0:40006

### Live env (R2041 态)
- KEY_COOLDOWN_S=75, TIER_COOLDOWN_S=75
- TIER_TIMEOUT_BUDGET_S=153
- 75+75=150 << 153 (3s margin, 极紧)

## 分析

R2041 将 KEY=TIER 从 60→75 (+15s)，期望超越 NVCF 60s 边界 +15s 缓冲以减少 429 cycling。但实测 429-cycling 从 R2030 的 60.6% (20/33) 恶化至 92.9% (26/28)。75s 不仅未消除 429，反而使更多请求进入 key 轮转等待。

5 zombie 每小时 pattern 与 429 cycling 高度相关：keys 在 429 后长时间冷却，请求在 key 轮转中耗尽预算后以 zombie 结束。无 fallback 路径（只有 glm5_2_nv 单 tier），一旦 zombie 就 502。

429-cycling 反模式规则：KEY_COOLDOWN_S 在 1-59s 反恶化 429 率，≥60s 应为充分。但 60s 和 75s 都未消除 429 → 问题不在冷却时间长度，而在冷却机制本身。0s 消除 key/tier 锁是唯一剩余路径。

预算：75+75=150 仅 3s margin 极度危险。0+0=0 << 153 大幅安全。

## 优化

**KEY_COOLDOWN_S: 75→0**
**TIER_COOLDOWN_S: 75→0**

0s 消除 key/tier 锁，请求无需等待冷却即可使用任意 key。5 keys × 4.7 req/h 低流量，key 耗尽风险 ≈ 0。NV_INTEGRATE_KEY_COOLDOWN_S 已在 R631 归零并长期稳定验证。

预算：0+0=0 << 153 (153s margin, 极大安全)

## 部署验证

- `sed -i` 修改 compose 第 500/505 行 → OK
- `docker compose up -d nv_gw` → Container Recreated / Started
- `docker exec nv_gw env` → KEY_COOLDOWN_S=0, TIER_COOLDOWN_S=0 ✓
- `docker logs nv_gw --tail 5` → clean startup, Listening on 0.0.0.0:40006 ✓

## 预期

- 429 cycling 从 92.9% 大幅下降（0s 消除 key 锁等待）
- Zombie 减少（无 key 冷却 → 无 zombie 窗口）
- SR 回升至 90%+
- 零 cooldown 低流量下安全（5 keys, 4.7 req/h）

单参数对; 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2