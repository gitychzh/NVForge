# R2043 (HM2→HM1): NVU_BIG_INPUT_THRESHOLD 115000→100000

## 数据采集 (HM1)

### DB 6h 窗口
- **总流量**: 30 req, 25 OK, 5 fail → **SR 83.33%**
- **30min**: 4 req, 3 OK, 1 fail → SR 75.00%
- **失败全部**: zombie_empty_completion ×4 + all_tiers_exhausted ×1 (全部 status=502)
- **Phantom ATE**: 2 dsv4p_nv (status=200, BIGINPUT breaker→peer-fb rescue), 2 glm5_2_nv (status=200)
- **429 cycling**: 25/30 (83.3%) — R2042 的 92.9%→83.3% 改善 -9.6pp
- **Fallback**: 0 triggered (no cross-model, no peer-fb in DB; peer-fb in logs for dsv4p_nv BIGINPUT rescues)
- **Latency (glm5_2_nv)**: avg 8937ms, range 2849-18388ms (vs R2042 avg 8881ms, 稳定)
- **Latency (dsv4p_nv)**: 2 req, avg 9944ms (both BIGINPUT peer-fb rescue)
- **Tier attempts**: 25 pexec_success, 1 pexec_429, 1 pexec_SSLEOFError

### 模型分布
- glm5_2_nv: 28/30 (93.3%), SR 82.14%
- dsv4p_nv: 2/30 (6.7%), SR 100% (both peer-fb rescued)

### Docker logs
- BIGINPUT breaker OPEN for dsv4p_nv (186K chars), 2/2 peer-fb rescues succeeded (ttfb=8ms,10ms)
- glm5_2_nv: 1 real ATE (all 5 keys timeout/other, 40s elapsed → peer-fb → HM2 timeout 122s → 502)
- Container restarted ~13:40 (R2043 deploy), clean startup

### Live env (R2042 态)
- NVU_BIG_INPUT_THRESHOLD=115000
- KEY_COOLDOWN_S=0, TIER_COOLDOWN_S=0 (R2042)
- NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=10800

## 分析

R2042 将 KEY_COOLDOWN_S=TIER_COOLDOWN_S=0 后，429 cycling 从 92.9%→83.3% 改善 9.6pp，方向正确但未根除。4 zombie/6h 全部 glm5_2_nv，说明仍有 zombie 输入低于 115K 阈值。

R1876 将阈值从 130000→115000 成功捕获了 ~119K chars 的 zombie，但当前仍有 4 zombie/6h，说明存在更小的 zombie 输入（~100K-115K chars）。BIGINPUT breaker 机制已证明：peer-fb rescue 路径 100% 成功（dsv4p_nv 2/2），breakers 打开后 fast-reject→peer-fb 比 zombie 等待 25s 超时更优。

NVU_BIG_INPUT_FAIL_N=1 确保第一只 zombie 即可打开 breaker，后续同类输入快速拒绝。

## 优化

**NVU_BIG_INPUT_THRESHOLD: 115000→100000**

降低 15K chars 阈值，捕获更多 zombie-prone 输入。peer-fb 救援路径已证明有效（dsv4p_nv 2/2 rescue），fake-ATE→peer-fb→HM2 比 zombie 超时更优。单参数，低风险。

## 部署验证

- `sed -i` 修改 compose 第 632 行 → OK
- `docker compose up -d nv_gw` → Container Recreated / Started
- `docker exec nv_gw env` → NVU_BIG_INPUT_THRESHOLD=100000 ✓
- `docker logs nv_gw --tail 5` → clean startup, Listening on 0.0.0.0:40006 ✓

## 预期

- Zombie 减少（阈值降低捕获更多 zombie 输入）
- Peer-fb rescue 增加（fake-ATE→peer-fb→HM2 替代 zombie 超时）
- SR 提升至 85%+
- 429 cycling 继续观察（R2042 零 cooldown 已改善 9.6pp）

单参数; 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
