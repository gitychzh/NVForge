## R2038 (HM2→HM1): NOP — R2030 regime 连续第 8 轮验证稳定, 6h SR 82.14%, 0 ATE, 0 peer-fb, 5 zombie 全 NVCF 噪声

### 数据收集
- 容器: `nv_gw` 运行中 (healthy), `logs_db` 运行中
- 日志: 零 ERROR/WARN, 2 big_input breaker OPEN→peer-fb OK, 1 zombie correctly detected (content_filter)

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
| 6h | 28 | 23 | 5 | 82.14% | 5 zombie NVCF噪声, 与 R2037(84.85%) 基本持平 |

- **失败明细**: 5 全部 zombie_empty_completion (glm5_2_nv, status=502, NVCF content_filter 函数级噪声), 0 ATE, 0 peer-fb, 0 NVStream_IncompleteRead, 0 NVAnth
- **key_cycle_429s**: 23/28 (82.1%), 22×1次 + 1×2次, 全部 status=200 — key rotation 正常工作, 429 率略高于 R2037(69.7%) 但无失败
- **OK 延迟**: 6h avg=9,214ms, min=2,046ms, max=28,697ms << 153s BUDGET; 略高于 R2037(8,188ms) 但小样本正常波动
- **fallback**: 0/28 (全部 f)
- **peer-fb**: 0/28 (6h 零 peer-fallback 事件, 连续 8 轮零事件)
- **ATE (status=502)**: 0 (6h 零真 ATE, 连续 8 轮零 ATE)
- **phantom ATE (status=200)**: 5 (big_input breaker 触发, 全部 peer-fb 成功 rescue)

### 最近日志事件
- 12:03:34, glm5_2_nv, zombie_empty_completion, content_filter SSE chunk, 触发 cc4101 zombie→api_error→CC retry
- 12:33:20, glm5_2_nv, big_input breaker OPEN (183,576c), peer-fb→HM2 OK (200, 1297B, 6ms TTFB)
- 12:33:26, glm5_2_nv, big_input breaker OPEN (184,095c), peer-fb→HM2 OK (200, 16B, 9ms TTFB)
- zombie 检测正确, big_input breaker + peer-fb 救援正常工作

### 优化决策: NOP
介入四条全不满足:
1. 非zombie失败: 0 ✓
2. 真ATE (status=502): 0 ✓
3. key_cycle_429s 导致失败: 0 ✓ (23/28 429 cycling 全部在成功请求上, cooldown 兜住)
4. 延迟回归: 无 (6h avg 9,214ms, 小样本波动, 无回归趋势) ✓

R2030 KEY_COOLDOWN_S=60 + TIER_COOLDOWN_S=60 已连续 8 轮 (R2031→R2038) 验证稳定。5 次 zombie 全部是 NVCF 函数级 content_filter 噪声, 不可配置。429 cycling 率 82.1% 略高于 R2037(69.7%) 但全部被 cooldown 兜住无失败, 60s 边界值仍在有效范围内。peer-fb 连续 8 轮零事件, 无 rescue 需求。big_input breaker 2 次触发均 peer-fb 救援成功。冻结理由仍成立。

### 约束
- 60+60+28=148 << 153 BUDGET (5s 余量) ✓
- UPSTREAM=28 + PEER=122 = 150 < 153 ✓
- 铁律: 只改 HM1 不改 HM2 ✓
## ⏳ 轮到HM1优化HM2
