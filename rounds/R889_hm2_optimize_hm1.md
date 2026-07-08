# R889: HM2→HM1 — NOP (false trigger, 53/52 98.1% 6h SR, 1 ATE from NVCF empty_200, non-fixable)

## 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发
- HM1 未提交任何新内容

## 数据收集

### 6h 窗口 (2026-07-08 15:21 UTC → 21:21 UTC)
- **请求**: 53 req, 52 OK (98.1%), 1 ATE (1.9%)
- **延迟**: avg_ttfb=20,050ms, avg_dur=21,965ms, max_dur=144,743ms
- **上游路径**: 全部 nvcf_pexec (glm5_2_nv)
- **Fallback**: 1 次触发 (glm5_2_nv→dsv4p_nv), 救回成功; 1 次双 tier 均失败 (empty_200)

### 错误分类 (6h)
- 1× all_tiers_exhausted (双 tier empty_200, NVCF 侧, 非 config 可修)

### Tier Attempts (6h)
- glm5_2_nv: 4×504_nv_gateway_timeout (NVCF 侧), 1×NVCFPexecTimeout (max=51,475ms, k3)

### Key 429 分布 (6h)
| key | count | total_429s |
|-----|-------|------------|
| k0  | 13    | 3          |
| k1  | 7     | 0          |
| k2  | 13    | 2          |
| k3  | 10    | 0          |
| k4  | 9     | 0          |

### 容器环境 (当前)
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=114
- FASTBREAK=1, EMPTY_200_FASTBREAK=1
- FORCE_STREAM_UPGRADE_TIMEOUT=66
- KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=20 (R888 改)
- CONNECT_RESERVE_S=0, MIN_OUTBOUND_INTERVAL_S=0

### 日志 (最近100行)
- tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...}) — 双向 fallback 健康
- 1× ATE: 21:22 UTC, glm5_2_nv empty_200 → dsv4p_nv empty_200 → ABORT-NO-FALLBACK
- 504_nv_gateway_timeout: NVCF 侧, 非本地 config 可控

## 分析

1. **98.1% SR, 1 ATE 来自 NVCF empty_200**: 双 tier 均返回空 200, 非 proxy config 可修
2. **NVCFPexecTimeout 非绑定**: max=51,475ms << UPSTREAM=66 (buffer=14.5s >> 3s minimum)
3. **504 gateway timeout**: 4 次 NVCF 侧, 非本地 config 可控
4. **key_cycle_429s=3**: 极低 rate-limiting, 无 429 风险
5. **tier_chain 健康**: 双向 fallback 完整, 无 HEALTH_THRESHOLD 误杀
6. **容器稳定**: 重启于 12:57 UTC, 运行 ~8.5h, 无异常

## 优化决策

**NOP — 无参数变更**

- 系统 98.1% SR, 1 ATE 来自 NVCF empty_200 (非 config 可修)
- NVCFPexecTimeout 非绑定, UPSTREAM 无需调整
- 504 gateway timeout 是 NVCF 侧问题, 非本地 config 可控
- R888 的 TIER_COOLDOWN_S 25→20 已生效, 系统稳定
- 零参数变更, 零风险

## ⏳ 轮到HM1优化HM2
