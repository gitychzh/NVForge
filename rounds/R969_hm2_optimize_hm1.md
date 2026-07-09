# R969: HM2→HM1 — UPSTREAM_TIMEOUT 60→62 (+2s)

## 数据收集 (2026-07-09 14:00-14:10 UTC, 6h窗口)

### 总体统计
| 指标 | 值 |
|------|-----|
| 6h 总请求 | 31 |
| 成功 (200) | 31 (100% SR) |
| 失败 (ATE) | 0 |
| 平均 TTFB | 57,290ms |
| 平均 Duration | 57,293ms |
| 最大 Duration | 173,278ms |
| Fallback 触发 | 10/31 (32.3%) |
| Fallback 平均 Duration | 120,102ms |
| 非 Fallback 平均 Duration | 27,383ms |

### 上游路径
| 路径 | 请求数 | 成功率 |
|------|--------|--------|
| nvcf_pexec | 31 | 100% |

### 错误分类
| 错误类型 | 数量 |
|----------|------|
| (无) | 0 |

### Tier Attempts (6h)
| Tier | 错误类型 | 次数 | 平均耗时 | 最大耗时 |
|------|---------|------|---------|---------|
| glm5_2_nv | NVCFPexecTimeout | 9 | 54,668ms | **60,373ms** |
| glm5_2_nv | 504_nv_gateway_timeout | 5 | - | - |
| glm5_2_nv | empty_200 | 3 | - | - |
| glm5_2_nv | budget_exhausted_after_connect | 1 | 51,838ms | 51,838ms |

### NVCFPexecTimeout 按 Key 分布
| Key | 次数 | 平均耗时 | 最大耗时 |
|-----|------|---------|---------|
| K0 | 2 | 52,635ms | 53,473ms |
| K1 | 2 | 55,924ms | 60,350ms |
| K2 | 2 | 55,832ms | 60,352ms |
| K3 | 1 | 60,373ms | 60,373ms |
| K4 | 2 | 51,428ms | 51,543ms |

### 24h 错误全景
| 错误类型 | 数量 |
|----------|------|
| all_tiers_exhausted | 1 |

### Docker Logs (最近关键)
```
[14:04:21.6] [NV-TIMEOUT] tier=glm5_2_nv k2 NVCF pexec timeout: attempt=60350ms total=60355ms
[14:04:21.6] [NV-PEXEC-FASTBREAK] tier=glm5_2_nv 1 consecutive NVCFPexecTimeout -> fast-break
[14:04:21.6] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=0
[14:04:21.6] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[14:04:43.2] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv
[14:05:44.7] [NV-TIMEOUT] tier=glm5_2_nv k3 NVCF pexec timeout: attempt=60352ms total=60355ms
[14:05:44.7] [NV-PEXEC-FASTBREAK] tier=glm5_2_nv 1 consecutive NVCFPexecTimeout -> fast-break
[14:05:44.7] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed
[14:05:44.7] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[14:06:14.4] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv
```

## 诊断

**核心发现**: glm5_2_nv NVCFPexecTimeout max=60,373ms @ UPSTREAM=60,000ms — **binding edge violated** (buffer = -373ms)。R968 commit message 报告 max=53,473ms (6.5s buffer)，但数据已漂移。

**R751 ≥3s buffer rule**:
- R751 要求: 当减少 UPSTREAM 时，减少后与 NVCFPexecTimeout max 的 buffer ≥3s
- 当前: UPSTREAM=60,  NVCFPexecTimeout max=60,373ms → buffer = -373ms ❌
- 目标: UPSTREAM=62 → buffer = 62,000 - 60,373 = 1,627ms
- 注: buffer < 3s 但本回合是 **增加** 而非减少，R751 规则仅适用于减少场景。+2s 是保守恢复。

**Failure Pattern**:
- glm5_2_nv 请求第一次尝试 → NVCFPexecTimeout @ ~60s → FASTBREAK=1 触发 → 立即 fallback 到 dsv4p_nv
- dsv4p_nv fallback 100% SR (所有 10 次 fallback 均成功)
- 非 fallback 请求 avg 27,383ms — dsv4p_nv 直连健康

**Optimization Rationale**:
- BUFFER math: 62,000 - 60,373 = 1,627ms — 紧但有效 (增加不含 R751 减少约束)
- BUDGET=114 >> 62 per tier → 安全
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64 ≥ 62 → 安全
- FASTBREAK=1 — 不变 (NVCFPexecTimeout 均匀分布五键，函数级别瓶颈)
- Single param per round; iron rule: only change HM1 never HM2

## 执行

```bash
# UPSTREAM_TIMEOUT: "60" → "62" in docker-compose.yml line 483
# Python stdin pipe edit (Workaround H), stripped accumulated history
# docker compose stop nv_gw && docker compose up -d nv_gw
# Verified: docker exec nv_gw env | grep UPSTREAM_TIMEOUT → 62
# Health check: {"status": "ok"}
```

## 验证结果

- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → `UPSTREAM_TIMEOUT=62` ✅
- `curl http://localhost:40006/health` → `{"status": "ok"}` ✅
- Container recreated successfully ✅

## ⏳ 轮到HM1优化HM2