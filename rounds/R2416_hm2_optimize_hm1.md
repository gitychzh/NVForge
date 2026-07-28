# R2416: HM2→HM1 NOP — R2415验证轮

**Author:** opc2_uname (HM2)  
**Date:** 2026-07-28 10:10 CST  
**Type:** NOP (no parameter change)  
**Iron Law:** 只改HM1，不改HM2本地

---

## 1. 数据收集 (改前必有数据)

### 1.1 链路全景

| 模型 | 请求数 | 200 OK | 502 Err | SR% |
|------|--------|--------|---------|-----|
| kimi_nv | 10 | 5 | 5 | 50.0% |
| glm5_2_nv | 10 | 8 | 2 | 80.0% |
| **总计** | **20** | **13** | **7** | **65.0%** |

### 1.2 错误分类

| 模型 | 错误类型 | 数量 |
|------|----------|------|
| kimi_nv | all_tiers_exhausted | 5 |
| glm5_2_nv | zombie_empty_completion | 2 |

### 1.3 kimi_nv ATE详细分析

所有5个kimi_nv ATE均发生在前R2415时代（KEY_COOLDOWN_S=25）：
- `tiers_tried_count=1` — 只尝试了1个tier（即同tier内5个key）
- `nv_key_idx=NULL` — 没有任何key被实际尝试
- `input_tokens=0, output_tokens=0` — 请求完全未到达NVCF
- 根因: KEY_COOLDOWN_S=25 → 所有key被cooldown锁定 → tier被预判为不可用

### 1.4 glm5_2_nv zombie_empty_completion

2个glm5_2_nv zombie_empty_completion:
- 4272004b: 5.4s, 291k input, k3 (mihomo-7896)
- 38060e12: 5.0s, 293k input, k2 (mihomo-7895)
- 低延迟(zombie) → NVCF返回空completion → 可能是NVCF侧瞬时故障

### 1.5 后R2415数据 (10:00重启后)

nv_gw在10:00 CST重启加载R2415配置后：
- 4个请求全部成功（4/4 = 100% SR）
- 其中2个kimi_nv, 2个glm5_2_nv（推测，基于nv_gw日志中的NV-REQ计数）
- 无ERROR日志
- 无error_detail.jsonl新条目

### 1.6 nv_gw当前配置

```
KEY_COOLDOWN_S=10          # R2415: 25→10
NVU_EMPTY_200_FASTBREAK=2  # R2414: 1→2
NVU_TIER_BUDGET_KIMI_NV=370 # R2413: 330→370
NVU_PEXEC_TIMEOUT_FASTBREAK=3 # R2409: 4→3
NVU_SSLEOF_RETRY_DELAY_S=2.0 # R2397
NVU_STREAM_FIRST_BYTE_DEADLINE_S=16 # R2394
UPSTREAM_TIMEOUT=32
TIER_TIMEOUT_BUDGET_S=475
MIN_OUTBOUND_INTERVAL_S=0
TIER_COOLDOWN_S=0
```

## 2. 分析

### 2.1 R2415效果评估

R2415（KEY_COOLDOWN_S 25→10）应用仅22分钟。后R2415数据虽样本极小（4个请求），但：
- 100% SR — 无ATE
- 前R2415的5个kimi_nv ATE全部是KEY_COOLDOWN_S=25的starvation pattern
- 10s cooldown使key_cycle周期从25s→10s，每个key每50s可被重试一次（vs 125s）

### 2.2 NOP决策理由

1. **样本不足**: 4个post-change请求，无法判断R2415是否完全解决kimi_nv ATE
2. **无新故障模式**: 无SSLEOFError、无empty_200冲击、无429 cascade
3. **过度优化风险**: 在R2415验证前再改参数可能导致参数振荡
4. **等待策略**: 让R2415运行至少1小时积累数据，下一轮HM2可以根据更多数据精准调整

### 2.3 下一轮建议方向

如果下轮kimi_nv ATE仍有残留：
- 考虑将KEY_COOLDOWN_S从10→5（更激进，但可能触发429 cascade）
- 如果empty_200开始出现 → 维持FASTBREAK=2或考虑调整到3
- 如果SSLEOFError再现 → 验证SSLEOF_RETRY_DELAY_S=2.0是否生效

## 3. 变更

**无变更 (NOP)** — R2415需要更多运行时间验证。

## 4. 验证

nv_gw容器在10:00重启后稳定运行，4/4请求成功，无error日志。

---

## ⏳ 轮到HM1优化HM2