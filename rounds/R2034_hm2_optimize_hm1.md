## R2034 (HM2→HM1): NOP — R2030 regime 连续第 4 轮验证稳定, 6h SR 88.24%, 0 真 ATE, 0 peer-fb, 4 zombie 全 NVCF 噪声

### 数据收集
- 容器: `nv_gw` Up 43min (healthy), `logs_db` Up 3d
- 日志: 零 ERROR/WARN, 仅 Listening 行 + 正常请求流

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
| 6h | 34 | 30 | 4 | 88.24% | 4 zombie NVCF噪声, 与 R2033 完全持平 |
| 30min | 3 | 3 | 0 | 100% | clean |

- **失败明细**: 4 全部 zombie_empty_completion (glm5_2_nv, NVCF content_filter 函数级噪声), 0 ATE, 0 peer-fb, 0 NVStream_IncompleteRead, 0 NVAnth
- **key_cycle_429s**: 21/34 (61.76%), 20×1次 + 1×2次, 全部 status=200 — key rotation 正常工作, 与 R2033(61.76%) 完全持平
- **OK 延迟**: 6h avg=7,870ms, min=1,696ms, max=28,697ms << 153s BUDGET; 30min avg=14,317ms (仅 3 请求, 方差噪声)
- **tier_attempts**: 22 total (glm5_2_nv), 21 pexec_success + 1 pexec_429 (被 cooldown 兜住), avg=8,076ms
- **fallback**: 0/34 (全部 f)
- **peer-fb**: 0/34 (6h 零 peer-fallback 事件)
- **ATE (status=502)**: 0 (6h 零真 ATE, 与 R2033 连续 4 轮零 ATE 一致)

### 优化决策: NOP
介入四条全不满足:
1. 非zombie失败: 0 ✓
2. 真ATE (status=502): 0 ✓
3. key_cycle_429s 导致失败: 0 ✓
4. 延迟回归: 无 (6h avg 7,870ms 与 R2033 持平, 30min 14,317ms 仅 3 请求方差) ✓

R2030 KEY_COOLDOWN_S=60 + TIER_COOLDOWN_S=60 已连续 4 轮 (R2031→R2034) 验证稳定。4 次 zombie 全部是 NVCF 函数级 content_filter 噪声, 不可配置。唯一 429 被 cooldown 兜住无失败。429 cycling 率 61.76% 与 R2033 完全持平, key 轮转正常运行。peer-fb 连续 4 轮零事件, 无 rescue 需求。冻结理由仍成立。

### 约束
- 60+60+28=148 << 153 BUDGET (5s 余量) ✓
- UPSTREAM=28 + PEER=122 = 150 < 153 ✓
- 铁律: 只改 HM1 不改 HM2 ✓
## ⏳ 轮到HM1优化HM2
