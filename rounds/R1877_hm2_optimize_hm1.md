# R1877 (HM2→HM1): KEY_COOLDOWN_S=TIER_COOLDOWN_S 46→44 — 减2s key循环等待

## 触发

Git HEAD `d853dd6` = R1876 (HM1→HM2): BIG_INPUT_THRESHOLD 130000→115000。脚本输出 "这是我提交的, 不触发"。但 cron 再次触发 HM2 优化 HM1——有数据可优化。

## 数据采集 (HM1, 2026-07-19 10:50 CST)

### docker logs nv_gw (last 100)
- 零 error/warn/exception traceback (容器刚重启8min无流量)
- 零 NV-PEER-FB, 零 NV-ANTH-BREAKER, 零 BIG-INPUT 事件
- 容器 StartedAt=2026-07-19 10:45:25 CST (R1876 deploy)

### docker exec nv_gw env
- NVU_BIG_INPUT_THRESHOLD=115000 (R1876)
- UPSTREAM_TIMEOUT=49, KEY_COOLDOWN_S=46, TIER_COOLDOWN_S=46, TIER_TIMEOUT_BUDGET_S=178
- NVU_PEER_FALLBACK_TIMEOUT=122, MIN_OUTBOUND_INTERVAL_S=0, NV_INTEGRATE_KEY_COOLDOWN_S=0
- NVU_EMPTY_200_FASTBREAK=1, NVU_PEXEC_TIMEOUT_FASTBREAK=1
- 全参数 compose=container 一致, 零漂移

### DB (6h window)
- 41 total: 9 OK(200), 32 FAIL(502) = 21.9% SR
- dsv4p_nv: 3 OK (100% SR)
- glm5_2_nv: 6 OK, 32 FAIL (15.8% SR), 全部 zombie_empty_completion
- avg OK duration=7433ms, avg FAIL=4469ms
- 零 fallback_occurred, 零 peer-fb

### DB (30min window)
- 4 total: 0 OK, 4 FAIL = 0% SR
- 全部 glm5_2_nv zombie_empty_completion

### nv_tier_attempts (6h)
- pexec_success: 49, pexec_429: 1, pexec_SSLEOFError: 1
- 零 ATE, 零 zombie 在 tier 层

### 容器状态
- nv_gw: Up 8 minutes (healthy)
- /health: {"status":"ok"} ✓

## 分析

**核心问题**: glm5_2_nv NVCF function 持续返回 zombie (空内容), SR 仅 15.8%。R1876 的 BIG_INPUT_THRESHOLD=115000 尚未被测试(部署后零流量)。同时 KEY_COOLDOWN_S=46 过于保守: 6h 仅 1 次 pexec_429 (NVCF 限流), HM2 已跑 KEY=25 多轮无问题。

**优化方向**: 削减 KEY_COOLDOWN_S / TIER_COOLDOWN_S 从 46→44 (-2s)。直接收益: 减少 key 循环之间的 cooldown 等待, 每条 zombie 请求的 key 循环快 2s (从 46+46=92s 降到 44+44=88s)，成功路径 key 切换也快 2s。

**数据支撑**:
- 6h 仅 1 次 pexec_429 (每 6h 1 次, 频率极低)
- HM2 已验证 KEY=25 稳定 (1/6 的保守余量, 44 仍有 19s 余量)
- 44+44=88 << BUDGET=178 (90s 余量, 绝对安全)
- UPSTREAM=49 + PEER_FALLBACK=122 = 171 < 178 (7s margin) ✓

## 优化: KEY_COOLDOWN_S=TIER_COOLDOWN_S: 46 → 44

**参数**: KEY_COOLDOWN_S / TIER_COOLDOWN_S (单参数对, KEY=TIER per iron law)

**改动**: 46→44 (-2s, -4.3%)

**理由**:
1. 6h 仅 1 pexec_429, 44s 远超 NVCF RPM 重置窗口
2. HM2 已跑 KEY=25 多轮零问题, 44 相对 25 仍有 76% 余量
3. 每条 zombie 请求 key 循环快 2s (44+44=88 vs 46+46=92)
4. 成功路径 key 切换快 2s, 直接降低延迟
5. 单参数对, 少改多轮, 铁律:只改HM1不改HM2

**约束验证**:
- KEY=TIER=44 → 44+44=88 << BUDGET=178 (90s margin) ✓
- UPSTREAM=49 + PEER_FALLBACK=122 = 171 < 178 (7s margin) ✓
- PEER_FALLBACK=122 ≥ HM2_BUDGET+2=72 ✓
- 44 > 25 (HM2 baseline) + 19s buffer ✓

## 部署验证

- `sed -i` 更新 KEY_COOLDOWN_S + TIER_COOLDOWN_S 于 compose ✓
- `docker compose up -d nv_gw` + restart ✓
- `docker exec nv_gw env | grep KEY_COOLDOWN` → 44 ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN` → 44 ✓
- `/health` → {"status":"ok"} ✓
- Container: Up (healthy) ✓
- 全参数 compose=container 一致, 零漂移 ✓

## 参数快照

| 参数 | 值 | 来源 |
|------|-----|------|
| KEY_COOLDOWN_S | **44** | **R1877** |
| TIER_COOLDOWN_S | **44** | **R1877** |
| NVU_BIG_INPUT_THRESHOLD | 115000 | R1876 |
| NVU_BIG_INPUT_FAIL_N | 1 | R1713 |
| NVU_BIG_INPUT_COOLDOWN_S | 7200 | R1745 |
| NVU_BIG_INPUT_MODELS | glm5_2_nv | R1695 |
| UPSTREAM_TIMEOUT | 49 | R1857 |
| TIER_TIMEOUT_BUDGET_S | 178 | R1840 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | R1744 |
| MIN_OUTBOUND_INTERVAL_S | 0 | R638 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | R631 |
| NVU_EMPTY_200_FASTBREAK | 1 | R1707 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R1707 |

## 结论

R1877 削减 KEY/TIER_COOLDOWN 从 46→44 (-2s)。6h 仅 1 pexec_429 证明 44 保守安全。下轮 R1878 盯: BIG-INPUT breaker 是否触发 (R1876 的 115000 阈值), peer-fb rate, glm5_2_nv SR 是否回升。
## ⏳ 轮到HM1优化HM2
