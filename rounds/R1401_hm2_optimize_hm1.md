# R1401: HM2→HM1 — NOP (false trigger, 零可修故障, 560th chain of R1133)

## 触发
- 脚本检测到HM1提交了新commit到GitHub (f5c0971 R1400)，触发HM2优化回合
- 实际: R1400是HM2→HM1的回合，非HM1→HM2提交。真·false trigger

## 6h 数据 (nv_gw 容器重启后 ~1h)

| 指标 | 值 |
|------|-----|
| **总请求** | 8 |
| **成功** | 6 (75.0% SR) |
| **失败** | 2 zombie_empty_completion |
| **tier_attempts** | 0 |
| **fallback** | 0 |
| **ms_gw** | 0/0 |
| **dsv4p_nv** | 0 traffic |
| **kimi_nv/minimax_m3_nv** | 0 traffic |

### 失败详��
- 2 zombie_empty_completion, 全部 glm5_2_nv integrate (code-level, NVCF content-filter: `content_chars<50, input_chars>=5000, finish_reason=stop`)
- 0 ATE, 0 timeout, 0 empty_200, 0 rate_limit

### 日志特征
- 全部 NV-INTEGRATE-SUCCESS on first attempt (k1-k5 轮转正常)
- NV-ZOMBIE-EMPTY pattern: content_chars=8-49, input_chars=90K-206K, finish_reason=stop → content_filter error SSE chunk to openclaw
- 无 error/warn 级别异常

## 24h 数据

| 指标 | 值 |
|------|-----|
| **dsv4p_nv** | 65/57/8 ATE (87.7% SR) |
| **ATE 全部 pre-restart** | 最新 18:03 UTC July 14, 容器重启后 0 ATE |
| **zombie_empty_completion** | 29 (全部 glm5_2_nv, code-level) |

## 配置验证

- compose md5: f493494e2b41b17fbf5d9cff9093648e (不变)
- 容器 env: 全部参数 floor/optimal
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, TIER_COOLDOWN_S=15
  - NVU_TIER_BUDGET_DSV4P_NV=106, NVU_TIER_BUDGET_GLM5_2_NV=96
  - FASTBREAKs: NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2
  - NVU_PEER_FB_SKIP_MODELS=(空), NVU_PEER_FALLBACK_ENABLED=1
  - NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_FALLBACK_HEALTH_THRESHOLD=0.05
  - KEY_COOLDOWN_S=25, KEY_AUTHFAIL_COOLDOWN_S=60

## 决策: NOP

- **零可修故障**: zombie_empty_completion 是 NVCF 代码级问题 (content-filter 返回 stop 但 content_chars<50)，非配置可修复
- **0 ATE post-restart**: dsv4p_nv 预算 106 自 R1370 生效后持续验证有效
- **全部参数 floor/optimal**: 无参数调整空间
- **0 tier_attempts, 0 fallback, 0 rate_limit**: 基础设施健康

## 变更
- 无 (NOP)

## 铁律
- 只改HM1不改HM2 (未改任何配置)
## ⏳ 轮到HM1优化HM2
