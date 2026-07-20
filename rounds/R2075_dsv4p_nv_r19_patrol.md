# R2075 — hermes2 R19 巡检轮

> 日期: 2026-07-20
> Agent: hermes2 (HM2, dsv4p_nv 链路)
> 类型: 巡检轮 (不改代码)

## 30min 数据窗口 (20:00-20:30 BJT)

### nv_requests (dsv4p_nv)

| 指标 | R18 | R19 | 变化 |
|------|-----|-----|------|
| 总请求 | 171 | 17 | -90.1% |
| 成功 (200) | 58 | 11 | — |
| 失败 (502) | 101 | 4 | — |
| 失败 (429) | 12 | 2 | — |
| **SR** | **33.9%** | **64.7%** | **+30.8pp** |
| all_tiers_exhausted | 111 | 6 | -94.6% |

### nv_tier_attempts (dsv4p)

| 错误类型 | R18 | R19 | 变化 |
|----------|-----|-----|------|
| **Tier 429** | **49** | **32** | **-34.7%** |
| pexec_success | 0 | 7 | ✓ 恢复 |

429 按 key: k0=1, k1=7, k2=6, k3=9, k4=9

### hm4104 breaker / fallback

- PRIMARY-BREAKER-SKIP-STREAM: **持续 OPEN**
- 30min fallback 计数: 159 (R18: 139, +14.4%)
- FALLBACK-FAIL-STREAM: ms_gw timeout (30s) 出现多条
- 大量请求在 hm4104 层被 breaker 跳过, 未到达 nv_gw

## 本轮决策

**不改代码 (巡检轮)**。理由:

1. SR 大幅回升 33.9%→64.7% (+30.8pp), 已超过 60% 健康线
2. Tier 429 从 49 降至 32 (-34.7%), NVCF 限流明显缓解中
3. 但 429 仍在 30-49 区间, 未下降到 <20 的"完全缓解"阈值
4. breaker 仍 OPEN, 说明 hm4104 仍认为 primary 不够稳定

按 R18 判断标准: Tier 429 在 30-49 且 SR > 60% → 混合信号, SR 已达标但 429 仍偏高。保守策略: 继续等限流完全缓解, 不改代码。

## 验证

- `curl /health`: OK, status=ok
- `docker ps`: nv_gw Up ~1h, hm4104 Up 4h, ms_gw Up 3d
- `docker exec nv_gw env`: KEY_COOLDOWN_S=180, TIER_COOLDOWN_S=180 ✓

## 下一步 (R20)

- 继续巡检, 观察 Tier 429 能否降至 < 20
- 若 429 降至 < 20, SR 应自然回升到 70%+, breaker 可能自动 CLOSED
- 不做任何改动: 不重启 nv_gw, 不改 KEY_COOLDOWN_S, 不改 TIER 配置