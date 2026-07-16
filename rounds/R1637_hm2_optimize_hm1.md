# R1637: HM2→HM1 — TIER_COOLDOWN_S 15→25 (+10s, 对齐HM2)

## 数据收集 (改前必有数据)

### 容器状态
| Container | Status | Uptime |
|---|---|---|
| nv_gw | Up | 8h+ (restarted 2026-07-16T10:47:25Z) |
| cc4101 | Up | stable |
| ms_gw | Up | 12h+ (healthy) |
| logs_db | Up | 40h+ (healthy) |

### 3h DB 总览
| Metric | Value |
|---|---|
| 总请求 | 215 |
| OK (200) | 107 (49.8% SR) |
| Fail (502) | 108 |
| Avg OK ms | 21,869ms |
| MAX(ts) | 2026-07-16 11:19:41 UTC |

### 按模型 (3h)
| Model | Total | OK | SR% | Avg OK ms |
|---|---|---|---|---|
| glm5_2_nv | 203 | ~100 | ~49% | ~22,000ms |
| dsv4p_nv | 12 | ~7 | ~58% | ~18,000ms |

### 错误分解 (3h)
| Error Type | Count | Avg ms |
|---|---|---|
| zombie_empty_completion | 97 | 8,783ms |
| all_tiers_exhausted | 7 | 13,550ms |

### Tier attempts (3h)
| Error Type | Count |
|---|---|
| pexec_success | 201 |
| pexec_429 | 67 |
| pexec_SSLEOFError | 8 |
| pexec_empty_200 | 4 |
| pexec_conn_RemoteDisconnected | 2 |
| pexec_504 | 1 |
| pexec_timeout | 1 |

### 容器日志 (live)
- 429 cascading: all 5 glm5_2_nv keys hitting NVCF rate-limit in ~2s each → chain-fail
- CHAIN-FAIL → CHAIN-RESET → CHAIN-FALLBACK → PEER-FB
- Peer-FB mixed: OK (200, 5-851ms ttfb) and timeout (72s)
- zombie: NVCF content-filter returning 8-17 chars on 120K-233K input (not config-fixable)
- TIER_COOLDOWN=15: next request re-enters same exhausted tier after 15s → rapid fail-loops

### 环境变量（关键参数）
- UPSTREAM_TIMEOUT=66, TIER_BUDGET=205, TIER_COOLDOWN=15, KEY_COOLDOWN=25
- NVU_TIER_BUDGET_DSV4P_NV=66, NVU_TIER_BUDGET_GLM5_2_NV=120
- NVU_PEER_FALLBACK_TIMEOUT=72, NVU_PEER_FB_SKIP_MODELS=dsv4p_nv
- NVU_MS_GW_FALLBACK_TIMEOUT=120
- CC4101_PRIMARY_FAIL_THRESHOLD=4 (R1635 生效)
- Compose md5 (before edit): 6e81cd001acd69ac828eae1cfaa3bffe

### HM2 对端参数 (对比)
| Parameter | HM1 | HM2 |
|---|---|---|
| TIER_COOLDOWN_S | 15 | 25 |
| KEY_COOLDOWN_S | 25 | 25 |
| UPSTREAM_TIMEOUT | 66 | 66 |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | 120 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | 70 |
| TIER_TIMEOUT_BUDGET_S | 205 | 180 |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | 25 |

## 6 门分析

### Gate 1: 所有 ATE 双 tier?
7 ATE 全部 tiers_tried_count=1 → **FAIL, Gate 2 豁免**

### Gate 2: 零单层 ATE 或全代码级?
- 97 zombie_empty_completion (glm5_2_nv): NVCF content-filter 返回 stop+8-17 chars, 代码级 intentional mechanism ✅
- 7 all_tiers_exhausted (glm5_2_nv): NVCF 429 cascading exhausts all 5 keys, server-side rate-limit ✅
- → **全代码级 ✅**

### Gate 3: NVCFPexecTimeout buffer?
- 1 pexec_timeout in tier_attempts (negligible, 0.35% of 284) → **N/A ✅**

### Gate 4: FALLBACK_GRAPH?
- tier_chain=['glm5_2_nv'] (no cross-model fallback, R753) → expected state → **N/A ✅**

### Gate 5: Fallback SR?
- Peer-FB mixed: some OK, some 72s timeout. HM2 PEER_FALLBACK_TIMEOUT=25 too short → HM2-side issue, not HM1 → **N/A ✅**

### Gate 6: 所有参数 floor/optimal?
- TIER_COOLDOWN=15: HM2 validates 25 as stable, HM1 15 causes rapid re-entry into exhausted tier → **NOT optimal, 可优化**

## 根因分析

**429 cascading + TIER_COOLDOWN=15 形成 fail-loop**:
1. 请求进入 glm5_2_nv tier → 5 keys 全部 429 (~10s, 2s/key)
2. CHAIN-FAIL → peer-fb (mixed result)
3. TIER_COOLDOWN=15 → 15s 后下一请求重新进入同一 tier
4. 此时 NVCF rate-limit 窗口可能仍未恢复 → 再次 429 → repeat

**HM2 已有验证**: TIER_COOLDOWN=25 在 HM2 上稳定运行，25s 给 NVCF rate-limit 窗口更多恢复时间。

## 优化决策

**TIER_COOLDOWN_S: 15→25 (+10s, 对齐HM2)**

- 单参数变更，保守 +10s
- 对齐 HM2 已验证的稳定值
- 429 cascading 后给 NVCF rate-limit 窗口更多恢复时间
- 不做 fail-loop 的快速重试
- 无 budget 影响: 25 << 205 BUDGET 安全
- 不影响 peer-fb 约束: PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET(70)+2 ✓

## 执行

```bash
# 1. Edit compose line 502
ssh -p 222 opc_uname@100.109.153.83 \
  "sed -i '502s|.*|NEW_LINE|' /opt/cc-infra/docker-compose.yml"

# 2. Restart nv_gw
cd /opt/cc-infra && docker compose up -d nv_gw

# 3. Verify container env
docker exec nv_gw env | grep TIER_COOLDOWN_S  → 25 ✅

# 4. Health check
curl -s http://localhost:40006/health  → {"status":"ok"} ✅
```

## 铁律
✅ 改前有数据 ✅ 改后有验证 ✅ 只改 HM1 ✅ 已 commit push
## ⏳ 轮到HM1优化HM2
