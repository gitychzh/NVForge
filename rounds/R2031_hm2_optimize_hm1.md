## R2031 (HM2→HM1): NOP — R2030 regime 刚部署 8min, 30min 窗口 clean, 0 真 ATE, 0 peer-fb

### 数据收集
- 容器: `nv_gw` Up 8min (healthy), `logs_db` Up 3d
- 日志: 零 ERROR/WARN, 仅 Listening 行

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

### DB 数据

| 窗口 | 总计 | OK | 失败 | SR | 说明 |
|------|------|-----|------|-----|------|
| 6h | 33 | 28 | 5 | 84.8% | 5 zombie NVCF噪声 |
| 30min | 3 | 3 | 0 | 100% | post-deploy clean |

- **失败明细**: 5 全部 zombie_empty_completion (glm5_2_nv, NVCF函数级噪声), 0 ATE, 0 peer-fb
- **key_cycle_429s**: 20/33 (60.6%), 全部 status=200 — key rotation 正常工作
- **OK 延迟**: avg=7079ms, max=28697ms << 153s BUDGET
- **upstream 路径**: pexec=20 (15 OK), NULL=13 (13 OK — 可能为旧regime的NULL上游数据)

### 优化决策: NOP
介入四条全不满足:
1. 非zombie失败: 0 ✓
2. 真ATE (status=502): 0 ✓
3. key_cycle_429s 导致失败: 0 ✓
4. 延迟回归: 无 ✓

R2030 KEY_COOLDOWN_S=60 + TIER_COOLDOWN_S=60 刚部署8分钟，30min 窗口 clean。等待下一轮累积更多 post-deploy 数据再评估。

### 约束
- 60+60+28=148 << 153 BUDGET (5s 余量) ✓
- UPSTREAM=28 + PEER=122 = 150 < 153 ✓
- 铁律: 只改 HM1 不改 HM2 ✓
## ⏳ 轮到HM1优化HM2
