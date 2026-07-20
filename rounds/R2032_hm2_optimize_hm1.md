## R2032 (HM2→HM1): NOP — R2030 regime 运行 21min, 6h SR 88.24%, 0 真实 ATE, 0 peer-fb, 4 zombie 全 NVCF 噪声

### 数据收集
- 容器: `nv_gw` Up 21min (healthy), `logs_db` Up 3d
- 日志: 零 ERROR/WARN, 仅 Listening 行 + GLM52 正常请求流

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

### DB 数据

| 窗口 | 总计 | OK | 失败 | SR | 说明 |
|------|------|-----|------|-----|------|
| 6h | 34 | 30 | 4 | 88.24% | 4 zombie NVCF噪声 |
| 30min | 3 | 3 | 0 | 100% | clean |

- **失败明细**: 4 全部 zombie_empty_completion (glm5_2_nv, NVCF函数级噪声), 0 ATE, 0 peer-fb
- **key_cycle_429s**: 21/34 (61.8%), 20×1次 + 1×2次, 全部 status=200 — key rotation 正常工作
- **OK 延迟**: avg=7,870ms, min=1,696ms, max=28,697ms << 153s BUDGET
- **tier_attempts**: 22 total (glm5_2_nv), 21 pexec_success + 1 pexec_429 (被 cooldown 兜住), avg=8,076ms
- **fallback**: 0/34 (全部 f)

### 优化决策: NOP
介入四条全不满足:
1. 非zombie失败: 0 ✓
2. 真ATE (status=502): 0 ✓
3. key_cycle_429s 导致失败: 0 ✓
4. 延迟回归: 无 ✓

R2030 KEY_COOLDOWN_S=60 + TIER_COOLDOWN_S=60 运行 21min，30min 窗口 clean。4 次 zombie 全部是 NVCF 函数级 content_filter 噪声，不可配置。唯一 429 被 cooldown 兜住无失败。等待下一轮累积更多数据。

### 约束
- 60+60+28=148 << 153 BUDGET (5s 余量) ✓
- UPSTREAM=28 + PEER=122 = 150 < 153 ✓
- 铁律: 只改 HM1 不改 HM2 ✓
## ⏳ 轮到HM1优化HM2
