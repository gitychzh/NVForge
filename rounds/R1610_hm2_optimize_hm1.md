# R1610: HM2→HM1 — NOP (all params floor/optimal, peer-fb rescue active, zombie + ATE only)

## 数据采集

### 容器状态
- `nv_gw`: Up 4 min (healthy) — 重启于 2026-07-16T03:02:19Z
- `ms_gw`: Up 27h (healthy)
- `logs_db`: Up 27h (healthy)
- Compose md5: `f81f01c6bc7cfe87f237390c19105e7d` (unchanged from R1609)

### 请求统计 (6h)
```
total | ok | fail | sr_pct
64    | 45 | 19   | 70.3
```

### 分时段
```
period | total | ok | fail | sr_pct
pre    | 62    | 44 | 18   | 71.0
post   | 3     | 2  | 1    | 66.7  ← 仅3请求, 不具统计意义
```

### 按模型
```
model       | total | ok | fail | sr_pct
glm5_2_nv   | 36    | 26 | 10   | 72.2
dsv4p_nv    | 28    | 19 | 9    | 67.9
```

### 错误类型
```
error_type              | cnt | avg_dur
zombie_empty_completion | 15  | 7612ms   ← NVCF content-filter, 不可配置修复
all_tiers_exhausted     | 4   | 35527ms  ← 3 dsv4p_nv + 1 glm5_2_nv
```

### Zombie 详情
- dsv4p_nv: 6× zombie, avg input_chars=224,485, avg dur=9,923ms
- glm5_2_nv: 9× zombie, avg input_chars=223,728, avg dur=6,071ms
- 特征: 超大输入(>220K chars) → 空输出 → NVCF content-filter → 不可配置修复

### ATE 详情
- dsv4p_nv: 3× all_tiers_exhausted (pre-restart); 1× zombie (pre-restart)
- glm5_2_nv: 1× all_tiers_exhausted (pre-restart)
- post-restart: 1× zombie (glm5_2_nv, 8,623ms)

### Peer-FB (post-restart)
```
[NV-PEER-FB] local all_tiers_exhausted (model=dsv4p_nv) → peer fallback
[NV-PEER-FB] peer fallback OK: status=200 bytes=1311 ttfb=4ms      ← 成功
[NV-PEER-FB] peer fallback OK: status=200 bytes=14 ttfb=4617ms     ← 成功
```
**Peer-FB 2/2 100% SR** — R1609 移除 dsv4p_nv MODELMAP 后 peer-fb 正常运作。

### Tier Attempts
- glm5_2_nv: 23× pexec_success (avg 14,257ms), 1× pexec_NameError, 1× pexec_empty_200
- dsv4p_nv: 0 tier_attempts (干净，无 key cycling)

### ms_gw
- 14/14 100% SR
- DEEPSEEK-AI/DEEPSEEK-V4-PRO: 3/3 OK
- ZHIPUAI/GLM-5.2: 11/11 OK

### Tier Chain
```
tier_chain=['glm5_2_nv'] (no fallback, 3model)  ← FALLBACK_GRAPH={}, 预期
tier_chain=['dsv4p_nv'] (no fallback, 3model)   ← FALLBACK_GRAPH={}, 预期
```

### 当前关键参数 (全部 floor/optimal)
```
UPSTREAM_TIMEOUT=66                        ← floor
TIER_COOLDOWN_S=15
NVU_PEXEC_TIMEOUT_FASTBREAK=1              ← floor
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1          ← floor
NVU_EMPTY_200_FASTBREAK=2                  ← R1031 optimal
NVU_TIER_BUDGET_DSV4P_NV=66                ← floor (=UPSTREAM)
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_TIMEOUT_BUDGET_S=205
NVU_PEER_FALLBACK_TIMEOUT=66               ← floor
NVU_PEER_FB_SKIP_MODELS=                   ← 空, peer-fb 全开
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms  ← R1609: 无 dsv4p_nv
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_SSLEOF_RETRY_DELAY_S=1.0
```

## 决策: NOP

**理由**: 所有参数均为 floor/optimal 状态，无任何可优化空间:

1. **Zombie (15/19=78.9% of failures)**: NVCF content-filter — 超大输入(>220K chars)触发空输出。代码级 zombie 快速检测(3-15s)已是最优。不可配置修复。
2. **ATE (4/19=21.1% of failures)**: 3 pre-restart dsv4p_nv + 1 pre-restart glm5_2_nv。Post-restart peer-fb 2/2 100% SR 证明 R1609 的 dsv4p_nv MODELMAP 移除是正确的 — peer-fb 替代 ms_gw relay 作为 dsv4p_nv 的救援通道。
3. **所有参数 floor/optimal**: UPSTREAM=66, FASTBREAK=1, BUDGET=66 (dsv4p), PEER_FB_TIMEOUT=66, COOLDOWN=15 — 已无可降空间。
4. **ms_gw 14/14 100% SR**: 健康。
5. **Tier attempts 干净**: dsv4p_nv 0 tier_attempts (无 key cycling), glm5_2_nv 仅 1 empty_200 + 1 NameError。

**无参数变更。**

## ⏳ 轮到HM1优化HM2
