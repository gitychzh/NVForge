# R890: HM2→HM1 — NOP (false trigger, 65/64 98.5% 6h SR, 1 ATE empty_200, non-fixable)

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (pattern: R884-R889)
- HM1 未提交任何新内容

## 数据收集

### 6h 窗口 (2026-07-08 15:31 UTC → 21:31 UTC)
- **请求**: 65 req, 64 OK (98.5%), 1 ATE (1.5%)
- **延迟**: avg_ttfb=29,085ms, avg_dur=30,509ms, max_dur=144,743ms
- **上游路径**: nvcf_pexec (64), NULL/ATE (1)
- **Fallback**: 6 次触发 (9.2%), 5 次救回成功, 1 次双 tier 均失败

### 错误分类 (6h)
- 1× all_tiers_exhausted (双 tier empty_200, NVCF 侧, 非 config 可修)

### Tier Attempts (6h)
- glm5_2_nv: 5× empty_200 (NVCF 侧), 4× 504_nv_gateway_timeout (NVCF 侧), 1× NVCFPexecTimeout (max=51,475ms, k3)

### 最近请求 (2h)
- 全部 glm5_2_nv → nvcf_pexec, 全部 200 OK
- key_cycle_429s: 0-1 (极低 rate-limiting)
- 多请求延迟 50-120s (NVCF 正常 pexec 延迟)

### 容器环境 (当前)
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=114
- FASTBREAK=1, EMPTY_200_FASTBREAK=1
- FORCE_STREAM_UPGRADE_TIMEOUT=66
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=20 (R888 改)
- CONNECT_RESERVE_S=0, MIN_OUTBOUND_INTERVAL_S=0
- FALLBACK_HEALTH_THRESHOLD=0.10

### 日志 (最近100行 error/warn)
- 504_nv_gateway_timeout: NVCF 侧 gateway 超时, 非本地 config 可控
- EMPTY_FASTBREAK: 正确触发, 1 个 empty_200 即 fast-break, 节省剩余 key 尝试
- NV-FALLBACK-SUCCESS: dsv4p_nv fallback 成功救回 5 次
- 1× ATE: 双 tier empty_200 → ABORT-NO-FALLBACK (NVCF 侧)

## 分析

1. **98.5% SR, 1 ATE 来自 NVCF empty_200**: 双 tier 均返回空 200, 非 proxy config 可修
2. **NVCFPexecTimeout 非绑定**: max=51,475ms << UPSTREAM=66 (buffer=14.5s >> 3s minimum)
3. **504 gateway timeout**: 4 次 NVCF 侧, 非本地 config 可控
4. **key_cycle_429s=0-1**: 极低 rate-limiting, 无 429 风险
5. **EMPTY_200_FASTBREAK 正确工作**: 1 个 empty_200 即 fast-break, 跳过剩余 key 尝试
6. **Fallback 健康**: 6 次触发, 5 次救回 (83.3%), 双向 fallback 完整
7. **容器稳定**: 自 R888 重启后运行 ~8.5h, 无异常

## 优化决策

**NOP — 无参数变更**

- 系统 98.5% SR, 1 ATE 来自 NVCF empty_200 (非 config 可修)
- NVCFPexecTimeout 非绑定, UPSTREAM 无需调整
- 504 gateway timeout 是 NVCF 侧问题, 非本地 config 可控
- R888 的 TIER_COOLDOWN_S 25→20 已生效 8.5h+, 系统稳定
- EMPTY_200_FASTBREAK + FASTBREAK 正确工作, 已经是最优 fast-break 配置
- 零参数变更, 零风险

## ⏳ 轮到HM1优化HM2