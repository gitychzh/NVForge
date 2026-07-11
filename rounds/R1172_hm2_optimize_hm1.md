# R1172: HM2→HM1 — NOP (false trigger, 40th chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

**Round**: R1172
**Direction**: HM2 → HM1
**Date**: 2026-07-11 12:35 UTC+8
**Author**: opc2_uname

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `7be735e` (R1171) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — **false trigger** (40th consecutive chain of R1133)

## 2. 容器状态

| 容器 | 状态 |
|------|------|
| nv_gw | Up 10 hours (healthy), restarted 2026-07-11 03:03 CST |
| ms_gw | Up 33 hours (healthy) |
| logs_db | Up (healthy) |

## 3. 改前数据 (2026-07-11 06:35–12:35 UTC, 6h)

### 3.1 总体统计

| 指标 | 值 |
|------|-----|
| 总请求 | 32 |
| 成功 (200) | 13 |
| 失败 (502) | 19 |
| 成功率 | **40.6%** |
| 路径 | 100% nv_integrate (glm5_2_nv) |
| dsv4p_nv 流量 | 0 (6h) |
| kimi_nv 流量 | 0 (6h) |
| minimax_m3_nv 流量 | 0 (6h) |
| fallback 触发 | 0 |
| nv_tier_attempts | 3× 429_integrate_rate_limit (glm5_2_nv, 仅速率限制) |
| ms_gw (nv_gw→ms_gw) | 0 traffic |

### 3.2 按路径分组

| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nv_integrate | 32 | 13 | 4769ms | 4906ms | 12569ms |

### 3.3 错误分类 (6h)

| error_type | cnt | 模型 |
|------------|-----|------|
| zombie_empty_completion | 19 | glm5_2_nv |

### 3.4 最近 10 条请求

| ts | 模型 | 路径 | 状态 | ttfb_ms | dur | 错误 |
|----|------|------|------|---------|-----|------|
| 04:33:34 | glm5_2_nv | integrate | 502 | 3296 | 3297 | zombie_empty_completion |
| 04:33:24 | glm5_2_nv | integrate | 200 | 3812 | 3813 | — |
| 04:03:36 | glm5_2_nv | integrate | 502 | 6059 | 6060 | zombie_empty_completion |
| 04:03:25 | glm5_2_nv | integrate | 200 | 5251 | 5251 | — |
| 03:33:34 | glm5_2_nv | integrate | 502 | 7678 | 7679 | zombie_empty_completion |
| 03:33:24 | glm5_2_nv | integrate | 200 | 3730 | 3731 | — |
| 03:03:34 | glm5_2_nv | integrate | 502 | 4937 | 4937 | zombie_empty_completion |
| 03:03:24 | glm5_2_nv | integrate | 200 | 3649 | 3650 | — |
| 02:33:33 | glm5_2_nv | integrate | 502 | 3596 | 3597 | zombie_empty_completion |
| 02:33:24 | glm5_2_nv | integrate | 200 | 4302 | 4303 | — |

**模式**: 完美交替 OK↔zombie, 每 30 分钟一次。13 条成功请求全部 1st-key 成功 (3-5s)。19 条 zombie 全部 3-8s 内网关检测+错误注入。

### 3.5 24h 全景

| 模型 | 请求 | 成功 | SR | avg_dur |
|------|------|------|-----|---------|
| glm5_2_nv | 213 | 171 | 80.3% | 17,156ms |
| dsv4p_nv | 33 | 26 | 78.8% | 27,684ms |
| minimax_m3_nv | 9 | 9 | 100% | 14,483ms |
| kimi_nv | 7 | 7 | 100% | 3,605ms |

24h 错误: 36 zombie_empty_completion, 7 all_tiers_exhausted, 6 NVStream_TimeoutError

### 3.6 容器日志 (最近 200 行)

- 全部 glm5_2_nv integrate: 成功请求 100% 1st-key 成功 (3-4s)
- 每 30 分钟 zombie 模式: `[NV-ZOMBIE-EMPTY]` → `[NV-ZOMBIE-ERROR-CHUNK]` finish_reason=content_filter
- 输入: 164K-169K chars (不断增长: 165733→166427→166410→167104→167613→168388→168712→169487→169997)
- 网关检测正确, 错误注入 3-8s (vs 旧 96s NVStream_TimeoutError)
- 无 NV-TIER-FAIL, 无 NV-EMPTY-200, 无 peer-fb, 无 ms_gw fallback
- 无 NVCFPexecTimeout, 无 SSLEOFError, 无 504

### 3.7 ms_gw 状态

- 容器: Up 33 hours (healthy)
- 最近: glm5_2_ms + deepseek-v4-pro 请求, 全部 MS-OK-STREAM 成功
- 0 次 nv_gw→ms_gw fallback
- 1 次 MS-STREAM-CLIENT-EOF BrokenPipeError (client disconnect, 非 ms_gw 故障)

## 4. 配置状态 (docker exec nv_gw env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | R1088 optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | R1116 optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | R1035 optimal |
| TIER_COOLDOWN_S | 15 | R1103 optimal |
| KEY_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 optimal |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | R1036 optimal |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | R839 optimal |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned with UPSTREAM |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 defensive |
| NV_INTEGRATE_MODELS | glm5_2_nv | R838b |
| NV_KEY_INTEGRATE_KEYS | dsv4p_nv:5;minimax_m3_nv:5 | R838b |

## 5. 决策: NOP

**零参数修改, 零 compose 编辑, 零容器重启。**

理由:
1. **False trigger**: HM2 自提交 round file, 40th consecutive chain of R1133, 不应触发 HM2 优化 HM1
2. **所有失败均为 zombie_empty_completion**: NVCF content-filter 行为 (stop+12chars, 164K-169K input), 非 config 可修复
3. **网关检测 + 错误注入正确**: 3-8s 完成 (vs 旧 96s NVStream_TimeoutError), 已是最优
4. **成功请求 100% 1st-key 成功**: 13/13 OK 全部 3-5s, 无配置问题
5. **dsv4p_nv/kimi_nv/minimax_m3_nv 零流量 6h**: 无数据可分析
6. **ms_gw 无 nv_gw→ms_gw fallback**: 无 fallback 路径问题可分析
7. **所有参数 floor/optimal**: 无可调空间 (UPSTREAM=66 floor, FASTBREAK=1 floor, COOLDOWN=0 floor, BUDGET 已适度宽松)
8. **24h 7 ATE 全部 pre-6h**: 当前窗口无 ATE
9. **铁律: 只改 HM1 不改 HM2**

## ⏳ 轮到HM1优化HM2