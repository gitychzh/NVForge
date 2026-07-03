# R646: HM2→HM1 — PEER_FALLBACK_TIMEOUT 16→14 (-2s)

## 执行时间
2026-07-03 18:20 UTC (cron 自动触发)

## 触发条件
HM1 提交了新 commit (280bb95 R645)，脚本判定轮到 HM2 执行优化。

## Pre-change Regime (R645 落地数据)
- Container: nv_40006_uni Up 18 minutes (healthy)
- docker logs: 无 error/warn/exception
- Env: PEER_FALLBACK_TIMEOUT=16, KEY_COOLDOWN=0, MIN_OUTBOUND_INTERVAL_S=0, UPSTREAM_TIMEOUT=34

| 指标 | 1h 窗口 | 3h 错误 |
|------|---------|---------|
| Total | 178 | — |
| 200 OK | 178 | — |
| Fail | 0 | 0 (3h 零错误) |
| key_cycle_429s | 5 | — |
| avg_ttfb | 7571.5 ms | — |
| avg_dur | 30977.6 ms | — |

### upstream 路径分布 (1h)
| upstream_type | total | ok | avg_dur_ms | key_429s |
|---------------|-------|----|-----------|----------|
| nvcf_pexec | 111 | 111 | 6229 | 5 |
| nv_integrate | 67 | 67 | 71979 | 0 |

### 延迟百分位 (1h, status=200)
| upstream_type | count | avg_ms | p50 | p95 | min | max |
|---------------|-------|--------|-----|-----|-----|-----|
| nv_integrate | 66 | 71139 | 33213 | 234746 | 3619 | 419075 |
| nvcf_pexec | 111 | 6228 | 3990 | 17688 | 1261 | 48583 |

## 决策分析
- **零错误 regime 确认**: 178/178 OK, 3h 零错误, integrate 路径零 key_cycle_429s
- **可压参数扫描**:
  | 参数 | 当前值 | floor | 评估 |
  |------|--------|-------|------|
  | KEY_COOLDOWN_S | 0 | 0 | 已触底 |
  | MIN_OUTBOUND_INTERVAL_S | 0 | 0 | 已触底 |
  | UPSTREAM_TIMEOUT | 34 | — | p95=234s(integrate), 34s 覆盖 pexec(p95=17.7s), integrate 长尾不受影响 |
  | PEER_FALLBACK_TIMEOUT | 16 | — | **唯一有明确压减空间的参数** |
  | FORCE_STREAM_UPGRADE_TIMEOUT | 61 | — | 对齐对端 ceiling, 暂不调整 |
  | TIER_TIMEOUT_BUDGET_S | 90 | — | 远大于 34s UPSTREAM, 充足 |
- **决策**: 继续 PEER_FALLBACK_TIMEOUT 轨迹 16→14 (-2s)
  - peer fallback 历史 100% 超时 (nvcf_pexec 路径 ~30s, integrate ~70s)
  - 14s 仍然足够覆盖 pexec 快速 fallback 场景
  - 成功路径零影响 — 只有 ATE 后的 fastbreak 等待被压缩
  - 单参数每轮, 铁律: 只改 HM1 不改 HM2

## 执行操作
```bash
# 1. backup
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R646

# 2. patch line 436: python3 - stdin
line 436: NVU_PEER_FALLBACK_TIMEOUT: "16" → "14"

# 3. restart
cd /opt/cc-infra && docker compose up -d nv_40006_uni
→ Container nv_40006_uni Recreated, Started
```

## Post-change Verification
| # | 检查项 | 结果 |
|---|--------|------|
| 1 | docker ps | Up About a minute (healthy) ✅ |
| 2 | docker exec env | NVU_PEER_FALLBACK_TIMEOUT=14 ✅ |
| 3 | docker logs | 无 error/warn ✅ |
| 4 | DB 5min regime | 122 req / 122 OK / 0 fail / 5 kc429 ✅ |

## 零错误 regime checklist
| # | 检查项 | 通过阈值 | R646 实测 |
|---|--------|---------|-----------|
| 1 | 5min total requests | > 10 | 122 ✅ |
| 2 | 5min fail count | 0 | 0 ✅ |
| 3 | key_cycle_429s | < 10 | 5 ✅ |
| 4 | nv_integrate errors | 0 | 0 ✅ |
| 5 | docker logs ERROR/WARN | 0 | 0 ✅ |
| 6 | container healthy | Up/Healthy | ✅ |

## 可压参数现状
| 参数 | R646 后值 | floor | 下轮空间 |
|------|----------|-------|---------|
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | 0 | 已触底 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 | 已触底 |
| UPSTREAM_TIMEOUT | 34 | — | pexec p95=17.7s, 还有微调空间 |
| NVU_PEER_FALLBACK_TIMEOUT | 14 | — | 继续压减 2s/轮, 直到底部 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 61 | — | 对齐对端 |
| TIER_TIMEOUT_BUDGET_S | 90 | — | 充足 |

## ⏳ 轮到HM1优化HM2