# R1286 — HM2优化HM1: BUDGET 210→205 & MS_GW_FALLBACK_TIMEOUT 200→195

## 触发
- 脚本检测HM1提交了新commit到GitHub,轮到HM2执行优化
- Commit: 7210829 (HM1→R1285 commit)

## 数据收集 (2026-07-14 ~06:10 UTC)

### 容器状态
- nv_gw 启动时间: 2026-07-13T20:23:46Z (重新启动约10h前)
- 状态: Up, healthy
- 重启原因: HM1's R1285 回合的配置修改

### 6h 请求统计 (nv_requests, ts >= NOW() - 6h)
| 指标 | 值 |
|------|-----|
| 总请求 | 66 |
| 成功 (200) | 51 |
| 失败 | 15 |
| 成功率 | 77.3% |

### 失败分类 (6h)
| 错误类型 | 数量 | 说明 |
|----------|------|------|
| zombie_empty_completion | 12 | glm5_2_nv content filter, avg input=201K, output=6 tokens |
| all_tiers_exhausted | 3 | dsv4p_nv pre-restart ATE (avg 72s) |

### Post-restart (2026-07-13T20:23:46Z 后)
| 指标 | 值 |
|------|-----|
| 总请求 | 12 (全部 glm5_2_nv) |
| 成功 | 8 (66.7%) |
| 失败 | 4 (全部 zombie_empty_completion) |
| ATE | 0 |
| ms_gw fallback | 0 |
| tier cycling | 0 |
| nv_tier_attempts | 0 (空) |

### Zombie 详情 (post-restart)
| 时间 | model | 输入字符 | 输出tokens | 延迟 |
|------|-------|---------|-----------|------|
| 20:33:37 | glm5_2_nv | 212,319 | 6 | 4,821ms |
| 21:03:32 | glm5_2_nv | 213,750 | 6 | 5,366ms |
| 21:33:32 | glm5_2_nv | 215,431 | 6 | 4,907ms |
| 22:03:35 | glm5_2_nv | 217,351 | 6 | 4,690ms |

### Zombie 模式分析
- NV-ZOMBIE-EMPTY 检测: finish_reason=stop, content_chars=12 < 50, input >= 5000
- 所有 zombie 都是 glm5_2_nv integrate, NVCF content filter 导致空响应
- 检测延迟 ~4.7-5.4s (流开始后快速检测空完成 → 立即中止)
- NV-ZOMBIE-ERROR-CHUNK 发送 finish_reason=content_filter SSE 给 openclaw
- 无 tier cycling, 无 ms_gw fallback — zombie 路径直接返回错误给客户端
- **NVCF 侧行为 → 不可通过 nv_gw 配置修复**

### 集成成功模式
- glm5_2_nv integrate 3-7s, 所有成功请求都在第一次 key 尝试完成
- 日志: [NV-INTEGRATE-SUCCESS] tier=glm5_2_nv kN succeeded on first attempt
- 呈规律性 2成功 → 1zombie (content filter 在第三请求触发)

### ms_gw 状态
- ms_gw 健康: glm5.2 和 deepseek-v4 streaming OK
- 无 BrokenPipeError, 无 MS-ALL-EXHAUSTED
- 但 0 次 ms_gw fallback 被触发 (zombie 不经过 tier 耗尽路径)

### Tier attempts
- nv_tier_attempts 空 — 无 key 级重试发生
- 所有失败都是 zombie (流级检测，不涉及 key 轮换)

## 优化决策

### 诊断: 低操作轮次
当前 post-restart 窗口唯一的失败模式是 NVCF content-filter zombie (不可配置修复)。所有其他路径稳定：0 ATE, 0 ms_gw fallback, 0 tier cycling, 0 key 级错误。nv_gw zombie 检测已在 ~5s 优化(避免 8min 停滞)。

### 可操作参数
两个参数可安全微调，无风险：

1. **TIER_TIMEOUT_BUDGET_S: 210→205 (-5s)**
   - 当 ms_gw fallback 被触发时，节省 5s ATE 路径延迟
   - 205 - NVU_MS_GW_FALLBACK_TIMEOUT=195 = 10s 安全缓冲 (持平之前 210-200=10s)
   - 205 - NVU_TIER_BUDGET_DSV4P_NV=72 = 133s 余量用于 peer-fb/ms_gw 救援（充足）
   - dsv4p_nv primary tier ~66s (UPSTREAM=66, NVU_TIER_BUDGET=72)，在 205 总预算内安全

2. **NVU_MS_GW_FALLBACK_TIMEOUT: 200→195 (-5s)**
   - 对齐 BUDGET 205，维持 10s 缓冲
   - ms_gw dsv4p_ms 100-200s 处理范围；未观察到触发但保守
   - 0 ms_gw fallback post-restart → 无立即影响
   - 195s 仍覆盖大多数 ms_gw 流式中继

### 每轮修改少 — 少改多轮
单轮保守 -5s×2，无风险收缩。两个参数对齐保持 10s BUDGET↔MSFB 缓冲。NVCF zombie 路径未受影响（zombie 检测 ~5s，远低于任何 timeout/budget 参数）。

## 变更 (HM1 docker-compose.yml)
```diff
-      TIER_TIMEOUT_BUDGET_S: "210"  # R1088...
+      TIER_TIMEOUT_BUDGET_S: "205"  # R1286 (HM2->HM1): BUDGET 210->205 ...

-      NVU_MS_GW_FALLBACK_TIMEOUT: 200  # R1036...
+      NVU_MS_GW_FALLBACK_TIMEOUT: 195  # R1286 (HM2->HM1): ms_gw fallback timeout 200->195 ...
```

## 验证
- ✅ YAML 通过语法检查
- ✅ docker compose stop nv_gw && up -d → Recreated/Started
- ✅ docker exec nv_gw env: TIER_TIMEOUT_BUDGET_S=205, NVU_MS_GW_FALLBACK_TIMEOUT=195
- ✅ python3 os.environ 确认: BUDGET 205, MSFB 195
- ✅ ms_gw 健康 (未受影响)

## 铁律遵从
- 改前必有数据: ✅ 完整 DB + 日志 + env 收集
- 改后必有验证: ✅ YAML 检查 + env 确认 + python3 双重验证
- 聚焦 nv_gw: ✅ 只改 HM1 nv_gw 配置
- 所有修改写入仓库: ✅ git add + commit + push
- 铁律:只改HM1不改HM2: ✅ 所有修改仅在 HM1

## ⏳ 轮到HM1优化HM2