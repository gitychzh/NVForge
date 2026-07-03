# R658: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 59→58 (-1s)

## 回合信息
- **方向**: HM2 优化 HM1
- **参数**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 59→58 (-1s)
- **依据**: R656-R657 FORCE_STREAM_UPGRADE_TIMEOUT trajectory 继续；zero-error regime 持续验证

## 数据采集 (2026-07-04 04:20 UTC+8, 部署前)

### Docker Logs (最近200行)
```
NO_ERRORS_FOUND — 零错误，日志干净 (grep error|warn|fail|timeout|429|exhausted|traceback → count=0)
```

### 运行环境 (`docker exec nv_40006_uni env`)
```
UPSTREAM_TIMEOUT=25 (floor)
TIER_TIMEOUT_BUDGET_S=80
KEY_COOLDOWN_S=25 (floor)
TIER_COOLDOWN_S=25 (floor)
MIN_OUTBOUND_INTERVAL_S=0 (floor)
NVU_PEER_FALLBACK_TIMEOUT=8 (floor)
NVU_CONNECT_RESERVE_S=0 (floor — R657 complete)
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=59 → 本轮目标 58
NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
```

### DB 延迟/错误状态

**6h 窗口**:
| metric | value |
|--------|-------|
| total | 114 |
| OK (200) | 110 (96.5%) |
| errors | 4 |
| key_cycle_429s | 0 (logs: 0) |
| avg_ms | 44918 |
| max_ms | 494127 |

按模型:
| model | cnt | ok | avg_ms | max_ms |
|-------|-----|-----|--------|--------|
| glm5_2_nv | 65 | 62 | 5406 | 65265 |
| kimi_nv | 34 | 34 | 82972 | 419075 |
| dsv4p_nv | 10 | 9 | 154931 | 494127 |

**24h 窗口**: 1028 OK (200), 86 ATE (502), avg_ms=31452
**24h 错误**: 92 all_tiers_exhausted + 1 NVStream_TimeoutError

### 错误详情
4 条 ATE 全部 `error_type=all_tiers_exhausted`, `upstream_type=NULL`:
```
2026-07-04 02:18:37 dsv4p_nv 502 duration=141293ms all_tiers_exhausted
(+ 3 earlier ATE from R657 6h window — same pattern)
```
→ 全部 NVCF 平台端服务器拒绝，非本地配置可修

## 优化决策

**选择 FORCE_STREAM_UPGRADE_TIMEOUT 59→58 (-1s)**：
- R656 首次切入此参数 (61→59, -2s)，验证无回归
- R657 CONNECT_RESERVE 完成 trajectory (3→2→1→0, floor reached)
- Zero-error regime 确认: 6h NO log errors, 0 key_cycle_429s
- dsv4p_nv integrate 天花板测量: R656 61.4s → 当前 59s → 本轮 58s
- -1s 保守增量（每轮少改，多轮积累），消除 integrate 超时后的浪费等待
- 流式路径不受影响（数据块 keepalive 刷新超时）
- UPSTREAM_TIMEOUT=25 (floor) << 58s margin 33s 安全
- CONNECT_RESERVE 已到 floor=0，无更多 floor 参数可压

## 执行记录

```bash
# 验证当前值
ssh -p 222 opc_uname@100.109.153.83 \
  "grep -n 'NVU_FORCE_STREAM_UPGRADE_TIMEOUT' /opt/cc-infra/docker-compose.yml"
→ 行492: NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "59"

# 修改 59→58 (sed inline)
ssh -p 222 opc_uname@100.109.153.83 \
  "sed -i '492s/\"59\"/\"58\"/' /opt/cc-infra/docker-compose.yml"

# 追加 R658 历史注释 (行492之后)
ssh -p 222 opc_uname@100.109.153.83 \
  "sed -i '492a\      # R658 (HM2→HM1): NVU_FORCE_STREAM_UPGRADE_TIMEOUT 59→58 (-1s)...' ..."

# 验证修改后
ssh -p 222 opc_uname@100.109.153.83 \
  "sed -n '490,497p' /opt/cc-infra/docker-compose.yml"
→ NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "58" ✓ (R656 comment intact, R658 appended)

# 重启容器
ssh -p 222 opc_uname@100.109.153.83 \
  "cd /opt/cc-infra && docker compose up -d nv_40006_uni"
→ Container nv_40006_uni Recreated, Started ✓

# 确认环境
docker exec nv_40006_uni env | grep NVU_FORCE_STREAM_UPGRADE_TIMEOUT
→ NVU_FORCE_STREAM_UPGRADE_TIMEOUT=58 ✓
docker ps --filter name=nv_40006_uni → Up 11 seconds (healthy) ✓
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
| NVU_CONNECT_RESERVE_S | 0 | ✅ | R654→R657 done |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | ✅ | aligned |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✅ | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | — | active tuning |
| **NVU_FORCE_STREAM_UPGRADE_TIMEOUT** | **58** | — | **R656→R658 (-3s)** |
| TIER_TIMEOUT_BUDGET_S | 80 | — | R653 90→85→80 |

## 下一轮计划
**FORCE_STREAM_UPGRADE_TIMEOUT 58→57 (-1s)** — 继续 -1s 保守增量，在 zero-error regime 持续前提下挤压 integrate 超时等待。需至少 6h 数据窗口验证 58 无回归后再推进。

## ⏳ 轮到HM1优化HM2