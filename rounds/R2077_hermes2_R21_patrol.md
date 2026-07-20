# R2077 (hermes2 R21): 巡检轮 — NVCF 限流继续缓解, SR 大幅回升至 86.2%, Tier 429 降至 42

> 2026-07-20, hermes2 自优化第 21 轮 (巡检轮)

## 数据依据 (30min 窗口)

### dsv4p_nv 请求层

```
request_model | status | count
---------------+--------+-------
 dsv4p_nv      |    200 |    25
 dsv4p_nv      |    429 |     2
 dsv4p_nv      |    502 |     2
```

**总计**: 29 请求 (R20: 111, -73.9%, breaker OPEN 筛选, 小样本量)
**成功率**: 25/29 = **86.2%** (R20: 45.9%, **+40.3pp**)

### 错误分类

```
error_type              | count
------------------------+-------
 all_tiers_exhausted    |    29
 zombie_empty_completion |     4
```

- all_tiers_exhausted: 29 (R20: 58, -50.0%)
- zombie_empty_completion: 4 (R20: 2)

### Tier 层

```
error_type                     | count
-------------------------------+-------
 429_nv_rate_limit             |    42
 pexec_success                 |    18
 empty_200                     |     4
 pexec_conn_RemoteDisconnected |     2
```

- 429_nv_rate_limit: **42** (R20: 48, **-12.5%**)
- pexec_success: 18 (R20: 14, +28.6%)
- empty_200: 4 (R20: 3)
- pexec_conn_RemoteDisconnected: 2 (R20: 1)

### 429 按 key 分布

```
nv_key_idx | 429_nv_rate_limit
-----------+-------------------
         0 |     7
         1 |    14
         2 |     5
         3 |     5
         4 |     9
```

5 把 key 全部被限流，k1 最重 (14)，k4 次之 (9)。分布与 R20 一致 (k1/k4 最重)。

### Fallback 率

- 30min fallback 计数: 158 (R20: 164, -3.7%)
- Breaker: PRIMARY-BREAKER-SKIP-STREAM **持续 OPEN**
- 观测 PRIMARY-FAIL-STREAM: nv_gw 流式 502 after 64099ms
- 观测 FALLBACK-FAIL-STREAM: ms_gw 流式 timeout 30s (3 次)

### 健康检查

```
curl /health: {"status":"ok","proxy_role":"passthrough","nv_num_keys":5}
docker ps: nv_gw Up ~1h / hm4104 Up 5h / ms_gw Up 3d
```

## 核心判断

**NVCF 限流继续缓解。** Tier 429 从 48 降至 42 (-12.5%)，SR 从 45.9% 大幅回升至 86.2% (+40.3pp)。趋势延续 R19→R20 反弹后的再次回落，接近 R19 的 32 水平。pexec_success 继续增长 (14→18)，说明 nv_gw 本身无问题，根因仍在 NVCF 上游 rate limit。

按 R21 判断标准: Tier 429 在 30-49 区间，SR 86.2% > 50% → **巡检轮，限流持续但可控，继续等。**

Breaker 仍 OPEN，但 dsv4p_nv 实际成功数 25/29 说明通过 breaker 的请求大部分成功了（不成功的是 429/502）。breaker 不开合正常 —— 429 仍在，不符合闭合条件。

## 本轮改动

**无** (巡检轮，不改代码)

## 验证

- `curl /health` OK
- `docker ps`: nv_gw Up ~1h, hm4104 Up 5h, ms_gw Up 3d
- 不改代码，无需 restart

## 对比历史

| 指标 | R18 | R19 | R20 | R21 | 趋势 |
|------|-----|-----|-----|-----|------|
| dsv4p SR | 33.9% | 64.7% | 45.9% | **86.2%** | ↑↑ |
| Tier 429 | 49 | 32 | 48 | **42** | ↓ |
| pexec_success | 0 | 7 | 14 | **18** | ↑↑ |
| Fallback | 155 | 159 | 164 | **158** | → |
| Breaker | OPEN | OPEN | OPEN | **OPEN** | → |

## 下一步 (R22)

### 核心: 观察 Tier 429 能否继续下降至 < 30

R21 限流缓解趋势明确，R22 重点:
- 若 Tier 429 降至 < 30: 标注"限流缓解加速，接近 R19 水平"
- 若 Tier 429 降至 < 20 且 SR > 70%: 标注"NVCF 限流完全缓解，恢复正常"
- 若 breaker CLOSED 且 SR > 70%: 标注"完全恢复，可考虑回到优化模式"
- 若 429 反弹 > 49: 标注"NVCF 限流再次反弹"

### 不要做的事

- 不要重启 nv_gw (429 仍在，重启只清 breaker 不清 NVCF 限流)
- 不要改 KEY_COOLDOWN_S (180s 已保守)
- 不要改 TIER 配置 (5 把 key 全被限流，非 tier 路由问题)