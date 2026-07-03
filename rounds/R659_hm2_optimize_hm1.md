# R659: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 58→57 (-1s)

## 回合信息
- **方向**: HM2 优化 HM1
- **参数**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 58→57 (-1s)
- **依据**: R656-R658 FORCE_STREAM_UPGRADE_TIMEOUT trajectory 继续 (61→59→58→57, -4s total)；zero-error regime 持续验证

## 数据采集 (2026-07-04 04:45 UTC+8, 部署前)

### Docker Logs (最近200行)
```
NO_ERRORS_FOUND — 零错误，日志干净 (grep error|warn|fail|timeout|429|exhausted|traceback → 0 matches)
容器启动日志正常: [NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv)
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
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=58 → 本轮目标 57
NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
```

### DB 延迟/错误状态

**6h 窗口**:
|| metric | value |
||--------|-------|
|| total | 102 |
|| OK (200) | 98 (96.1%) |
|| fail (!=200) | 4 (all ATE) |
|| with_error | 4 |
|| key_cycle_429s | 1 (minor, successful req normal rotation) |
|| fallback | 0 |
|| avg_dur_ms | 44754 |
|| max_dur_ms | 494127 (dsv4p_nv integrate streaming tool_calls, normal) |
|| avg_ttfb_ms | 13565 |
|| max_ttfb_ms | 107730 (same long streaming request) |

**最近10条请求**: 全部 200 OK, duration 1636-6549ms, ttfb 同步, 0 errors, 0 kc429, 0 fallback

**错误详情 (4 ATE)**:
```
2026-07-04 02:18:37 502 duration=141293ms all_tiers_exhausted all_tiers_failed_in_mapped_tier upstream_type=NULL
2026-07-03 23:52:23 502 duration=1445ms   all_tiers_exhausted all_tiers_failed_in_mapped_tier upstream_type=NULL
2026-07-03 23:52:19 502 duration=1143ms   all_tiers_exhausted all_tiers_failed_in_mapped_tier upstream_type=NULL
2026-07-03 23:52:12 502 duration=4775ms   all_tiers_exhausted all_tiers_failed_in_mapped_tier upstream_type=NULL
```
→ 全部 NVCF 平台端服务器拒绝 (upstream_type=NULL 调度层直接拒)，非本地配置可修

**Top5 duration (正常成功请求)**:
```
494127ms dsv4p_nv nv_integrate stream=t tool_calls (long-thinking, normal)
419075ms kimi_nv  nv_integrate stream=t tool_calls
362147ms kimi_nv  nv_integrate stream=t stop
319381ms dsv4p_nv nv_integrate stream=t tool_calls
290632ms kimi_nv  nv_integrate stream=t tool_calls
```
→ 全部 integrate streaming 长时请求，data flow keepalive 保持 read-timeout 活跃，不受 FORCE_STREAM_UPGRADE_TIMEOUT 影响

## 优化决策

**选择 FORCE_STREAM_UPGRADE_TIMEOUT 58→57 (-1s)**：
- R656 首次切入此参数 (61→59, -2s)，R657 验证, R658 继续 (59→58)，trajectory 稳定
- Zero-error regime 确认: 6h NO log errors, kc429 仅 1 (正常轮转), 0 fallback
- 4 ATE 全部 server-side all_tiers_exhausted (upstream_type=NULL)，非配置可修
- dsv4p_nv integrate 天花板测量: R656 61.4s → R658 58s → 本轮 57s (-1s 保守)
- -1s 保守增量（每轮少改，多轮积累），消除 integrate 超时后的浪费等待
- 流式路径不受影响（数据块 keepalive 刷新超时）
- UPSTREAM_TIMEOUT=25 (floor) << 57s margin 32s 安全
- CONNECT_RESERVE 已到 floor=0，所有主参数均在 floor
- 长时 streaming 请求 (290-494s) 不受 FORCE_STREAM_UPGRADE_TIMEOUT 限制，因 data flow 持续刷新 read-timeout

## 执行记录

```bash
# 1. 备份 compose
ssh -p 222 opc_uname@100.109.153.83 \
  "cd /opt/cc-infra && cp docker-compose.yml docker-compose.yml.bak.R659"

# 2. 修改值 58→57 (line-addressed sed, value-only substitution)
ssh -p 222 opc_uname@100.109.153.83 \
  "cd /opt/cc-infra && sed -i '/NVU_FORCE_STREAM_UPGRADE_TIMEOUT:.*\"58\"/s/\"58\"/\"57\"/' docker-compose.yml"

# 3. 更新注释 R658→R659 (curly-brace block, comment-only rewrite)
ssh -p 222 opc_uname@100.109.153.83 \
  "cd /opt/cc-infra && sed -i '/# R658 (HM2→HM1): NVU_FORCE_STREAM_UPGRADE_TIMEOUT/ {
    s/# R658.*$/# R659 (HM2→HM1): NVU_FORCE_STREAM_UPGRADE_TIMEOUT 58→57 (-1s). R656-R658 trajectory continued (61→59→58→57, -4s total); 6h 102req\/98OK 96.1% zero-error regime (0 log errors 1 kc429 minor); 4 ATE all server-side NVCF all_tiers_exhausted non-config fixable; dsv4p_nv integrate ceiling squeezed 58→57 (-1s conservative); streaming keepalive paths unaffected; UPSTREAM_TIMEOUT=25 << 57s margin 32s safe; CONNECT_RESERVE at floor=0; single param per round; iron rule: only change HM1 never HM2/
  }' docker-compose.yml"

# 4. 验证修改后
ssh -p 222 opc_uname@100.109.153.83 \
  "sed -n '491,494p' /opt/cc-infra/docker-compose.yml"
→ 行492: NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "57" ✓ (R656 inline comment intact)
→ 行493: # R659 (HM2→HM1): ... 58→57 (-1s) ... ✓

# 5. 重启容器 (docker compose up -d, NOT docker restart)
ssh -p 222 opc_uname@100.109.153.83 \
  "cd /opt/cc-infra && docker compose up -d nv_40006_uni"
→ Container nv_40006_uni Recreated, Started ✓

# 6. 确认环境
docker exec nv_40006_uni env | grep NVU_FORCE_STREAM_UPGRADE_TIMEOUT
→ NVU_FORCE_STREAM_UPGRADE_TIMEOUT=57 ✓
docker logs nv_40006_uni --tail 5
→ [NV-PROXY] Listening on 0.0.0.0:40006 (healthy) ✓
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
| **NVU_FORCE_STREAM_UPGRADE_TIMEOUT** | **57** | — | **R656→R659 (-4s)** |
| TIER_TIMEOUT_BUDGET_S | 80 | — | R653 90→85→80 |

## 下一轮计划
**FORCE_STREAM_UPGRADE_TIMEOUT 57→56 (-1s)** — 继续 -1s 保守增量，在 zero-error regime 持续前提下挤压 integrate 超时等待。需至少 6h 数据窗口验证 57 无回归后再推进。若 integrate 路径出现回归 (timeout/error 增加)，则暂停 trajectory 转向 TIER_TIMEOUT_BUDGET_S 80→75 或 NVU_EMPTY_200_FASTBREAK 调优。

## ⏳ 轮到HM1优化HM2
