# HM2 Optimize HM1 — Round R1609

## 1. 触发分析
- HM1 commit 8d06406 (R1608 NOP) 由 opc_uname 提交 → 脚本判定轮到HM2优化
- 正常轮次，非 double-dispatch

## 2. 数据收集 (6h 窗口, 2026-07-16 ~04:40-10:40 UTC)

### 2.1 容器状态
- nv_gw: Up 2 hours (healthy, restart 2026-07-16 00:36 UTC)
- logs_db: Up 27 hours (healthy)
- Compose md5: 64e8fc1a (stable, unchanged)

### 2.2 nv_requests 6h 聚合
| 指标 | 值 |
|------|-----|
| Total | 66 |
| OK | 46 (69.7% SR) |
| Fail | 20 |
| Avg latency (OK) | 13,634 ms |

### 2.3 按模型
| Model | Total | OK | Fail | SR% | Avg Lat(OK) | Max Succ |
|-------|-------|----|------|-----|------------|----------|
| glm5_2_nv | 36 | 26 | 10 | 72.2% | 13,477 ms | 98,646 ms |
| dsv4p_nv | 30 | 20 | 10 | 66.7% | 13,822 ms | 63,895 ms |

### 2.4 失败分布
| Error Type | Model | Count | Avg Duration | Notes |
|-----------|-------|-------|-------------|-------|
| zombie_empty_completion | glm5_2_nv | 9 | 5,631 ms | NVCF content-filter, input ~224K, output 6-16 chars |
| zombie_empty_completion | dsv4p_nv | 7 | 9,525 ms | NVCF content-filter, input ~224K, output 24-48 chars |
| all_tiers_exhausted | dsv4p_nv | 3 | 44,565 ms | 504 → ms_gw TimeoutError (relay_started=True) |
| all_tiers_exhausted | glm5_2_nv | 1 | 8,411 ms | Quick ATE, transient |

### 2.5 upstream 路径分布
| upstream_type | Total | OK | Fail |
|--------------|-------|----|------|
| nvcf_pexec | 47 | 36 | 11 |
| nv_integrate | 14 | 9 | 5 |
| NULL | 5 | 1 | 4 |

### 2.6 nv_tier_attempts
- Total: 23 (all glm5_2_nv)
- pexec_success: 21 (avg 14,488ms, max 51,657ms)
- pexec_NameError: 1 (3,310ms)
- pexec_empty_200: 1 (NULL elapsed)

### 2.7 ms_gw
- 14 total, 14 ok (100% SR)
- All MS-STREAM-DONE within 4-5s, healthy

### 2.8 日志关键发现
- **dsv4p_nv 504 → ms_gw TimeoutError** (confirmed):
  - k1 → 504_nv_gateway_timeout at ~63s
  - NV-TIER-BUDGET: budget 66.0s remaining 2.1s < 5s → breaks after 1 key
  - NV-TIER-FAIL: all 5 keys failed, elapsed ~63s (only 1 key attempted)
  - NV-MS-FB: ms_gw relay failed after 124-132s TimeoutError (relay_started=True)
  - ms_gw log: MS-OK-STREAM + MS-STREAM-DONE in 4-5s → nv_gw never sees [DONE]
  - **Root cause: streaming sync defect (code-level) — ms_gw completes but relay fails**

- **dsv4p_nv ms_gw relay: 100% failure rate (2/2 in window)**
  - All ms_gw relay attempts for dsv4p_nv → TimeoutError (relay_started=True)
  - ms_gw log shows MS-STREAM-DONE 23-55KB → relay completes but nv_gw doesn't see it
  - R1474/R1488 pattern: ms_gw SR ≠ relay health. Only NV-MS-FB OK is proof.

- **No peer-fallback activity**: zero NV-PEER-FB logs in window
  - R1474 pitfall: `elif` blocks peer-fb for any model in MODELMAP
  - dsv4p_nv is in MODELMAP → ms_gw fires first and fails → peer-fb NEVER reached

- **glm5_2_nv zombie pattern** (continued):
  - NV-ZOMBIE-EMPTY: finish_reason=stop, content_chars=12-16 < 50, input_chars=223-224K
  - Code-level zombie detection, not config-fixable

### 2.9 容器 env (关键参数)
| Param | Value | Status |
|-------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | Floor |
| TIER_TIMEOUT_BUDGET_S | 205 | Generous |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | BUDGET Floor Pattern |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | Generous |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | Function-level correct |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | ← TARGET |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | Adequate |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | Adequate |
| NVU_PEER_FB_SKIP_MODELS | "" | All models eligible |
| MIN_OUTBOUND_INTERVAL_S | 0 | Floor |
| TIER_COOLDOWN_S | 15 | Stable |

## 3. 决策: 移除 dsv4p_nv 从 MODELMAP

### 3.1 根因
- dsv4p_nv ms_gw relay 100% 失败 (2/2 TimeoutError relay_started=True)
- ms_gw container 正常完成请求 (MS-STREAM-DONE 4-5s)，但 nv_gw streaming relay 无法接收 [DONE] 信号
- 这是 code-level streaming sync defect (R1488 pattern)，不可配置修复
- R1474 pitfall: dsv4p_nv 在 MODELMAP 中 → `elif` 阻塞 peer-fb → peer-fb 从未触发
- 每个 dsv4p_nv ATE: 66s tier → 124-132s ms_gw (guaranteed failure) → 502 = ~190s

### 3.2 修复
- 从 `NVU_MS_GW_FALLBACK_MODELMAP` 移除 `dsv4p_nv:dsv4p_ms`
- 新值: `glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms`
- dsv4p_nv ATEs 跳过 ms_gw → peer-fb (HM2 独立 key pool)
- Budget: 66s tier + 66s peer-fb = 132s << 205s BUDGET
- HM2 nv_gw healthy (health check OK, 5 keys active)

### 3.3 预期效果
- 每个 dsv4p_nv ATE 节省 ~120s (跳过 guaranteed-failure ms_gw)
- Peer-fb 使用 HM2 独立 key pool → 可能 rescue 504 ATEs
- glm5_2_nv 和 kimi_nv 仍保留 ms_gw fallback (ms_gw relay 对这些模型正常)

### 3.4 验证
- YAML OK
- Compose line 684 已更新
- Container env: `NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms`
- Container health: OK
- HM2 peer-fb URL: healthy ({"status":"ok"})

## 4. 不可修复项
- **zombie_empty_completion (16/20 = 80%)**: code-level，不可配置修复
- **ms_gw streaming sync defect**: code-level，不可配置修复
- 所有其他参数已在 floor/optimal

## ⏳ 轮到HM1优化HM2
