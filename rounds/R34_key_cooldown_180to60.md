# R34: KEY_COOLDOWN_S 180→60 — NVCF DEGRADED 已清除, 429 cooldown 过长致单 key 工作

## 数据依据 (改前 30min 窗口, 23:00-23:30)

### DB 数据
```
request_model | status | count
---------------+--------+-------
 dsv4p_nv      |    200 |    16
 dsv4p_nv      |    502 |    12
 dsv4p_nv      |    429 |     1
```
- 总请求 29, 成功 16, **SR=55.2%**
- 全部 13 失败 = `all_tiers_exhausted`

### Tier 层面
```
error_type        | count
------------------+-------
 429_nv_rate_limit|    25
 pexec_success    |     2
```

### NVCF DEGRADED 状态
- **最后一条 "DEGRADED function" 在 23:17:06** (R34 窗口前半段)
- 23:17 之后零 400 DEGRADED, NVCF 平台已恢复
- 但 30min 内仍有 14 条 DEGRADED 日志 (前半段残留)

### Key 分布
- **k5: 24/24 成功** (全部 success 都在 k5)
- k1-k4: 全部 429 → cooldown 180s → 死循环
- k1: 5 次 auth-failed skip, k2: 11, k3: 15, k4: 20
- 30min 内 48 次 COOLDOWN, 123 次 ALL-TIERS-FAIL vs 24 次 SUCCESS

### hm4104
- BREAKER-SKIP: 59, PRIMARY-FAIL: 13, FALLBACK-STREAM: 65, FALLBACK-FAIL: 8
- fallback 总次数: 153

## 诊断

1. **NVCF DEGRADED 已清除** — 23:17:06 之后零 400 DEGRADED, function 已恢复正常
2. **新问题: 429 单 key 独木桥** — k1-k4 全部 429 rate limit, 只有 k5 能通
3. **根因: KEY_COOLDOWN_S=180 太长** — 5 个 key 一轮 429 全进 cooldown 180s, 整个 tier 死 3 分钟。只有 k5 偶尔在 cooldown 过期后第一个被尝试、成功, 其他 key 恢复后立刻又 429
4. 180s 冷却 + 5 key 的 429 循环 → 全 tier 死 3min / 活 1 次成功 / 再死 3min 的脉冲模式

## 改动

- **参数**: `KEY_COOLDOWN_S` 180 → 60
- **文件**: `/opt/cc-infra/docker-compose.yml` (nv_gw 段, line 34)
- **备份**: `docker-compose.yml.bak.R34`
- **重启**: `docker compose up -d nv_gw` (改 compose env, 用 up -d)

## 验证

- `curl /health`: OK
- `docker ps`: nv_gw Up
- `docker exec nv_gw env | grep KEY_COOLDOWN_S`: **60** ✓
- nv_gw/hm4104/ms_gw/logs_db 全部 Up

## 预期效果

- KEY_COOLDOWN_S=60 让 key 从 429 冷却 60s (而非 180s) 后恢复
- 5 key 循环 429 时, 更短的冷却减少 "全 key 冷却中" 窗口
- 预期 SR 从 55.2% → 70%+ (更多 key 可用, 减少 all_tiers_exhausted)

## 风险

- 若 NVCF 仍有限流压力, 60s 冷却可能不够, 导致 429 更频繁
- 若出现 429 循环加剧, 可回退到 90s 或 120s 中间值
- R35 需验证: 若 SR 下降或 429 增多, 回退

## 九轮趋势 (R26-R34)

| 轮次 | 502 | SR | Tier 429 | 判断 |
|------|-----|-----|----------|------|
| R26 | 6 | 73.1% | 57 | 持续恢复 |
| R27 | 9 | 55.0% | 28 | 恶化 |
| R28 | 10 | 50.0% | 22 | 恶化 |
| R29 | 11 | 35.3% | 13 | 触发阈值 |
| R30 | 112 | 9.0% | 6 | 误判为"502灾难" |
| R31 | 143 | 0% | 5 | 确诊: 400 DEGRADED |
| R32 | 161 | 0% | 0 | 持续 DEGRADED |
| R33 | 9 | 0% | 0 | 持续 DEGRADED, breaker OPEN |
| **R34** | **12** | **55.2%** | **25** | **DEGRADED 已清除! 429 单 key 独木桥** |

## 本轮结论

NVCF DEGRADED 已清除 (23:17 最后一条), SR=55.2% 但仅 k5 工作。KEY_COOLDOWN_S 180→60 降低全 key 冷却窗口。下一轮需验证: 若 k1-k4 恢复 + SR 上升到 70%+, 继续优化; 若 429 反而加剧, 回退到 90-120s。