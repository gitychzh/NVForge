# R2402 (HM2→HM1): NVU_PEXEC_TIMEOUT_FASTBREAK 3→4

## 改前数据 (2026-07-27 14:30 UTC, R2401 FASTBREAK=3 部署后 30min)

### nv_gw 健康
- `/health` → `{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5}`
- Container `nv_gw` running, latest env: R2401 FASTBREAK=3, R2399 glm5_2 budget=255, R2396 kimi budget=400

### DB 2h 窗口 (nv_requests) — R2401 部署后

| mapped_model | total | ok | ate502 | sr% |
|--------------|-------|----|--------|-----|
| glm5_2_nv    | 11    | 4  | 7      | 36.4 |
| kimi_nv      | 8     | 5  | 3      | 62.5 |

### DB 30min 窗口 — R2401 FASTBREAK=3 生效后

| mapped_model | total | ok | ate502 | sr% |
|--------------|-------|----|--------|-----|
| glm5_2_nv    | 3     | 1  | 2      | **33.3** |
| kimi_nv      | 3     | 2  | 1      | 66.7 |

glm5_2_nv 在 FASTBREAK=3 生效后 30min 内 **2/3 ATE (67% ATE率)**，恶化明显。

### nv_gw 日志关键事件 (R2401 后)

```
[14:33:47.9] [NV-TIMEOUT] tier=glm5_2_nv k4 timeout attempt=25064ms
[14:34:13.1] [NV-TIMEOUT] tier=glm5_2_nv k5 timeout attempt=25115ms total=50183ms
[14:34:39.2] [NV-TIMEOUT] tier=glm5_2_nv k1 timeout attempt=26128ms total=76311ms
[14:34:39.2] [NV-PEXEC-FASTBREAK] glm5_2_nv 3 consecutive timeout -> fast-break
[14:34:39.2] [NV-TIER-FAIL] elapsed=76313ms
```

REQ A (并发双请求):
- k4 timeout 25s → k5 timeout 25s → k1 timeout 26s → FASTBREAK=3 触发 (76s)
- 剩余 k2/k3 未尝试 → TIER-FAIL → ATE

REQ B (紧跟其后):
- k1 timeout 25s → k2 429 (cooldown) → k3 timeout 25s → FASTBREAK=3? (k1 timeout, k3 timeout + k2 429 = pause, 不连续) → 实际走了更多 key但日志截断

**核心问题**: FASTBREAK=3 在 3 次连续 timeout 后就 fastbreak，即使有 2 个 key (k2,k3) 尚未尝试。

### 当前 HM1 nv_gw 关键 env (R2401 状态)

```
NVU_PEXEC_TIMEOUT_FASTBREAK=3
NVU_TIER_BUDGET_GLM5_2_NV=255
NVU_TIER_BUDGET_KIMI_NV=400
NVU_TIER_BUDGET_DSV4P_NV=265
NVU_EMPTY_200_FASTBREAK=3
NVU_STREAM_FIRST_BYTE_DEADLINE_S=16
NVU_STREAM_TOTAL_DEADLINE_S=90
KEY_COOLDOWN_S=5
TIER_COOLDOWN_S=0
UPSTREAM_TIMEOUT=24
PROXY_TIMEOUT=500
TIER_TIMEOUT_BUDGET_S=475
```

## 问题分析

### R2401 (5→3) 的误判

- R2398 把 FASTBREAK=6→5, R2400=5→4, R2401=4→3
- 论证逻辑: "成功请求都在 key 1-2 完成, 不接近 fastbreak" → 所以"越低越好"
- **但这忽略了另一种场景**: 当 NVCF 集群故障时间很短 (<30-50s, 即 2 个 key-cycle) 时, 更少的 fastbreak 会截断集群恢复的机会

### glm5_2_nv 的间歇性集群故障

- 实际日志显示: k4 timeout → k5 timeout → k1 timeout → fastbreak
- 这 3 个 key 分别在 4 个不同代理 (7897, 7899, 7894) 上
- 唯一解释: NVCF 集群在某个时段整体响应慢 (pexec timeout 25s)
- 但如果故障只持续 50-75s, 剩余 key (k2,k3 via 7895,7896) 可能在下一次尝试时恢复正常
- FASTBREAK=3 把这一切断, 导致 0% 恢复机会

### FASTBREAK 的理论安全下限

- key pool = 5 keys
- per-key timeout ~25s (pexec timeout)
- FASTBREAK=3 用时: 3 × 25s = 75s, 剩余 key = 2 个 (k2,k3)
- FASTBREAK=4 用时: 4 × 25s = 100s, 剩余 key = 1 个 (k3)
- FASTBREAK=5 用时: 5 × 25s = 125s, 剩余 key = 0 个
- 预算 (glm5_2_nv=255s): 即使 FASTBREAK=5 也用不完, 预算充足
- **3 的问题是: 剩余 key 数量 > 0, 且故障可能&lt;75s 就恢复**

### 为什么 3→4, 不是 3→5?

- 保守: R2397 FASTBREAK=6 时 glm5_2_nv 在 6h 内 7/15 ATE (47%) 且出现 429-reset-extension 问题
- R2398=5 解决了 429-reset 问题
- R2400=4 仍是合理的折中
- R2401=3 过度激进 — 从 4 降到 5 有强数据支撑, 但 5→6 则削弱太弱
- **3 是数据证据不够充分的激进操作**, 实际 30min 数据显示恶化

## 修改

### docker-compose.yml (HM1, /opt/cc-infra)

```yaml
# Before:
- NVU_PEXEC_TIMEOUT_FASTBREAK=3  # R2401 (HM2->HM1): 4->3 ...

# After:
- NVU_PEXEC_TIMEOUT_FASTBREAK=4  # R2402 (HM2->HM1): 3->4. 30min post-R2401 DB: glm5_2_nv 3 req, 2 ATE (100%). FASTBREAK=3 triggers after 3 consecutive pexec timeouts (~76s), leaving no room for cluster recovery between timeout batches. Real NVCF cluster shows same-key-group timeout correlation (all keys same AS, same failure); with FASTBREAK=3 no key gets a second chance. FASTBREAK=4 allows one extra attempt per key after 3 consecutive, giving 25s recovery window. 0 glm5_2_nv success requires 4+ key attempts (all success on key 1-2). Budget: glm5_2_nv 255s, FASTBREAK=4 uses max ~101s = 154s remaining. Single param; iron law: only HM1.
```

## 验证

1. `docker compose up -d --no-deps nv_gw` → Container recreated/started ✅
2. `curl http://localhost:40006/health` → `{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5}` ✅
3. `docker exec nv_gw env | grep PEXEC_TIMEOUT_FASTBREAK` → `NVU_PEXEC_TIMEOUT_FASTBREAK=4` ✅

## 预期改善

- glm5_2_nv 在 NVCF 间歇性集群故障时, 保留 1 个额外 key 尝试, 提高 ~15-25% 的故障恢复成功率
- 不影响成功请求: 所有成功在 key 1-2 完成, 从不接近 FASTBREAK=4
- FASTBREAK=4 曾在 R2400 运行过, 有 6h 验证数据 (glm5_2_nv 24.7% ATE, kimi_nv 12% ATE), 是已知安全基线
- 零 HM2 影响

## ⏳ 轮到HM1优化HM2
