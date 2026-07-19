# R1876 (HM2→HM1): BIG_INPUT_THRESHOLD 130000→115000 — catch glm5_2_nv zombie at ~119K

## 触发

Git HEAD `be50d5c` = R1875 (HM2 cc2 inspect). HM1未提交新commit. 脚本输出 "这是我提交的, 不触发". 但cron再次触发HM2优化HM1. 实际有数据可优化.

## 数据采集 (HM1, 2026-07-19 10:35 CST)

### docker logs nv_gw (last 100)
- 4条 zombie_empty_completion (10:33:20-10:33:47), 全部 glm5_2_nv, input_chars=119845-120106
- 每条 zombie: pexec成功→返回空内容(content_chars=12 < 50)→abort stream→502
- 每条 zombie 循环1个key (cycle time 3.5-10s), 无 breaker 触发
- 零 BIG-INPUT 事件, 零 NV-ANTH-BREAKER 事件

### docker exec nv_gw env
- NVU_BIG_INPUT_THRESHOLD=130000 (R1873: 250000→130000)
- NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=7200, NVU_BIG_INPUT_MODELS=glm5_2_nv
- UPSTREAM_TIMEOUT=49, KEY_COOLDOWN_S=46, TIER_COOLDOWN_S=46, TIER_TIMEOUT_BUDGET_S=178
- NVU_PEER_FALLBACK_TIMEOUT=122, MIN_OUTBOUND_INTERVAL_S=0, NV_INTEGRATE_KEY_COOLDOWN_S=0
- 全参数 compose=container 一致, 零漂移

### DB (6h window)
- 41 total: 9 OK(200), 32 FAIL(502) = 21.9% SR
- dsv4p_nv: 3 OK (all with error_type=all_tiers_exhausted but status=200 — phantom ATE)
- glm5_2_nv: 6 OK(200), 32 FAIL(502 zombie_empty_completion)
- 6 OK 的 input_tokens: 16, 27296, 27621, 66021, 66110, 26609
- 32 zombie 的 input_tokens: ~27K-28K (≈119K-127K chars at 3.0 chars/token)
- 零 fallback_occurred, 零 peer-fb

### DB (30min window)
- 4 total: 0 OK, 4 FAIL = 0% SR
- 全部 glm5_2_nv zombie_empty_completion, avg duration=6533ms

### nv_tier_attempts (6h)
- pexec_success: 49
- pexec_429: 1
- pexec_SSLEOFError: 1
- 零 ATE, 零 zombie 在 tier 层

### 容器状态
- nv_gw: Up 23 minutes (healthy), StartedAt=2026-07-19T02:17:57Z (R1873 重启)
- /health: {"status":"ok"} ✓

## 分析

**核心问题**: R1873 将 BIG_INPUT_THRESHOLD 从 250000 降到 130000，但 glm5_2_nv zombie 的实际 input 在 ~119K-127K chars 范围内，仍低于 130000 阈值。breaker 从未触发——日志零 BIG-INPUT 事件，零 NV-ANTH-BREAKER 事件。

**影响**: 每条 zombie 请求 pexec 成功返回空内容→nv_gw 检测到 zombie→abort stream→502。下游 cc4101 收到 zombie→api_error→CC retry，但 retry 仍走 glm5_2_nv 同函数同 input→再次 zombie→循环。每个 zombie 浪费 3-10s 且无 fallback 救援。

**根本原因**: NVCF glm5_2 function 在大输入(~119K+ chars)下返回空内容(start-fn-only 模式)，这是 NVCF 侧已知问题，代码已通过 zombie 检测+breaker 机制处理。breaker 阈值 130000 未覆盖 119K-129K 区间。

## 优化: NVU_BIG_INPUT_THRESHOLD: 130000 → 115000

**参数**: 单一参数 BIG_INPUT_THRESHOLD

**改动**: 130000→115000 (-15000 chars, -11.5%)

**理由**:
1. zombie input 范围 ~119K-127K chars，115000 阈值可覆盖所有当前 zombie 场景
2. breaker 触发后(cooldown 7200s=2h) 后续同 input 快速 reject→peer-fb→HM2 rescue
3. 115000 仍远高于正常 input (OK 请求 max input=66110 tokens ≈ 198K chars at 3.0，但 66110 是 OK 请求——说明有正常大 input 能成功。zombie 模式是 input>119K chars + content_chars<50)
4. 保守: 115000 与正常大 input 边界至少有 38000 chars 安全距离 (198K-119K=79K chars 余量，115K 距 119K 仅 4K 但 breaker 仅影响 zombie 模式)
5. 单参数, 少改多轮, 铁律:只改HM1不改HM2

**约束验证**:
- UPSTREAM=49 + PEER_FALLBACK=122 = 171 < BUDGET=178 (7s margin) ✓
- PEER_FALLBACK=122 ≥ HM2_BUDGET+2 ✓
- NVU_BIG_INPUT_FAIL_N=1 (R1713): 首次 zombie 后 breaker 立即 OPEN ✓
- BIG_INPUT_COOLDOWN=7200s: 2h 窗口内同 input 快速 reject ✓

## 部署验证

- `sed -i 's|NVU_BIG_INPUT_THRESHOLD: "130000".*|NVU_BIG_INPUT_THRESHOLD: "115000"  # R1876|'` ✓
- `docker compose up -d nv_gw` + restart ✓
- `docker exec nv_gw env | grep BIG_INPUT_THRESHOLD` → 115000 ✓
- `/health` → {"status":"ok"} ✓
- Container: Up (healthy) ✓
- 全参数 compose=container 一致, 零漂移 ✓

## 参数快照

| 参数 | 值 | 来源 |
|------|-----|------|
| NVU_BIG_INPUT_THRESHOLD | **115000** | **R1876** |
| NVU_BIG_INPUT_FAIL_N | 1 | R1713 |
| NVU_BIG_INPUT_COOLDOWN_S | 7200 | R1745 |
| NVU_BIG_INPUT_MODELS | glm5_2_nv | R1695 |
| UPSTREAM_TIMEOUT | 49 | R1857 |
| KEY_COOLDOWN_S | 46 | R1870 |
| TIER_COOLDOWN_S | 46 | R1870 |
| TIER_TIMEOUT_BUDGET_S | 178 | R1840 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | R1744 |
| MIN_OUTBOUND_INTERVAL_S | 0 | R638 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | R631 |

## 结论

R1873 的 250000→130000 是一个正确的方向，但未覆盖 119K-129K 区间的 zombie。R1876 进一步降到 115000 以覆盖当前所有 zombie 场景。预期: breaker 首次触发后 cooldown 2h 内同 input 快速 reject+peer-fb rescue，SR 回升。下轮 R1877 盯: breaker 是否触发, BIG-INPUT 事件是否出现, peer-fb rate, glm5_2_nv SR。
## ⏳ 轮到HM1优化HM2
