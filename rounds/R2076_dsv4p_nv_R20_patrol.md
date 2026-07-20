# R2076 (hermes2 R20): 巡检轮 — NVCF 限流反弹, SR 45.9%, Tier 429 回升至 48

## 本轮改了

无 (巡检轮, 不改代码)

## 数据依据

### 30min dsv4p_nv 请求层

| mapped_model | status | count |
|-------------|--------|-------|
| dsv4p_nv    | 502    | 54    |
| dsv4p_nv    | 200    | 51    |
| dsv4p_nv    | 429    | 6     |

- 总请求: 111 (R19: 17, +553% — 新增流量, 涵盖巡检周期内所有请求)
- 成功: 51 (200)
- **SR = 45.9%** (R19: 64.7%, **-18.8pp**)

### 错误分类 (nv_requests)

| error_type            | count |
|-----------------------|-------|
| all_tiers_exhausted   | 58    |
| zombie_empty_completion | 2    |

### Tier 层 (nv_tier_attempts)

| error_type           | count | R19 对比 |
|----------------------|-------|----------|
| 429_nv_rate_limit    | 48    | 32 (+50.0%) |
| pexec_success        | 14    | 7 (+100%) |
| empty_200            | 3     | 0 (新增) |
| pexec_conn_RemoteDisconnected | 1 | 0 (新增) |

### 429 按 key 分布

| key_idx | 429 count | R19 对比 |
|---------|-----------|----------|
| 0       | 6         | 1 (+500%) |
| 1       | 14        | 7 (+100%) |
| 2       | 6         | 6 (持平) |
| 3       | 9         | 9 (持平) |
| 4       | 13        | 9 (+44%) |

5 把 key 全部被限流, k1/k4 最重, k0/k1 增幅最大。

### Fallback 率

- 30min fallback: 164 (R19: 159, +3.1%)
- breaker: PRIMARY-BREAKER-SKIP-STREAM 持续 OPEN
- 观测到 PRIMARY-FAIL-STREAM: nv_gw 流式 502 after 120989ms (个别长请求超时)

## 核心判断

**NVCF 限流反弹**。R19 的缓解趋势被逆转:

| 指标 | R18 | R19 | R20 | 趋势 |
|------|-----|-----|-----|------|
| SR   | 33.9% | 64.7% | 45.9% | ↓ 反弹 |
| Tier 429 | 49 | 32 | 48 | ↑ 反弹 |
| Fallback | 139 | 159 | 164 | ↑ 持续 |
| pexec_success | 0 | 7 | 14 | ↑ 恢复 |

- Tier 429 从 32 反弹至 48 (+50%), 接近 R18 的 49
- SR 从 64.7% 跌至 45.9% (-18.8pp), 跌破 50% 健康线
- pexec_success 翻倍 (7→14), 说明 nv_gw 本身没问题, 问题是 429 率太高
- 按 R19 判断标准: 429 在 30-49 区间但 SR < 50% — 限流反弹, 继续巡检

## 验证

- `curl /health` OK
- `docker ps`: nv_gw Up ~1h / hm4104 Up 4h / ms_gw Up 3d
- `docker exec nv_gw env`: KEY_COOLDOWN_S=180 ✓

## 下一步 (R21)

- 继续巡检, 观察 Tier 429 是否继续反弹 (>49) 或重新回落
- 若 429 > 49: 标注"NVCF 限流恶化, 回到 R18 水平"
- 若 429 回落至 < 30: 标注"限流再次缓解"
- **不要重启 nv_gw, 不要改 KEY_COOLDOWN_S**
- 若连续 2 轮 429 > 40: 考虑联系 NVCF 侧