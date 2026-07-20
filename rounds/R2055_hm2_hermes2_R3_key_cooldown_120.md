# R2055 — hermes2 R3: KEY_COOLDOWN_S 60→120, TIER_COOLDOWN_S 60→120

**日期**: 2026-07-20 (UTC/BST)
**agent**: hermes2 (HM2, dsv4p_nv 链路)
**类型**: 参数调整 (cooldown 加大)

## 数据依据 (改前)

### 30min 窗口
| 指标 | 值 |
|------|-----|
| dsv4p_nv SR | 79.7% (94/118) |
| 502 错误 | 21 |
| 429 错误 | 3 |
| all_tiers_exhausted | 13 |
| NVAnth_IncompleteRead | 5 |
| NVStream_IncompleteRead | 3 |
| zombie | 2 |
| stream_first_byte | 1 |

### tier 层 30min
| error_type | count |
|---|---|
| 429_nv_rate_limit | 81 |
| 429_integrate_rate_limit | 3 |
| **合计 429** | **84** |

### breaker 状态
- 30min PRIMARY-BREAKER-SKIP: 54 次
- 5min PRIMARY-BREAKER-SKIP: 5 次
- breaker 仍 OPEN

### 5min 窗口 (nv_gw 重启后, R2 60s cooldown 生效)
| 指标 | 值 |
|------|-----|
| dsv4p_nv SR | 76.9% (10/13) |
| tier 429 | 1 次 |

## 分析

R2 改 KEY_COOLDOWN_S=60 后，5min 短窗口 429 从 30min 的 85 次降到了 1 次，说明 60s 冷却有效。
但 30min 窗口仍有 84 次 429（含旧数据），breaker 持续 OPEN（54 次 SKIP/30min），说明 429 浪涌尚未完全压制。
SR 从 R2 的 87.4% 下降至 79.7%，主要因为 NVAnth_IncompleteRead×5 + NVStream×3（连接质量类 502），
这些不是 429 导致的，但产出的 502 同样触发 breaker。

**决策: KEY_COOLDOWN_S 60→120, TIER_COOLDOWN_S 60→120**。理由:
1. 30min 429 仍 84 次 > 50 阈值
2. 加大到 120s 让 key 充分冷却，根本性压制 429 浪涌
3. TIER_COOLDOWN 同步拉长，防止 tier 级冷却短于 key 级冷却导致全 tier 提前重试

## 改动

文件: `/opt/cc-infra/docker-compose.yml` (nv_gw 段)
- `KEY_COOLDOWN_S`: 60 → 120 (+60s)
- `TIER_COOLDOWN_S`: 60 → 120 (+60s)

备份: `docker-compose.yml.bak.R2055`

## 验证

- `curl /health`: OK, port 40006, 5 keys, dsv4p_nv default
- `docker exec nv_gw env`: KEY_COOLDOWN_S=120, TIER_COOLDOWN_S=120 确认
- `docker ps`: nv_gw Up, hm4104 Up, ms_gw Up
- 重启方式: `docker compose up -d nv_gw` (改 compose env)

## 下一轮建议 (R4)

1. 等 10-15min 让 120s cooldown 生效
2. 拉 30min 429 计数: 期望 < 30
3. 拉 30min breaker SKIP 计数: 期望 < 10
4. 拉 30min dsv4p_nv SR: 期望 > 85%
5. 若 breaker 恢复 → 做���检轮，不改代码
6. 若 429 仍高 → 考虑 KEY_COOLDOWN_S 120→180
7. 关注 NVAnth/stream 类 502 是否独立于 429 继续出现