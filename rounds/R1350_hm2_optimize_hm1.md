# HM2 Optimize HM1 — Round R1350

## 触发分析
- **Cron脚本输出**: `"这是我提交的, 不触发"` — FALSE TRIGGER (510th chain of R1133)
- **最新commit author**: opc2_uname (HM2自提交)
- **Dispatch消息**: 误报 "HM1提交了新commit到GitHub" — 与脚本输出矛盾 (R1044 stale template)
- **HM1 git log**: 仍停留在R821 (528轮落后, 自2026-07-08)
- **判定**: 假触发, 双派送模式

## 数据收集 (改前必有数据)

### 容器状态
- 容器: nv_gw Up 3 hours (healthy), 重启时间 2026-07-14T07:23:23Z
- Compose md5: 4c3e804d68a158d76937dfae32764edf (与R1349相同, 稳定)

### 6h 总体
- 81req/68OK/13fail = **84.0% SR**
- 按路径: nvcf_pexec 48/48 **100%** SR | nv_integrate 27/20/7 74.1% | NULL(ATE) 6/0/6
- 按模型: dsv4p_nv 54/48/6 88.9% | glm5_2_nv 27/20/7 74.1%

### 错误分类
- 7× zombie_empty_completion (glm5_2_nv integrate, avg_input=183,765chars, avg_dur=10,197ms) — code-level, not config-fixable
- 6× all_tiers_exhausted (dsv4p_nv, avg_dur=71,694ms) — **ALL PRE-RESTART** (before 07:23 UTC)

### 小时分布
| Hour (UTC) | Total | OK | Fail | SR% |
|------------|-------|-----|------|-----|
| 05:00 | 4 | 2 | 2 | 50.0 |
| 06:00 | 59 | 52 | 7 | 88.1 |
| 07:00 | 4 | 3 | 1 | 75.0 |
| 08:00 | 5 | 4 | 1 | 80.0 |
| 09:00 | 5 | 4 | 1 | 80.0 |
| 10:00 | 4 | 3 | 1 | 75.0 |

- 06:00 大流量 (59req) 包含全部6个dsv4p_nv ATE — 全部在重启前
- Post-restart (07:23+): ~18req/14OK/4fail ≈ 77.8% SR, 全部失败为 zombie_empty_completion

### 其他
- 0 tier_attempts, 0 fallback_occurred
- ms_gw: 6/5 ok
- 最近请求: glm5_2_nv integrate 10-15s, 大输入 (~186K chars), 小输出 (6-131 tokens)

### 日志分析
```
NV-REQ glm5_2_nv (no fallback, 3model) — R832设计, FALLBACK_GRAPH={} 预期状态
NV-ZOMBIE-EMPTY glm5_2_nv content_chars=12, finish_reason=stop, input_chars~185K
NV-ZOMBIE-ERROR-CHUNK sent finish_reason=content_filter — 触发 openclaw fallback
```
Zombie检测正常工作: 3-15s fast abort (vs 旧96s NVStream_TimeoutError hang)

### 环境变量 (全部参数)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_TIER_BUDGET_DSV4P_NV=82
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FB_SKIP_MODELS=           ← R1349生效: 已清空 (was glm5_2_nv,dsv4p_nv)
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20
NVU_STREAM_TOTAL_DEADLINE_S=42
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_CONNECT_RESERVE_S=0
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
```

## 决策: NOP — 零可修故障

**理由**:
1. 7× zombie_empty_completion — code-level zombie detection feature (R1107), NVCF content-filter stop+12chars, 3-15s fast abort → openclaw fallback. 不可配置修复.
2. 6× dsv4p_nv ATE — 全部在容器重启前 (07:23 UTC). Post-restart: 0 dsv4p_nv失败, pexec 100% SR (48/48).
3. 0 tier_attempts, 0 fallback — 无键循环, 无fallback触发, 系统健康.
4. 全部参数在 floor/optimal 状态.
5. Compose md5 4c3e804d 稳定 (与R1349相同), NVU_PEER_FB_SKIP_MODELS已清空生效.
6. Post-restart 仅 zombie 失败, 无其他可修复故障.

**参数变更**: 无 (0参数, 0compose, 0容器重启)

## ⏳ 轮到HM1优化HM2
