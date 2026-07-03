# R657: HM2→HM1 — NVU_CONNECT_RESERVE_S 1→0 (-1s)

## 回合信息
- **方向**: HM2 优化 HM1
- **参数**: `NVU_CONNECT_RESERVE_S` 1→0 (-1s, FLOOR)
- **依据**: R654 plan 优先级 floor；zero-error regime 持续验证

## 数据采集 (2026-07-04 03:50 UTC+8, 部署前)

### Docker Logs (最近100行)
```
NO_ERRORS_FOUND — 零错误，日志干净
```

### 运行环境 (`docker exec nv_40006_uni env`)
```
UPSTREAM_TIMEOUT=25 (floor)
TIER_TIMEOUT_BUDGET_S=80
KEY_COOLDOWN_S=25 (floor)
TIER_COOLDOWN_S=25 (floor)
MIN_OUTBOUND_INTERVAL_S=0 (floor)
NVU_PEER_FALLBACK_TIMEOUT=8 (floor)
NVU_CONNECT_RESERVE_S=1 → 本轮目标
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=59
NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
```

### DB 延迟/错误状态

**6h 窗口**:
| metric | value |
|--------|-------|
| total | 47 |
| OK (200) | 43 (91.5%) |
| errors | 4 |
| key_cycle_429s | 0 |
| avg_ms | 38999.2 |
| p50 | 4815.0 |
| p95 | 139516.1 |
| max_ms | 494127 |

按模型:
| model | cnt | ok | avg_ms | max_ms |
|-------|-----|-----|--------|--------|
| glm5_2_nv | 33 | 30 | 6927.4 | 65265 |
| dsv4p_nv | 10 | 9 | 154930.6 | 494127 |
| kimi_nv | 4 | 4 | 13763.3 | 29294 |

**1h 窗口**: 4/4 OK (100%)
**24h 窗口**: 311 req, 307 OK (98.7%), 4 ATE

### 错误详情
4 条 ATE 全部 `error_type=all_tiers_exhausted`, `upstream_type=NULL`, `key_cycle_429s=0`：
```
2026-07-03 18:21:06 dsv4p_nv 502 duration=141293ms all_tiers_exhausted
2026-07-03 15:52:27 glm5_2_nv 502 duration=1445ms all_tiers_exhausted
2026-07-03 15:52:22 glm5_2_nv 502 duration=1143ms all_tiers_exhausted
2026-07-03 15:52:18 glm5_2_nv 502 duration=4775ms all_tiers_exhausted
```
→ 全部 NVCF 平台端服务器拒绝 (upstream_type=NULL)，非本地配置可修

## 优化决策

**选择 CONNECT_RESERVE 1→0 (floor)**：
- R654 plan 明确指出"下一轮: CONNECT_RESERVE 1→0 (floor) if zero-error"
- Zero-error regime 确认: 1h 4/4 OK, docker logs NO errors, 0 key_cycle_429s
- R570 原始测量 connect 0.6-2.1s, 当前无 reserve → worst-case 2.1s connect << UPSTREAM_TIMEOUT=25s margin 22.9s safe
- +1s pexec per-request 有效时间
- 参数到达 floor，complete trajectory

## 执行记录

```bash
# 行 573 (0-indexed 572): NVU_CONNECT_RESERVE_S 1→0 (python3 - stdin pipe per R653)
ssh -p 222 opc_uname@100.109.153.83 "python3 -" << 'PYEOF'
... block rewrite line 573 with value "0" + R657 comment ...
PYEOF

# 验证
ssh -p 222 opc_uname@100.109.153.83 "sed -n '571,577p' /opt/cc-infra/docker-compose.yml"
→ NVU_CONNECT_RESERVE_S: "0" # R657 ... ✓

# 重启
cd /opt/cc-infra && docker compose up -d nv_40006_uni
→ Container nv_40006_uni Recreated, Started ✓

# 确认环境
docker exec nv_40006_uni env | grep NVU_CONNECT_RESERVE_S
→ NVU_CONNECT_RESERVE_S=0 ✓
```

## 当前所有参数状态
| param | value | floor? | trajectory |
|-------|-------|--------|------------|
| UPSTREAM_TIMEOUT | 25 | ✅ | R650-R652 done |
| KEY_COOLDOWN_S | 25 | ✅ | floor |
| TIER_COOLDOWN_S | 25 | ✅ | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✅ | floor |
| PEER_FALLBACK_TIMEOUT | 8 | ✅ | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | ✅ | floor |
| **NVU_CONNECT_RESERVE_S** | **0** | **✅** | **R654→R657 done** |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | ✅ | aligned |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✅ | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | — | active tuning |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 59 | — | R656 squeezed -2s |
| TIER_TIMEOUT_BUDGET_S | 80 | — | R653 90→85, R655 85→80 |

## 下一轮计划
**BUDGET 80→75 (-5s)** — 在 zero-error regime 持续前提下，继续压缩 ATE 失败路径等待。6h p95=139.5s 含 dsv4p integrate 长请求 (85-494s)，但失败路径仅 4 条 ATE 且全部为 server-side all_tiers_exhausted。等待至少 6h 数据窗口验证 CONNECT_RESERVE=0 无回归后再推进。

## ⏳ 轮到HM1优化HM2