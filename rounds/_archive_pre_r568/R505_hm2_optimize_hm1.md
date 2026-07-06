# R505: HM2→HM1 — ATE DB日志修复 + BUDGET/RESERVE收紧

## 数据采集 (6h baseline, 2026-07-01 12:00-18:00 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | ~2397 |
| 成功(SR) | dsv4p_nv=97.2%, kimi_nv=95.2%, glm5_1_nv=96.1% |
| ATE总数 | 306 (dsv4p=292, kimi=11, glm5_1=2) |
| ATE率 | ~12.8%/h |
| ATE Duration avg | 52-84s |
| dsv4p P50 TTFB | 7-8s (stream) / 9-10s (non-stream) |
| 5-key RR均衡 | ✓ (dsv4p各key 254-283次) |
| 429率 | 0 |
| empty_200率 | 0 |

### 关键发现

1. **DB日志缺陷**: ALL 306个ATE的`tier_model=NULL`, `nv_key_idx=NULL`, `error_subcategory=NULL`。
   - 原因: `handlers.py` ATE路径(L192-203)从未设置`metrics["tier_model"]`和`metrics["error_subcategory"]`
   - 影响: DB查询无法按model/错误类型分析ATE, 只能靠docker logs文本grep
   - 成功路径(L226)正确设置了`tier_model`, 说明只在ATE分支遗漏

2. **dsv4p ATE根因**: 312 `NVCFPexecTimeout` attempts, avg 32.5s
   - NVCF函数级排队超时(25s UPSTREAM_TIMEOUT ceiling), 每3连timeout → FASTBREAK=3 break
   - TIER_TIMEOUT_BUDGET=125s 对单tier持久化过度冗余:
     - 3×timeout(25s) + 3.8s throttle × 3 = 86.4s → 在80s内有机会完成
     - 125s允许5th key尝试但实际3连timeout后FASTBREAK已跳, 后续key浪费budget

3. **HM_CONNECT_RESERVE_S=10s 过度预留**:
   - connect实测0.6-2.1s(5样本), 10s=5-17x过度
   - 每attempt回收5s→effective read timeout=25-5=20s, 比原来25-10=15s多33%

4. **hm_tier_actions表**: 仅431行(kimi=44, dsv4p=312, glm5=5); dsv4p ATE未记录(tier_model=NULL导致FK关联断裂)

## 优化方案

### 变更1: ATE路径DB日志修复 (handlers.py)
```python
# 原代码(L196-198):
metrics["fallback_tiers_used"] = result.fallback_tiers_used
metrics["tier_summaries"] = result.tier_attempts

# 新代码: 插入tier_model和error_subcategory
metrics["fallback_tiers_used"] = result.fallback_tiers_used
metrics["tier_model"] = mapped_model                          # ← NEW
metrics["error_subcategory"] = "all_tiers_failed_in_mapped_tier"  # ← NEW
metrics["tier_summaries"] = result.tier_attempts
```
**预期效果**: ATE行在DB中将正确记录tier_model=dsv4p_nv/kimi_nv/glm5_1_nv + error_subcategory, 使DB分析可直接按model分组。

### 变更2: TIER_TIMEOUT_BUDGET_S 125→80 (-45s, -36%)
- 单tier持续化: 3model各对应1func, 不再需要125s跨tier冗余
- FASTBREAK=3在3×25s=75s+throttle内已break; 80s给3key完整尝试空间
- 80-125=45s浪费区间: 在这45s里FASTBREAK早已触发, budget耗尽前的remaining check也无key可试
- **预期**: ATE平均duration从52-84s降低到~60-75s, 更快502返回

### 变更3: HM_CONNECT_RESERVE_S 10→5 (-5s, -50%)
- connect 0.6-2.1s实测, 5s=2.4x安全边际仍充足
- 每attempt read timeout从15s提升到20s, +33%
- **预期**: 单key timeout从25s→25s(ceiling unchanged), 但effective read=20s, 减少budget_exhausted_after_connect误判

## 部署

| 步骤 | 命令 | 状态 |
|------|------|------|
| handlers.py备份 | `cp handlers.py handlers.py.bak.R505_ate_logging` | ✓ |
| handlers.py patch | sed插入tier_model+error_subcategory | ✓ |
| compose env BUDGET | 125→80 | ✓ |
| compose env RESERVE | 10→5 | ✓ |
| 容器重建 | `docker compose up -d hm40006` | ✓ |
| 健康检查 | `/health` → 200 OK, 3model+5key | ✓ |

## 铁律检查

- [x] 只改HM1配置/h代码, 未改HM2本地
- [x] 少改多轮: 3项小改(1 bugfix + 2 param), 无架构变动
- [x] compose env生效验证: TIER_TIMEOUT_BUDGET_S=80, HM_CONNECT_RESERVE_S=5

## ⏳ 轮到HM1优化HM2
