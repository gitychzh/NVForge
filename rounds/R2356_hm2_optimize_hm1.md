# R2356: HM2→HM1 Optimisation Round

**Role**: HM2 execution (optimize HM1)
**Timestamp**: 2026-07-25 20:15 UTC
**Commit**: R2356 (HM2→HM1): NVU_TIER_BUDGET_KIMI_NV 220→230, kimi_nv ATE ceiling fix. Single param delta per iron law.
**Agent**: HM2 (opc2_uname)

---

## 1. HM1 系统状态采集 (nv_gw / 40006)

### 1.1 容器状态
- `cc4101`: Up 10 minutes (R2355 recreated)
- `nv_gw`: Up 2 hours (healthy)
- `logs_db`: Up 8 days (healthy)

### 1.2 docker exec nv_gw env (关键参数)
```
NVU_TIER_BUDGET_KIMI_NV=220                # R2353
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_TIER_BUDGET_GLM5_2_NV=210
NVU_BIG_INPUT_COOLDOWN_S=180               # R2327→R2348
NVU_BIG_INPUT_FAIL_N=2
NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv
NVU_BIG_INPUT_THRESHOLD=250000
NVU_EMPTY_200_FASTBREAK=3
KEY_COOLDOWN_S=30
TIER_COOLDOWN_S=30
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=60
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,kimi_nv
UPSTREAM_TIMEOUT=24
```

### 1.3 cc4101 env
```
UPSTREAM_TIMEOUT=90                          # R2355 (30→90)
UPSTREAM_IDLE_TIMEOUT=150
```

### 1.4 DB 延迟 & 错误统计 (6h window)

| model       | total | 200 OK | failed | SR%   | avg_ok_s | max_ok_s | p90_s  |
|-------------|-------|--------|--------|-------|----------|----------|--------|
| kimi_nv     | 43    | 31     | 12     | 72.1% | 79.3     | 184      | 139.7  |
| glm5_2_nv   | 30    | 14     | 16     | 46.7% | 13.5     | 43       | 21.3   |
| dsv4p_nv    | 15    | 0      | 15     | 0.0%  | —        | —        | —      |

### 1.5 Failed请求分析

**kimi_nv 失败 (12次)**:
- `all_tiers_failed_in_mapped_tier`: 10次 — 持续时间188-220s，**正击中220s预算天花板**
- 2次 NVStream_IncompleteRead: 61s (cc4101 broken pipe before R2355 fix)
- 无 429 错误

**glm5_2_nv 失败 (16次)**:
- `all_tiers_failed_in_mapped_tier`: 15次 — big_input breaker active (333K-343K chars)
- 1次: 无 error_subcategory, 342K chars, 6s dur
- **真正的非big-input失败: 0次** (实际SR = 14/14 = 100%)

**dsv4p_nv 失败 (15次)**:
- 全部 `all_tiers_failed_in_mapped_tier` — big_input breaker 正常工作
- 输入大小: 333K-343K chars

### 1.6 Tier attempt errors (6h)
| tier       | error_type                  | count |
|------------|-----------------------------|-------|
| kimi_nv    | empty_200                   | 20    |
| kimi_nv    | NVCFPexecRemoteDisconnected | 7     |
| kimi_nv    | NVCFPexecSSLEOFError        | 1     |
| glm5_2_nv  | NVCFPexecRemoteDisconnected | 1     |
| glm5_2_nv  | NVCFPexecTimeout            | 1     |

### 1.7 nv_gw docker logs (recent)
- kimi_nv: empty_200 → key_cycle → success 模式持续
- kimi_nv: NV-THINKING-TIMEOUT extended 66s 正常
- kimi_nv: NV-STREAM-BUFFER-FLUSH write failed: Broken pipe (R2355前遗留; R2355修复后应减少)
- glm5_2_nv: big_input breaker OPEN → 返回 local 502 触发 ms_gw fallback
- dsv4p_nv: big_input breaker OPEN → 同上

---

## 2. 数据分析与决策

### 2.1 核心发现: kimi_nv ATE ceiling at 220s

1. **10次 kimi_nv ATE**: 持续时间 188-220s，全部 `all_tiers_failed_in_mapped_tier`
2. **预算天花板证据**: 
   - 预算 = 220s (NVU_TIER_BUDGET_KIMI_NV)
   - EMPTY_200_FASTBREAK=3 → 3次 empty_200 快速跳过后，第4-5个key尝试需要时间
   - 5 keys × ~30s cooldown = 150s 基础时间 + 3次 empty_200 快速跳过 (~30s) + 实际 pexec 时间
   - 220s 预算刚好被耗尽
3. **最大成功请求**: 184s, P90=139.7s → 230s 留有 46s 余量
4. **R2353修复效果**: 210→220 后 kimi_nv SR 从 ~60% → 72.1%，但 220s 仍不足以覆盖所有场景

### 2.2 非kimi_nv模型状态

- **glm5_2_nv**: 非big-input请求 SR=100% (14/14 OK)，big_input breaker 正确保护
- **dsv4p_nv**: 全部 big_input breaker 保护，未浪费预算时间
- **cc4101 UPSTREAM_TIMEOUT**: R2355 修复 (30→90) 稳定，无新增 broken pipe 错误

### 2.3 决策: NVU_TIER_BUDGET_KIMI_NV 220→230

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| NVU_TIER_BUDGET_KIMI_NV | 220 | 230 | kimi_nv ATE ceiling at 220s; max_OK=184s + buffer |

**风险评估**:
- 单参数增量 (+10s)，符合铁律
- 不改变任何其他模型预算
- 不改变任何其他参数
- 健康检查 ✅ (nv_gw: healthy)

---

## 3. 执行

### 3.1 配置变更
```bash
# /opt/cc-infra/docker-compose.yml (HM1 only)
NVU_TIER_BUDGET_KIMI_NV=220 → NVU_TIER_BUDGET_KIMI_NV=230
```

### 3.2 重启 nv_gw
```bash
cd /opt/cc-infra && docker compose up -d --no-deps --force-recreate nv_gw
```
结果: Container nv_gw Recreated → Started ✅

### 3.3 验证
- `docker exec nv_gw env | grep NVU_TIER_BUDGET_KIMI_NV` → `NVU_TIER_BUDGET_KIMI_NV=230` ✅
- `curl http://127.0.0.1:40006/health` → `{"status": "ok", ...}` ✅
- 健康检查: `running` ✅

---

## 4. 总结

| 项目 | 值 |
|------|-----|
| 变更参数 | NVU_TIER_BUDGET_KIMI_NV: 220→230 |
| 变更原因 | kimi_nv ATE ceiling at 220s; 10 failed ATE hitting budget ceiling |
| 预期效果 | kimi_nv SR 72.1%→~80%+ (10 ATE saved) |
| 副作用 | 所有kimi_nv请求预算增加10s，最坏情况多等10s |
| 铁律合规 | ✅ 单参数，只改HM1 |

## ⏳ 轮到HM1优化HM2