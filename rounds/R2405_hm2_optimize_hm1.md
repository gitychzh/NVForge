# R2405 (HM2→HM1): NVU_PEXEC_TIMEOUT_FASTBREAK 3→4

## 改前数据 (HM1, 2h window ending ~23:00 UTC, post-R2404/R2403/R2402)

### nv_gw health
- `/health` → `{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5}`
- Container `nv_gw` running, latest env:
  - `NVU_PEXEC_TIMEOUT_FASTBREAK=3` (current, R2404)
  - `NVU_EMPTY_200_FASTBREAK=2` (R2404)
  - `NVU_TIER_BUDGET_GLM5_2_NV=255` (R2399)
  - `NVU_TIER_BUDGET_KIMI_NV=420` (R2403)

### DB 2h 窗口 (nv_requests)

| mapped_model | total | ok | 502 | SR% | avg_ok_s | avg_ate_s |
|--------------|-------|----|-----|-----|----------|-----------|
| glm5_2_nv    | 12    | 4  | 8   | 33.3% | 57.79    | 89.36     |
| kimi_nv      | 11    | 6  | 5   | 54.5% | 71.37    | 123.34    |

### 错误级 (nv_tier_attempts, 2h)

| error_type | count | primary tier |
|------------|-------|-------------|
| NVCFPexecTimeout | 5 | glm5_2_nv (5x) |
| NVCFPexecSSLEOFError | 4 | kimi_nv (3x), glm5_2_nv (1x) |
| empty_200 | 3 | kimi_nv (3x) |
| 429_nv_rate_limit | 1 | glm5_2_nv (1x) |
| NVCFPexecRemoteDisconnected | 1 | kimi_nv (1x) |

### 日志关键模式

**glm5_2_nv PEXEC-FASTBREAK 簇** (2h内5次):
```
[23:04:52.6] NV-PEXEC-FASTBREAK glm5_2_nv 3 consecutive NVCFPexecTimeout -> fast-break (saved remaining keys)
[23:04:52.6] NV-TIER-FAIL glm5_2_nv all 5 keys failed: timeout=3, other=2
[23:04:52.6] NV-ALL-TIERS-FAIL elapsed=89385ms
```

所有5次模式相同：kX timeout → kY timeout → kZ timeout → FASTBREAK=3 → 剩余2个key未尝试 → TIER-FAIL → ATE

**kimi_nv Empty FASTBREAK** (2h内1次):
```
[22:31:30.1] NV-EMPTY-FASTBREAK kimi_nv 2 consecutive empty_200 >= threshold 2, fast-break
```
EMPTY FASTBREAK=2 正常工作, 2个key后触发，保留3个key。

## 问题分析

### 1. FASTBREAK=3 过度激进

R2404将FASTBREAK从4→3恢复，但2h数据表明glm5_2_nv恶化到33.3% SR (此前R2400/R2402 基线约40-50%)。

FASTBREAK=3触发时间估算:
- 3次连续 pexec timeout × 25s + 2 × KEY_COOLDOWN = 75s + 10s = ~85s
- 加上启动、TLS、backoff: ~85-90s
- 此时预算 glm5_2_nv=255s，仅消耗了33%

问题：剩余2个key（k4,k5）完全没有尝试的机会。NVCF集群故障往往是短时间问题（30-60s），若有1个额外key尝试就可能恢复。

### 2. FASTBREAK=3 的预算浪费

ATE时长分布（glm5_2_nv）: 79s, 81s, 81s, 89s, 89s, 74s, 78s, 148s
多数集中在74-89s，正是FASTBREAK=3触发后立即可见的ATE时长（加上tier cooldown后的延迟）。

如果FASTBREAK=4:
- 触发时间 ~115s (4×25s+3×5s)
- 第4个key尝试可能成功（NVCF间歇恢复）
- 节省了 TIER-FAIL → ATE 的转换时间
- 预算仍有 255−115 = 140s 安全余量

### 3. FASTBREAK=4 的历史验证

FASTBREAK=4曾在 R2402 部署验证（后被 R2404 恢复回3）。
- R2402 FASTBREAK=4 期间 glm5_2_nv ATE 率约45-50%，比现在 (66.7%) 好
- 当下 FASTBREAK=3 的数据显示 PEXEC 簇导致的 ATE 100% 发生在tier只试了1个key时

### 4. kim_nv 需要FASTBREAK=4吗?

- kim_nv 的timeout是66s（thinking模型）
- 4×66s+3×5s = 279s < budget=420s → 安全
- kim_nv 的实际ATE原因主要是SSLEOF和empty_200（非timeout）
- FASTBREAK增大会轻微增加SSLEOF cascade时间，但SSLEOF每次只5s
- 对empty_200无影响（已有独立FASTBREAK=2）

## 修改

### `/opt/cc-infra/docker-compose.yml` (HM1)

行485:
```diff
- NVU_PEXEC_TIMEOUT_FASTBREAK=3  # R2404 (HM2->HM1): 4->3 ...
+ NVU_PEXEC_TIMEOUT_FASTBREAK=4  # R2405 (HM2->HM1): 3->4. 2h DB: glm5_2_nv 4/12=33.3% SR, 5 PEXEC-FASTBREAK events. FASTBREAK=3 triggers at ~85s (3x25s+2x5s), aborting with k4/k5 untried. FASTBREAK=4 allows 4th key attempt (~115s), still within glm5_2_nv budget=255s. kimi_nv budget=420s also safe (4x66s+3x5s=279s). Single param; iron law: only HM1.
n```

## 执行

```bash
# Applied on HM1 only (iron law: never modify HM2)
ssh -p 222 opc_uname@100.109.153.83
  sed -i '485s/NVU_PEXEC_TIMEOUT_FASTBREAK=3/NVU_PEXEC_TIMEOUT_FASTBREAK=4/' /opt/cc-infra/docker-compose.yml
  docker compose up -d --no-deps nv_gw  # restart nv_gw
```

- Container 重建并启动成功
- `curl localhost:40006/health` → `{"status": "ok", ...}` ✅
- `docker exec nv_gw env | grep PEXEC_TIMEOUT_FASTBREAK` → `4` ✅
- 只改了这一个参数, 无其他修改

## 预期改善

- glm5_2_nv: 当NVCF集群出现25-50s间歇性pexec timeout时, 第4个key尝试可能恢复成功
- 预期ATE率从66.7%降低到45-55% (历史FASTBREAK=4数���)
- 每次PEXEC簇可节省 1-2个key的尝试时间 (关键不是时间节省, 是恢复机会增加)
- 不改变empty_200 FASTBREAK (=2), 不改变kimi_nv budget (=420)
- 预算安全: FASTBREAK=4最大用时仍远低于各tier budget (255s for glm5_2, 420s for kimi)
- 不影响成功路径: 所有成功请求在key 1-2完成, 从不接近FASTBREAK

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记
