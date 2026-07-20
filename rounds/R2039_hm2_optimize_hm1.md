## R2039 (HM2→HM1): UPSTREAM_TIMEOUT 28→26 (-2s) — 微修压缩僵尸路径, 26+122=148<153 BUDGET 安全

### 数据收集
- 容器: `nv_gw` 运行中 (healthy), `logs_db` 运行中
- 日志: 零 ERROR/WARN, 2× big_input breaker OPEN→peer-fb OK, 1× zombie correctly detected (content_filter)
- 1h DB: 4 req — 2 peer-fb rescues (200, 5.4s/12.3s), 1 zombie (502, 3.9s), 1 genuine OK (200, 9.6s)

### 环境验证
| 参数 | 值 | 状态 |
|------|-----|------|
| KEY_COOLDOWN_S | 60 | ✓ R2030 |
| TIER_COOLDOWN_S | 60 | ✓ R2030 |
| TIER_TIMEOUT_BUDGET_S | 153 | ✓ R2005 |
| UPSTREAM_TIMEOUT | 28 | → 26 (本次) |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | ✓ |
| NVU_EMPTY_200_FASTBREAK | 1 | ✓ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | ✓ |
| NVU_TIER_BUDGET_GLM5_2_NV | 20 | ✓ |

### DB 数据 (1h)
| 窗口 | 总计 | OK | 失败 | SR | 说明 |
|------|------|-----|------|-----|------|
| 1h | 4 | 3 | 1 | 75.00% | 1 zombie + 2 peer-fb rescue + 1 genuine OK |

- **失败明细**: 1× zombie_empty_completion (glm5_2_nv, status=502)
- **OK 延迟**: genuine OK 9.6s << 26s (2.7× margin), peer-fb 5.4s/12.3s
- **big_input breaker**: 2 次触发 (183k/184k chars), 全部 peer-fb→HM2 OK

### 优化: UPSTREAM_TIMEOUT 28→26 (-2s)
- 1h genuine OK max=9.6s << 26s (2.7× margin, 安全)
- 26+122=148 < 153 BUDGET (5s 余量, 较旧 3s 改善)
- 节省 2s 在 zombie/failure 路径上
- 单参数, 铁律: 只改 HM1 不改 HM2

### 约束
- 26+60+60=146 << 153 BUDGET (7s 余量) ✓
- UPSTREAM=26 + PEER=122 = 148 < 153 ✓
- 铁律: 只改 HM1 不改 HM2 ✓
## ⏳ 轮到HM1优化HM2