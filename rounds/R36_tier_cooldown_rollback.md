# hermes2 R36 — TIER_COOLDOWN_S 60→180 回退: NVCF key 配额耗尽, 全5key 429, SR=0%

## 数据 (30min 窗口, 2026-07-20 23:30-00:00 BJT)

### dsv4p_nv 请求 (nv_requests)
| request_model | status | count |
|---------------|--------|-------|
| dsv4p_nv      | 502    | 12    |
| dsv4p_nv      | 429    | 2     |

- **总请求: 14, 成功: 0, SR=0%** (R35: 44.8%, ↓44.8pp)
- 全部 14 失败 = `all_tiers_exhausted`
- tier 层面: `nv_tier_attempts` 30min 无记录 (可能表结构不同��写入延迟)

### nv_gw 日志关键信号
- **NV-SUCCESS: 0** (R35: 13 次成功, 含 k5 12/12)
- **NV-GLOBAL-COOLDOWN: 6 次** (R35: 同量级, 但 TIER_COOLDOWN=60s 下频率更高)
- **429: 56 次** (R35: 同量级)
- **NV-TIER-SKIP: 大量** — 全 key 冷却中, 所有请求被跳过
- **无 400 DEGRADED** — NVCF function 本身正常, 纯 429 限流
- 全 5 key 429, 连 R35 唯一工作的 k5 也挂了

### hm4104 fallback
- **fallback 总次数: 231** (R35: 181, ↑27.6%)
- PRIMARY-BREAKER-SKIP-STREAM: circuit OPEN, 直走 ms_gw
- 偶有 PRIMARY-FAIL-STREAM 502 after 7ms

## 诊断

**R35 的 TIER_COOLDOWN_S=60 适得其反。** 逻辑上是对的: 全 key 429 后让 tier 全局冷却与 key 冷却同步, 消除"key 好了但 tier 还锁着"的死窗。但现实中:

1. NVCF 对 dsv4p 的 key 配额极紧 — 全 5 key 同时 429
2. TIER_COOLDOWN=60s 意味着每 60s 就解除全局锁, 让请求涌入 → 所有 key 立即再 429 → 再触发 NV-GLOBAL-COOLDOWN
3. 这个循环反而增加了 NVCF 的 429 压力, 加速配额耗尽
4. 结果: 连 R34/R35 唯一工作的 k5 也挂了, SR 从 44.8% 暴跌到 0%

**根因: 不是冷却参数的问题, 是 NVCF key 配额问题。** dsv4p_nv 的 5 个 key 的 RPM/TPM 配额不足以支撑正常流量。无论 TIER_COOLDOWN 是 60 还是 180, 只要流量超过配额就全 429。TIER_COOLDOWN=180 至少能降低重试频率, 减少对 NVCF 的压力。

## 改动

**回退: TIER_COOLDOWN_S 60→180** (docker-compose.yml nv_gw 段)

```diff
- TIER_COOLDOWN_S=60   # R35
+ TIER_COOLDOWN_S=180  # R36 回退
```

KEY_COOLDOWN_S 保持 60 (R34), 不改。

## 验证

- `curl /health`: OK, status=ok
- `docker ps`: nv_gw Up
- `docker exec nv_gw env | grep TIER_COOLDOWN_S`: **180** ✓
- `docker exec nv_gw env | grep KEY_COOLDOWN_S`: 60 ✓
- nv_gw 日志: 正常启动, 有请求进来, k4/k5 立即 429 (确认配额问题)

## 结论

**NVCF dsv4p key 配额不足, 参数调优已到天花板。** 冷却参数 (KEY_COOLDOWN / TIER_COOLDOWN) 只能控制重试节奏, 不能增加配额。当前 5 key 中无一能稳定工作, 任何流量都会触发全 key 429。

**下一步建议:**
1. **人为检查 NVCF dsv4p function 的 key 配额** — 每个 key 的 RPM/TPM limit, 是否被其他用户共享
2. 如果配额无法增加, 考虑减少并发请求、增加请求间隔 (MIN_OUTBOUND_INTERVAL_S)
3. 如果配额是 NVCF 平台级限制, 当前 dsv4p_nv 不可用, hm4104 breaker OPEN 走 ms_gw 是正确行为

## 趋势

| 轮次 | 502 | SR | Tier 429 | 判断 |
|------|-----|-----|----------|------|
| R31 | 143 | 0% | 5 | 400 DEGRADED |
| R32 | 161 | 0% | 0 | 持续 DEGRADED |
| R33 | 9 | 0% | 0 | breaker OPEN |
| R34 | 12 | 55.2% | 25 | DEGRADED清除, KEY_COOLDOWN=60 |
| R35 | 13 | 44.8% | 17 | TIER_COOLDOWN=60 |
| **R36** | **12** | **0%** | **N/A** | **全key 429, 回退180** |