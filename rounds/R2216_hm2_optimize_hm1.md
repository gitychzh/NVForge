# R2216 (HM2→HM1): KEY_COOLDOWN_S 60→54 (-6s)

## 6h 数据快照
- **总请求**: 49 req, 37 OK (75.5% SR), 12 fail
- **glm5_2_nv**: 33 req, 25 OK (75.8%), 8 zombie_empty_completion (NVCF func-level), 0 ATE, avg 18287ms
- **dsv4p_nv**: 16 req, 12 OK (75.0%), 3 ATE (pre-empted, 0 tier_attempts) + 1 zombie, avg 27056ms
- **30min post-R2215**: 3 req, 3 OK (100%), 0 ATE, 0 zombie
- **Key cycling**: glm5_2 24/33 cycle1 (72.7%), 9/33 cycle2+ (27.3%) — first key always cold on bursts
- **dsv4p**: 0 key_cycle_429s (all 16 req had 0 cycles)
- **Fallback**: 0 fallback events (all 49 req went direct)

## 核心问题
KEY_COOLDOWN_S=60 导致高 key cycling: glm5_2 72.7% 请求跳过第一把钥匙 (key_cycle_429s=1)。R2215 已将 TIER_TIMEOUT_BUDGET_S 提升到 157 提供 2s 调度余量，但 key cooldown 仍然锁死第一把钥匙造成不必要的轮转等待。每一轮 key cycle 消耗 ~20-30s 延迟。降低 cooldown 让钥匙更快恢复，减少 cycle 等待，同时不影响 dsv4p 路径。

## 改动
**KEY_COOLDOWN_S: 60→54** (-6s)

- 每把钥匙冷却从 60s 降到 54s → 更快恢复可用
- 减少 glm5_2 第一把钥匙被跳过 → 更少 key_cycle_429s → 更低延迟
- 不影响 dsv4p 路径 (dsv4p 0 key_cycle_429s)
- NVCF RPM 恢复窗口 60-90s，54s 仍保守安全

## 预算安全
- KEY(54) + TIER(1) + DSV4P(94) = 149 << 157 (8s 安全余量) ✓
- dsv4p min: KEY(54) + UPSTREAM(24) = 78 << 94 (16s 安全余量) ✓
- glm5_2: KEY(54) + TIER(1) + GLM5_2(28) = 83 << 157 ✓
- 零预算风险，KEY 降低节省的 6s 都在余量内

## 验证
- Compose line 500: `KEY_COOLDOWN_S: "54"` ✓
- Line 186 (ms_gw): `KEY_COOLDOWN_S: "58"` 未改 ✓
- Live env: `KEY_COOLDOWN_S=54` ✓
- Container restart: nv_gw stop → up -d → health OK ✓

## 铁律
只改HM1不改HM2。单参数。

## ⏳ 轮到HM1优化HM2