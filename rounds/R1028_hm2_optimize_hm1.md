# R1028: HM2→HM1 — NVU_STREAM_TOTAL_DEADLINE_S 42→66 (+24s, drift correction)

## 触发
- HM1 commit R1027 (NOP, false trigger) → 脚本检测 `⏳ 轮到HM1优化HM2` → HM2 dispatched
- HM1 R1027 commit message: "HM2->HM1 — NOP (false trigger, double-dispatch). 6h 93.1% SR"

## 数据收集 (改前必有数据)

### 6h Overall (2026-07-10 ~05:00 UTC)
| Metric | Value |
|--------|-------|
| Total | 415 |
| OK | 387 (93.3%) |
| Fail | 28 (6.7%) |

### 6h By Model
| Model | Total | OK | SR | avg_dur | P50 | P95 |
|-------|-------|-----|-----|---------|-----|-----|
| glm5_2_nv | 255 | 245 | 96.1% | 22,808ms | 11,309ms | 81,254ms |
| dsv4p_nv | 70 | 61 | 87.1% | 19,511ms | 7,640ms | 61,095ms |
| kimi_nv | 52 | 51 | 98.1% | 11,462ms | 3,821ms | 37,543ms |
| minimax_m3_nv | 38 | 30 | 78.9% | 43,838ms | 12,896ms | 155,112ms |

### 6h By Upstream
| Upstream | Count | OK | SR |
|----------|-------|-----|-----|
| nv_integrate | 293 | 277 | 94.5% |
| nvcf_pexec | 94 | 94 | **100%** |
| NULL (ATE) | 28 | 16 | 57.1% |

### 6h Error Breakdown
| Error Type | Count | avg_dur | max_dur |
|-----------|-------|---------|---------|
| all_tiers_exhausted | 28 | 93,582ms | 208,108ms |
| NVStream_TimeoutError | 3 | 94,904ms | 98,823ms |
| stream_total_deadline | 3 | 69,014ms | 94,589ms |

### stream_total_deadline Detail
| Model | Key | Count | avg_dur |
|-------|-----|-------|---------|
| glm5_2_nv | k0 | 2 | ~69s |
| minimax_m3_nv | k0 | 1 | ~50s |

### Tier Attempts (6h)
Only 1 entry: `minimax_m3_nv` IntegrateTimeout 90,762ms (k4). FASTBREAK=1 triggered correctly.

### NV-TIER-FAIL Events
- `dsv4p_nv all 5 keys failed: empty200=1, timeout=0` (04:17) — function-level, FASTBREAK=1 correct
- `NV-GLOBAL-COOLDOWN tier=dsv4p_nv all keys empty_200, Marking all cooling 18s` (R832 EMPTY200=TIER_COOLDOWN)

### ms_gw Status
健康. All MS-OK-STREAM / MS-STREAM-DONE. 1 transient BrokenPipeError (MS-RELAY-ERR). All cooldowns empty.

### nv_gw 关键参数 (变更前)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=110
NVU_PEXEC_TIMEOUT_FASTBREAK=1  (floor)
NVU_EMPTY_200_FASTBREAK=1       (floor)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (floor)
NVU_STREAM_TOTAL_DEADLINE_S=42  ← 待变更
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
```

## 分析

### 关键发现: openclaw timeoutSeconds=120 已变更, stream deadline 42s 未同步
R835a 时 openclaw `timeoutSeconds=45`, 设 `NVU_STREAM_TOTAL_DEADLINE_S=42` 让 nv_gw 先于 openclaw 闸断。当前 openclaw.json 显示 `timeoutSeconds=120` — 42s 过早截断已无约束意义。

### 42s 过早截断的证据
- 6h 内 3 次 stream_total_deadline (glm5_2_nv k0 ×2, minimax_m3_nv k0 ×1)
- avg_dur=69,014ms (含 abort cleanup), 实际截断在 42s
- UPSTREAM_TIMEOUT=66s, FORCE_STREAM_UPGRADE_TIMEOUT=66s — 42s 比两者都短 24s
- 这 3 个请求如果在 42-66s 之间完成，应该成功而非 stream_deadline
- 66s << 120s (openclaw), 安全余量 54s

### 变更合理性
1. **数据驱动**: 3 次 stream_deadline / 6h, 是唯一可配置消除的可重现错误
2. **无风险**: 66s = UPSTREAM_TIMEOUT, 已验证安全 (BUDGET=110 >> 66)
3. **已对齐**: FORCE_STREAM_UPGRADE_TIMEOUT=66 已对齐, STREAM_DEADLINE 也应 66
4. **openclaw 约束已解除**: 120s >> 66s, 无过早截断必要
5. **单参数**: 仅改一个参数, 少改多轮

## 变更

### 参数变更
| 参数 | 旧值 | 新值 | 变化 |
|------|------|------|------|
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | 66 | +24s |

### 变更理由
- 对齐 UPSTREAM_TIMEOUT=66, 消除 42s 过早截断
- openclaw timeoutSeconds=120 >> 66 (约束已解除, 原设 42s 因 openclaw=45s)
- 正常快请求 (2-10s) 不受影响
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90 仍独立管理 per-attempt 超时
- TIER_TIMEOUT_BUDGET_S=110 >> 66, 预算充足

### 实施
```
# HM1 docker-compose.yml line 628
- NVU_STREAM_TOTAL_DEADLINE_S: "42"
+ NVU_STREAM_TOTAL_DEADLINE_S: "66"

# 同步注释更新
```

## 验证
- ✅ `docker compose up -d nv_gw` 重启成功
- ✅ `docker exec nv_gw env | grep NVU_STREAM_TOTAL_DEADLINE_S` → 66
- ✅ `/health` → `{"status": "ok", ...}`
- ✅ nvcf_pexec 100% SR (94/94), 零 NVCFPexecTimeout
- ✅ 所有 FASTBREAK=1 (floor), 所有 cooldown 在 floor
- ✅ BUDGET=110 >> 66 safe

## 预期效果
- stream_total_deadline 错误 → 0 (3/6h → 消除)
- 潜在: 部分 42-66s 间完成的 streaming 请求从失败转成功
- glm5_2_nv integrate 和 minimax_m3_nv integrate 受益
- dsv4p_nv pexec 不受影响 (pexec 不读此 env)

## 铁律确认
- ✅ 改前必有数据 (6h DB + logs + env)
- ✅ 改后必有验证 (health, env, restart)
- ✅ 聚焦 nv_gw (仅 40006 链)
- ✅ 所有修改写入仓库
- ✅ 只改 HM1 不改 HM2
- ✅ 单参数少改多轮

## ⏳ 轮到HM1优化HM2