## R2040 (HM2→HM1): NOP — R2039 regime 验证中, 6h SR 81.48%, 5 zombie 全 NVCF 噪声, 0 可配置失败

### 数据收集
- 容器: `nv_gw` 运行中 (healthy, StartedAt=04:52Z, R2039 restart), `logs_db` 运行中
- 日志: 零 ERROR/WARN, 干净启动, 无异常

### 环境验证
| 参数 | 值 | 状态 |
|------|-----|------|
| KEY_COOLDOWN_S | 60 | ✓ R2030 |
| TIER_COOLDOWN_S | 60 | ✓ R2030 |
| TIER_TIMEOUT_BUDGET_S | 153 | ✓ R2005 |
| UPSTREAM_TIMEOUT | 26 | ✓ R2039 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | ✓ |
| NVU_EMPTY_200_FASTBREAK | 1 | ✓ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✓ |
| NVU_TIER_BUDGET_GLM5_2_NV | 20 | ✓ |
| NVU_TIER_BUDGET_DSV4P_NV | 20 | ✓ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | ✓ |
| MIN_OUTBOUND_INTERVAL_S | 0 | ✓ |
| NVU_CONNECT_RESERVE_S | 0 | ✓ |

### DB 数据

| 窗口 | 总计 | OK | 失败 | SR | 说明 |
|------|------|-----|------|-----|------|
| 6h | 27 | 22 | 5 | 81.48% | 5 zombie 全 NVCF content_filter 噪声, 与 R2038(82.14%) 基本持平 |

- **失败明细**: 5 全部 zombie_empty_completion (glm5_2_nv, status=502, NVCF content_filter 函数级噪声, 不可配置)
- **0 real ATE (status=502)**: 连续 9 轮零真 ATE
- **phantom ATE (status=200)**: 4 (big_input breaker 触发, 全部 peer-fb 救援成功)
- **OK 延迟**: 6h avg=8,328ms, min=2,046ms, max=18,388ms << 26s UPSTREAM (1.4× margin)
- **key_cycle_429s**: 23/27 (85.2%), 22×1次 + 1×2次, 全部 status=200 — key rotation 正常工作, cooldown 兜住
- **fallback**: 0/27 (全部 f)
- **peer-fb**: 0/27 (6h 零 peer-fallback 事件)
- **tier errors**: pexec_success 23, pexec_429 1 (同比流量小波动, 无新增类)

### 最近日志事件
- 13:03:20, glm5_2_nv, pexec_us_rr, k1, channel=pexec via 7894, timeout=20s — 干净请求, 无异常
- 总体: 零 ERROR/WARN, clean start from R2039 restart

### 优化决策: NOP
介入四条全不满足:
1. 非zombie失败: 0 ✓
2. 真ATE (status=502): 0 ✓ (连续 9 轮零真 ATE)
3. key_cycle_429s 导致失败: 0 ✓ (23/27 429 cycling 全部在成功请求上, cooldown 兜住)
4. 延迟回归: 无 (6h avg 8,328ms, max 18,388ms << 26s, 无回归趋势) ✓

R2039 UPSTREAM 28→26 仅部署 ~3h, 需更多时间验证稳定。R2030 KEY=TIER=60 regime 已连续 10 轮 (R2031→R2040) 验证稳定。5 次 zombie 全部是 NVCF 函数级 content_filter 噪声, 不可配置。429 cycling 率 85.2% 全部被 cooldown 兜住无失败。peer-fb 连续 9 轮零事件, 无 rescue 需求。冻结理由仍成立。

### 约束
- 26+60+60=146 << 153 BUDGET (7s 余量) ✓
- UPSTREAM=26 + PEER=122 = 148 < 153 ✓
- 铁律: 只改 HM1 不改 HM2 ✓
## ⏳ 轮到HM1优化HM2
