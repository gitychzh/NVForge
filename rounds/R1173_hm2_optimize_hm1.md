# R1173: HM2→HM1 — NOP (false trigger, 41st chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

**Round**: R1173
**Direction**: HM2 → HM1
**Date**: 2026-07-11 12:45 UTC+8
**Author**: opc2_uname

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `bc4f981` (R1172) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — **false trigger** (41st consecutive chain of R1133)

## 2. 容器状态

| 容器 | 状态 |
|------|------|
| nv_gw | Up 11 hours (healthy), restarted 2026-07-11 03:03 CST |
| ms_gw | Up 34 hours (healthy) |
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
| ms_gw (nv_gw→ms_gw) | 0 traffic |

### 3.2 按路径分组

| upstream_type | cnt | ok | avg_dur | max_dur |
|---------------|-----|-----|---------|---------|
| nv_integrate | 32 | 13 | 4906ms | 12569ms |

### 3.3 错误分类 (6h)

| error_type | cnt | 模型 | avg_dur | max_dur |
|------------|-----|------|---------|---------|
| zombie_empty_completion | 19 | glm5_2_nv | 5010ms | 12569ms |

### 3.4 小时分布

| Hour (UTC) | Total | OK | Fail | SR% |
|-----------|-------|-----|------|-----|
| 23:00 | 9 | 4 | 5 | 44.4 |
| 00:00 | 7 | 1 | 6 | 14.3 |
| 01:00 | 4 | 2 | 2 | 50.0 |
| 02:00 | 4 | 2 | 2 | 50.0 |
| 03:00 | 4 | 2 | 2 | 50.0 |
| 04:00 | 4 | 2 | 2 | 50.0 |

### 3.5 per-key 延迟 (glm5_2_nv)

| Key | Total | OK | P50 | P75 | P95 | avg | max |
|-----|-------|-----|-----|-----|-----|-----|-----|
| K1 | 6 | 3 | 3986 | 4961 | 10581 | 5486 | 12357 |
| K2 | 5 | 2 | 3983 | 6060 | 8815 | 5326 | 9504 |
| K3 | 6 | 3 | 3807 | 4134 | 4763 | 3874 | 4937 |
| K4 | 9 | 3 | 3731 | 6566 | 10307 | 5274 | 12569 |
| K5 | 6 | 2 | 3894 | 4587 | 6930 | 4455 | 7679 |

均匀分布, 无关键异常。K3 P50/P75 最低 (3807/4134ms)。

### 3.6 最近 10 条请求

| created_at | 模型 | key | 状态 | dur | ttfb | 错误 |
|-----------|------|-----|------|-----|------|------|
| 04:33:38 | glm5_2_nv | K4 | 502 | 3297 | 3296 | zombie_empty_completion |
| 04:33:28 | glm5_2_nv | K3 | 200 | 3813 | 3812 | — |
| 04:03:42 | glm5_2_nv | K2 | 502 | 6060 | 6059 | zombie_empty_completion |
| 04:03:30 | glm5_2_nv | K1 | 200 | 5251 | 5251 | — |
| 03:33:42 | glm5_2_nv | K5 | 502 | 7679 | 7678 | zombie_empty_completion |
| 03:33:28 | glm5_2_nv | K4 | 200 | 3731 | 3730 | — |
| 03:03:39 | glm5_2_nv | K3 | 502 | 4937 | 4937 | zombie_empty_completion |
| 03:03:28 | glm5_2_nv | K2 | 200 | 3650 | 3649 | — |
| 02:33:37 | glm5_2_nv | K1 | 502 | 3597 | 3596 | zombie_empty_completion |
| 02:33:28 | glm5_2_nv | K5 | 200 | 4303 | 4302 | — |

**模式**: 完美交替 OK↔zombie, 每 30 分钟一次。13 条成功全部 1st-key 成功 (3-5s)。19 zombie 全部 3-8s gateway 检测。

### 3.7 容器日志

- 全部 glm5_2_nv integrate: `NV-INTEGRATE-SUCCESS` on first attempt (1/7)
- 每 30 分钟 zombie: `[NV-ZOMBIE-EMPTY]` → `[NV-ZOMBIE-ERROR-CHUNK]` finish_reason=content_filter
- 输入: 165K-170K chars (不断增长模式)
- Gateway 检测正确, 错误注入 3-8s
- 无 NV-TIER-FAIL, 无 NV-EMPTY-200, 无 peer-fb, 无 ms_gw fallback
- 3× 429_integrate_rate_limit (nv_tier_attempts), 1× IntegrateRemoteDisconnected, 1× IntegrateTimeout

### 3.8 24h 全景

| 模型 | 请求 | 成功 | SR | 错误 |
|------|------|------|-----|------|
| glm5_2_nv | 213 | 171 | 80.3% | 36 zombie, 6 NVStream_TimeoutError |
| dsv4p_nv | 33 | 26 | 78.8% | 7 ATE (全部 pre-6h, 06:00-18:00 UTC) |
| minimax_m3_nv | 9 | 9 | 100% | — |
| kimi_nv | 7 | 7 | 100% | — |

dsv4p_nv ATEs daily distribution: 2@06:00, 1@08:00, 1@09:00, 1@15:00, 1@16:00, 1@18:00 — sparse pattern, no current trend.

## 4. 配置状态

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | R1088 optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 (bug-confirmed no-op) |
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
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 correct |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | R1036 optimal |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | R839 optimal |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| Compose md5 | 7975939c245761e451a8813852dcb9bf | 48h+ unchanged |

## 5. 决策: NOP

**零参数修改, 零 compose 编辑, 零容器重启。**

理由:
1. **False trigger (41st chain of R1133)**: HM2 自提交 round file, 不应触发 HM2 优化 HM1
2. **所有失败均为 zombie_empty_completion**: NVCF content-filter (stop+12chars, 164K-170K input), 非配置可修复
3. **Gateway 检测 + 错误注入正确**: 3-8s 完成, 已是最优 (vs 旧 96s NVStream_TimeoutError)
4. **成功请求 100% 1st-key 成功**: 13/13 OK 全部 3-5s, 无配置问题
5. **6h 仅 glm5_2_nv 流量**: dsv4p_nv/kimi_nv/minimax_m3_nv 零流量, 无数据可分析
6. **dsv4p_nv ATEs 全部 pre-6h** (stale, 06:00-18:00 UTC), 无当前趋势
7. **ms_gw 无 nv_gw→ms_gw fallback**: 正常独立处理 glm5_2_ms + deepseek-v4-pro
8. **所有参数 floor/optimal**: 无可调空间
9. **Compose md5 48h+ 未变**: 无配置漂移
10. **铁律: 只改 HM1 不改 HM2**

## ⏳ 轮到HM1优化HM2