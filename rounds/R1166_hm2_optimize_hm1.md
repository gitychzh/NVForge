# HM2 → HM1 Optimization Round R1166

**Date**: 2026-07-11 11:30 UTC
**Trigger**: Cron dispatch (false trigger — self-commit)
**Decision**: NOP (no parameter changes)

## 1. 触发分析

- Cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author: `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（R1133 zombie-only chain 第35链）
- HM1 本地 git 远落后于 HM2 — 无实际变更

## 2. 6h 数据全景

| 指标 | 值 |
|------|-----|
| 总请求 | 38 |
| 成功 (200) | 14 (36.8%) |
| 失败 (502) | 24 (63.2%) |
| 错误类型 | zombie_empty_completion ×24 |
| 路径 | nv_integrate ×38 |
| 模型 | glm5_2_nv ×38 |
| dsv4p_nv 流量 | 0 |
| ms_gw 流量 | 0 |
| fallback 触发 | 0 |

## 3. 每小时 SR 趋势

| 小时 (UTC) | 总 | OK | 失败 | SR% |
|-----------|-----|-----|------|-----|
| 21:00 | 3 | 3 | 0 | 100.0 |
| 22:00 | 9 | 1 | 8 | 11.1 |
| 23:00 | 9 | 4 | 5 | 44.4 |
| 00:00 | 7 | 1 | 6 | 14.3 |
| 01:00 | 4 | 2 | 2 | 50.0 |
| 02:00 | 4 | 2 | 2 | 50.0 |
| 03:00 | 2 | 1 | 1 | 50.0 |

高峰 21UTC 100% SR → 22UTC 起 zombie 爆发（NVCF content-filter 激活）。

## 4. Zombie 模式分析

```
[NV-INTEGRATE-SUCCESS] tier=glm5_2_nv k<N> succeeded on first attempt (1.7-3.3s)
[NV-ZOMBIE-EMPTY] passthrough zombie empty completion:
  finish_reason=stop but content_chars=12 < 50
  input_chars=164K-168K >= 5000, no tool_calls
[NV-ZOMBIE-ERROR-CHUNK] sent finish_reason=content_filter error SSE chunk
```

- 配对请求: 第一个成功 (INTEGRATE-SUCCESS ~1.7-3.3s), 第二个 zombie (content_chars=12)
- NVCF content-filter stop+12chars, 输入 164K-168K → 函数级行为
- Gateway detection+error-chunk 正确触发
- 不可配置修复 — NVCF 内容过滤功能

## 5. 容器状态

- 最后重启: 2026-07-10T19:03:27Z (运行 ~16h)
- 状态: Up (healthy)
- 零重启后 ATE
- 零 NV-TIER-FAIL, 零 NV-MS-FB, 零 NV-EMPTY-FASTBREAK
- tier_attempts: 仅 3× 429_integrate_rate_limit (minimal)

## 6. 参数状态

全部参数在 floor/optimal:
- UPSTREAM_TIMEOUT=66 (R988), TIER_TIMEOUT_BUDGET_S=198 (R1088)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
- NVU_TIER_BUDGET_DSV4P_NV=72 (R1116), NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_MS_GW_FALLBACK_TIMEOUT=180 (R1036)
- TIER_COOLDOWN_S=15 (R1103), KEY_COOLDOWN_S=25, MIN_OUTBOUND_INTERVAL_S=0
- NV_INTEGRATE_KEY_COOLDOWN_S=0, NVU_CONNECT_RESERVE_S=0
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=20, NVU_STREAM_TOTAL_DEADLINE_S=42
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- compose md5: 7975939c245761e451a8813852dcb9bf (unchanged since R1133)

## 7. 决策

**NOP** — 零参数修改。

- 所有失败均为 zombie_empty_completion (NVCF content-filter → stop+12chars, 164K-168K input)
- dsv4p_nv 0 流量 6h → 无 secondary optimization 路径
- ms_gw 0 流量 6h → 无 secondary optimization 路径
- 所有参数 floor/optimal → 无优化空间
- 配对请求模式: success+zombie 交替, zombie 快速 abort (3-5s)
- 与 R1165 数据完全一致: 38req/14OK(36.8%)/24zombie
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
