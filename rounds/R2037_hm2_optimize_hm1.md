## R2037 (HM2→HM1): NOP — R2030 regime 连续第 7 轮验证稳定, 6h SR 84.85%, 0 ATE, 0 peer-fb, 5 zombie 全 NVCF 噪声

### 数据收集
- 容器: `nv_gw` 运行中 (healthy), `logs_db` 运行中
- 日志: 零 ERROR/WARN, 仅 GLM52 正常请求流 + 1 zombie event (content_filter) + 1 429 (cooldown 兜住)

### 环境验证
| 参数 | 值 | 状态 |
|------|-----|------|
| KEY_COOLDOWN_S | 60 | ✓ R2030 |
| TIER_COOLDOWN_S | 60 | ✓ R2030 |
| TIER_TIMEOUT_BUDGET_S | 153 | ✓ |
| UPSTREAM_TIMEOUT | 28 | ✓ |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | ✓ |
| NVU_EMPTY_200_FASTBREAK | 1 | ✓ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✓ |
| NVU_FORCE_STREAM_UPGRADE | 0 | ✓ |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✓ |
| FALLBACK_HEALTH_THRESHOLD | 0.05 | ✓ |
| NVU_CONNECT_RESERVE_S | 0 | ✓ |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | ✓ |
| NVU_SSLEOF_RETRY_DELAY_S | 0.1 | ✓ |
| NVU_TIER_BUDGET_DSV4P_NV | 20 | ✓ |
| NVU_TIER_BUDGET_GLM5_2_NV | 20 | ✓ |

### DB 数据

| 窗口 | 总计 | OK | 失败 | SR | 说明 |
|------|------|-----|------|-----|------|
| 6h | 33 | 28 | 5 | 84.85% | 5 zombie NVCF噪声, 与 R2036 完全持平 |
| 30min | 2 | 1 | 1 | 50.00% | 仅 2 请求, 1 zombie 方差, 无统计意义 |

- **失败明细**: 5 全部 zombie_empty_completion (glm5_2_nv, status=502, NVCF content_filter 函数级噪声), 0 ATE, 0 peer-fb, 0 NVStream_IncompleteRead, 0 NVAnth
- **key_cycle_429s**: 23/33 (69.7%), 22×1次 + 1×2次, 全部 status=200 — key rotation 正常工作, 与 R2036(69.7%) 完全持平
- **OK 延迟**: 6h avg=8,188ms, min=1,696ms, max=28,697ms << 153s BUDGET; 与 R2036(8,188ms) 完全一致
- **fallback**: 0/33 (全部 f)
- **peer-fb**: 0/33 (6h 零 peer-fallback 事件, 连续 7 轮零事件)
- **ATE (status=502)**: 0 (6h 零真 ATE, 连续 7 轮零 ATE)

### 最近 zombie 详情
- 12:03:34, glm5_2_nv, zombie_empty_completion, content_filter SSE chunk, 触发 cc4101 zombie→api_error→CC retry
- zombie 检测正确: 被 zombie 机正确识别并触发下游重试

### 优化决策: NOP
介入四条全不满足:
1. 非zombie失败: 0 ✓
2. 真ATE (status=502): 0 ✓
3. key_cycle_429s 导致失败: 0 ✓
4. 延迟回归: 无 (6h avg 8,188ms 与 R2036 完全一致) ✓

R2030 KEY_COOLDOWN_S=60 + TIER_COOLDOWN_S=60 已连续 7 轮 (R2031→R2037) 验证稳定。5 次 zombie 全部是 NVCF 函数级 content_filter 噪声, 不可配置。429 cycling 率 69.7% 与 R2036 完全持平, 全部被 cooldown 兜住无失败。peer-fb 连续 7 轮零事件, 无 rescue 需求。冻结理由仍成立。

### 约束
- 60+60+28=148 << 153 BUDGET (5s 余量) ✓
- UPSTREAM=28 + PEER=122 = 150 < 153 ✓
- 铁律: 只改 HM1 不改 HM2 ✓
## ⏳ 轮到HM1优化HM2
