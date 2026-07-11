# R1168: HM2→HM1 — NOP (false trigger, 36th chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `e5192e2` by `opc2_uname` (R1167 NOP)
- 判定: **false trigger** — HM2 自提交, 36th consecutive chain of R1133

## 6h 数据 (改前必有数据)

| 指标 | 值 |
|------|-----|
| 总请求 | 37 |
| 成功 (200) | 12 |
| 失败 (502) | 25 |
| 成功率 | **32.4%** |
| 路径 | 100% nv_integrate (glm5_2_nv) |
| dsv4p_nv 流量 | 0 (6h) |
| fallback 触发 | 0 |
| nv_tier_attempts | 3× 429_integrate_rate_limit (glm5_2_nv, 仅速率限制) |
| ms_gw (nv_gw→ms_gw) | 0 traffic |

### 按路径分组
| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nv_integrate | 37 | 12 | 4622ms | 4740ms | 12569ms |

### 错误分类
| error_type | cnt |
|------------|-----|
| zombie_empty_completion | 25 |

### 僵尸模式详情
- glm5_2_nv integrate, NVCF content-filter stop+12chars
- 输入: 164K-168K chars (不断增长)
- 网关检测: `[NV-ZOMBIE-EMPTY]` → `[NV-ZOMBIE-ERROR-CHUNK]` finish_reason=content_filter
- 检测准确, 错误注入正确, 3-7s 内完成 (vs 旧 96s NVStream_TimeoutError)
- 这是 **NVCF 内容过滤行为**, 非 config 可修复

## 配置状态

### nv_gw 容器 (docker exec env)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | R1031 optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | R1116 optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| TIER_COOLDOWN_S | 15 | R1103 optimal |
| KEY_COOLDOWN_S | 25 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | R1039 optimal |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 | optimal |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned with UPSTREAM |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 defensive |

### ms_gw 状态
- 容器: Up 32 hours (healthy)
- 6h 流量: 少量 glm5_2_ms / deepseek-v4-pro 请求, 全部 MS-OK-STREAM
- ms_gw 健康, 0 错误

## 决策: NOP

**零参数修改, 零 compose 编辑, 零容器重启。**

原因:
1. 所有参数均已达到 floor/optimal — 无可调空间
2. 25/25 失败全部为 zombie_empty_completion — NVCF content-filter 行为, 非 config 可修复
3. 网关检测 + 错误注入正确 (3-7s vs 旧 96s)
4. dsv4p_nv 0 traffic 6h, ms_gw 0 nv_gw→ms_gw fallback
5. 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2

