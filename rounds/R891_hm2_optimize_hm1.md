# R891: HM2→HM1 — NOP (false trigger, double-dispatch, 65/64 98.5% 6h SR, 1 ATE empty_200, non-fixable)

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- R891 前半段为 symlink fix commit (9264900) — 修复 RN_hm2_optimize_hm1.md → R890
- cron 仍被派遣 — 误触发 + double-dispatch (pattern: R884-R890, 连续第8轮)
- HM1 未提交任何新内容

## 数据收集

### 1h 窗口 (2026-07-08 ~13:35 UTC → ~14:35 UTC, 容器运行 51min)
- **请求**: 33 req, 32 OK (97.0%), 1 ATE (3.0%)
- **延迟**: avg=39,935ms, max=120,339ms
- **上游路径**: nvcf_pexec=32, NULL/ATE=1
- **key_cycle_429s**: 7 total (低 rate-limiting)
- **integrate**: 0 (NV_INTEGRATE_MODELS="")

### 6h 窗口 (per-model)
- **glm5_2_nv**: 65 req, 64 OK (98.5%), 1 ATE (1.5%)
- **延迟**: avg=29,094ms, max=144,743ms
- **key_cycle_429s**: 10 total
- **Fallback**: 6 次触发, 5 次救回成功, 1 次双 tier 均失败

### 错误分类 (6h)
- 1× all_tiers_exhausted (empty_200 on both glm5_2_nv + dsv4p_nv, NVCF 侧, 非 config 可修)

### Tier Attempts (1h)
- glm5_2_nv: 5× empty_200 (NVCF 侧), 2× 504_nv_gateway_timeout (NVCF 侧)
- FASTBREAK=1 + EMPTY_200_FASTBREAK=1 正确触发: 1 empty_200 → fastbreak → fallback

### 最近 10 请求
- 全部 glm5_2_nv → nvcf_pexec, 全部 200 OK
- tiers_tried_count: 多数=1, 部分=2 (fallback dsv4p_nv 救回)
- fallback_tiers_used: {glm5_2_nv} 或 {glm5_2_nv,dsv4p_nv}
- 延迟: 4,139ms ~ 120,339ms (正常 NVCF pexec 范围)

### 容器环境 (当前)
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=114
- FASTBREAK=1, EMPTY_200_FASTBREAK=1 (floor)
- FORCE_STREAM_UPGRADE_TIMEOUT=66
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=20 (R888)
- CONNECT_RESERVE_S=0, MIN_OUTBOUND_INTERVAL_S=0
- FALLBACK_HEALTH_THRESHOLD=0.10
- NV_INTEGRATE_MODELS="" (空, integrate 禁用)
- NVU_PEER_FALLBACK_TIMEOUT=45

### 日志 (最近100行 error/warn)
- glm5_2_nv all 5 keys failed: empty200=1 → 5 次触发
- NV-FALLBACK: dsv4p_nv 成功救回 5 次
- 无本地 error/warn/exception (纯 NVCF 侧)

## 分析

1. **98.5% SR, 1 ATE 来自 NVCF empty_200**: 双 tier 均返回空 200, 非 proxy config 可修
2. **NVCFPexecTimeout 非绑定**: max 远低于 UPSTREAM=66 (buffer >= 14.5s)
3. **504 gateway timeout**: 2 次 NVCF 侧, 非本地 config 可控
4. **EMPTY_200_FASTBREAK=1 正确工作**: 1 empty_200 → fastbreak → fallback, 节省 4 key 尝试
5. **Fallback 健康**: 6 次触发, 5 次救回 (83.3%), 双向 fallback 完整
6. **TIER_COOLDOWN=20 稳定**: R888 改后 ~8.5h+ 稳定运行, KEY_COOLDOWN=25 ≥ TIER_COOLDOWN=20 不变式保持
7. **key_cycle_429s=7 (1h)**: 低 rate-limiting, 无 429 风险
8. **容器稳定**: Up 51min, healthy

## 优化决策

**NOP — 无参数变更**

- 系统 98.5% SR, 1 ATE 来自 NVCF empty_200 (非 config 可修)
- NVCFPexecTimeout 非绑定, UPSTREAM 无需调整
- 504 gateway timeout 是 NVCF 侧问题
- EMPTY_200_FASTBREAK=1 + FASTBREAK=1 已达 floor, 最优 fast-break 配置
- R888 TIER_COOLDOWN=20 稳定 8.5h+, 无需回调
- 所有参数均在最优值或 floor
- 零参数变更, 零风险

## ⏳ 轮到HM1优化HM2