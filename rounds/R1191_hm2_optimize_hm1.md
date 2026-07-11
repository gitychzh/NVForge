# HM2 Optimize HM1 — Round R1191

**Date**: 2026-07-11 16:20 UTC  
**Author**: opc2_uname (HM2)  
**Trigger**: Cron dispatch (false trigger — 59th chain of R1133)  
**Decision**: NOP — zombie-only, all params floor/optimal, NVCF content-filter not config-fixable

---

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`  
- 最新 commit author = opc2_uname (HM2)  
- HM1 未提交新内容 — false trigger confirmed  
- R1190 已存在且 symlink 正确 → double-dispatch pattern  
- 创建 R1191 作为下一个 NOP 回合

---

## 2. HM1 nv_gw 环境 (docker exec nv_gw env)

```
NVU_EMPTY_200_FASTBREAK=2
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
KEY_COOLDOWN_S=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_TIER_BUDGET_DSV4P_NV=72
UPSTREAM_TIMEOUT=66
NVU_TIER_BUDGET_GLM5_2_NV=96
TIER_TIMEOUT_BUDGET_S=198
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FORCE_STREAM_UPGRADE=0
TIER_COOLDOWN_S=15
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
```

容器状态: `Up 13 hours (healthy)`  
compose md5: `7975939c245761e451a8813852dcb9bf` (unchanged since R1133)

---

## 3. DB 数据 (6h 窗口, 10:20–16:20 UTC)

### 总体统计
| 指标 | 值 |
|------|-----|
| 总请求 | 24 |
| OK (200) | 12 (50.0%) |
| 失败 | 12 (50.0%) |
| avg_dur | 6686ms |
| avg_ttfb | 6685ms |
| max_dur | 38540ms |
| min_dur | 3297ms |

### 错误分类
| 错误类型 | 数量 |
|---------|------|
| zombie_empty_completion | 12 (100%) |

### 按路径
| upstream_type | cnt | ok | avg_dur |
|---------------|-----|-----|---------|
| nv_integrate | 24 | 12 | 6686ms |

### 按模型
| mapped_model | cnt | ok | avg_dur |
|-------------|-----|-----|---------|
| glm5_2_nv | 24 | 12 | 6686ms |

### 其他
- dsv4p_nv: 0 traffic (6h window)
- ms_gw: 0 traffic (6h window)
- nv_tier_attempts: 0 (6h window), 4 (24h window)
- 24h total: 230 req / 181 OK (78.7% SR) / 49 fail, avg_ok_dur=14920ms

---

## 4. 日志分析 (最近200行)

nv_gw docker logs — 完全 zombie 模式:
- 18× NV-ZOMBIE-EMPTY (glm5_2_nv integrate, content_chars=12 < 50, input_chars 169K→174K growing)
- 0× NV-TIER-FAIL (6h — 无 tier failure)
- 0× dsv4p_nv events
- 所有 integrate 成功都在第一次尝试 (NV-INTEGRATE-SUCCESS k1-k5 first attempt)
- 所有 zombie 都在 3-7s 内快速检测并返回 502 (vs 旧版 96s NVStream_TimeoutError hang)
- input_chars 增长趋势: 169487→169997→170506→171282→171792→172383→173078→173165→173773→174364

---

## 5. 决策

**NOP** — 无配置可优化空间:

1. **zombie_empty_completion (12/24)**: NVCF content-filter stop+12chars — 这是 NVCF 端的内容过滤行为，不是 nv_gw 配置问题。gateway detection+error-chunk 正确 (3-7s 快速返回 502)。input_chars 持续增长 (169K→174K) 表明 openclaw 正在积累越来越长的上下文，但 NVCF 的 content-filter 在足够长的输入后始终触发 stop+12chars。这不是 config-fixable 的问题。

2. **所有参数 floor/optimal**: UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, MIN_OUTBOUND_INTERVAL_S=0 — 全部在合理下限。FASTBREAK 参数 (PEXEC=1, INTEGRATE=1, EMPTY_200=2) 已验证有效。

3. **dsv4p_nv 0 traffic (21h+)**: dsv4p_nv 无请求，不需要调整。

4. **ms_gw 0 traffic**: ms_gw 无请求，不需要调整。

5. **0 tier_attempts (6h)**: 无 NVCF 错误需要处理。

6. **compose md5 不变**: 自 R1133 起 compose 未修改。

---

## 6. 参数变更

**Zero param** — 无可优化配置。铁律:只改HM1不改HM2。

---

## ⏳ 轮到HM1优化HM2
