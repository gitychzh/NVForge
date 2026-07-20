# R35: hermes2 — TIER_COOLDOWN_S 180→60, 匹配 KEY_COOLDOWN_S=60

> 时间: 2026-07-20 23:52 UTC+8
> 轮次: R35 (git commit R2094)
> 上一轮: R34 (R2093, KEY_COOLDOWN_S 180→60)

## 30min 数据 (R35 改前)

| 指标 | 值 |
|------|-----|
| 总请求 | 29 |
| 200 OK | 13 |
| 502 | 13 |
| 429 | 3 |
| **SR** | **44.8%** (R34: 55.2%, ↓10.4pp) |
| 失败分类 | 16× all_tiers_exhausted (100%) |
| Tier 429 | 17 |
| Fallback 总次数 | 181 (R34: 153, ↑18%) |

### Key 分布

| key_idx | 200 | 502 | 429 |
|---------|-----|-----|-----|
| 4 (k5) | 12 | 12 | 0 |
| NULL | 0 | 0 | 3 |

**仅 k5 有成功 (12/12)，其他 key 全 429。**

## 诊断: TIER_COOLDOWN_S 是瓶颈

nv_gw 日志揭示关键瓶颈:

```
[NV-COOLDOWN] tier=dsv4p_nv k2 marked cooling after 429
[NV-COOLDOWN] tier=dsv4p_nv k3 marked cooling after 429
[NV-COOLDOWN] tier=dsv4p_nv k4 marked cooling after 429
[NV-COOLDOWN] tier=dsv4p_nv k5 marked cooling after 429
[NV-COOLDOWN] tier=dsv4p_nv k1 marked cooling after 429
[NV-TIER] tier=dsv4p_nv all keys in cooldown/auth-failed, breaking
[NV-GLOBAL-COOLDOWN] tier=dsv4p_nv all keys 429. Marking all cooling 180s (TIER_COOLDOWN)
```

**全 5 key 都 429 → 触发 NV-GLOBAL-COOLDOWN 180s → 所有请求被 "NV-TIER-SKIP all keys in cooldown" 跳过。**

R34 的 KEY_COOLDOWN_S=60 形同虚设 — 单 key 60s 后恢复，但 TIER_COOLDOWN_S=180s 全局锁还有 120s 剩余，所有请求被 tier 级跳过，单个 key 根本没机会重试。

## 改动: TIER_COOLDOWN_S 180→60

```diff
- TIER_COOLDOWN_S=180    # R7: 120→180
+ TIER_COOLDOWN_S=60     # R35: 180→60, 匹配 KEY_COOLDOWN_S=60
```

**文件**: `/opt/cc-infra/docker-compose.yml` (nv_gw 段)
**备份**: docker-compose.yml.bak.R35

## 验证

- `curl /health`: `{"status": "ok"}` ✓
- `docker ps`: nv_gw Up ✓
- `docker exec nv_gw env`: TIER_COOLDOWN_S=60, KEY_COOLDOWN_S=60 ✓

## 十轮 502/SR 趋势 (R26-R35)

| 轮次 | 502 | SR | Tier 429 | 判断 |
|------|-----|-----|----------|------|
| R26 | 6 | 73.1% | 57 | 持续恢复 |
| R27 | 9 | 55.0% | 28 | 恶化 |
| R28 | 10 | 50.0% | 22 | 恶化 |
| R29 | 11 | 35.3% | 13 | 触发阈值 |
| R30 | 112 | 9.0% | 6 | 误判"502灾难" |
| R31 | 143 | 0% | 5 | 确诊: 400 DEGRADED |
| R32 | 161 | 0% | 0 | 持续 DEGRADED |
| R33 | 9 | 0% | 0 | 持续 DEGRADED, breaker OPEN |
| R34 | 12 | 55.2% | 25 | DEGRADED 清除, KEY_COOLDOWN=60 |
| **R35** | **13** | **44.8%** | **17** | **429全key+TIER_COOLDOWN=180瓶颈** |

## 结论

R35 发现 KEY_COOLDOWN_S=60 改后 SR 反而从 55.2% 降到 44.8%，fallback 从 153 升到 181。
根因是 TIER_COOLDOWN_S=180s 全局锁：全 5 key 429 后触发 NV-GLOBAL-COOLDOWN 180s，在 180s 内
所有请求被 tier 跳过，单 key 的 60s 冷却恢复根本用不上。现在将 TIER_COOLDOWN_S 同步降到 60s，
让 key 冷却和 tier 冷却窗口一致，打破 "全 key 429 → 180s 全局锁死 → 恢复后立即再 429" 的死循环。

下一轮(R36)验证: k1-k4 是否恢复工作，SR 能否回升到 55%+。