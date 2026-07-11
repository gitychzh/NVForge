# HM2 Optimize HM1 — Round R1161

## ⏱️ 判定: NOP (false trigger, 30th chain of R1133)

**触发类型**: FALSE TRIGGER — cron 脚本输出 "这是我提交的, 不触发"

### 铁律: 只改HM1不改HM2 ✓

---

## 1. 6h 数据快照 (2026-07-11 ~10:40 UTC)

```
6h: 42req/19OK(45.2%)/23zombie
  └─ glm5_2_nv: 42/19/23 (45.2% SR)
  └─ dsv4p_nv: 0 traffic
  └─ kimi_nv: 0 traffic
  └─ minimax_m3_nv: 0 traffic
  └─ ms_gw: 0 traffic
```

| 维度 | 数值 |
|------|------|
| 总请求 | 42 |
| 成功 | 19 (45.2%) |
| 失败 | 23 (100% zombie_empty_completion) |
| 上游类型 | nv_integrate (100%) |
| fallback_occurred | 0 (全部 f) |
| tier_attempts | 3× 429_integrate_rate_limit (仅) |
| ms_requests | 0 |

## 2. 错误分析

所有23个失败均为 `zombie_empty_completion`:
- glm5_2_nv integrate 模式
- NVCF 返回 finish_reason=stop, content_chars=12, input_chars=164K-167K
- Gateway 在 3-4s 内检测到 zombie → 返回 502 + error-chunk
- 日志: `[NV-ZOMBIE-EMPTY]` + `[NV-ZOMBIE-ERROR-CHUNK]`
- 无 NV-TIER-FAIL, 无 NV-EMPTY-FASTBREAK, 无 NV-MS-FB
- tier_chain=['glm5_2_nv'] (no fallback, 3model) — 预期状态 (FALLBACK_GRAPH={})

这是 NVCF content-filter 的行为 — 对 164K+ 输入返回 stop+12chars。Gateway 的 zombie 检测正确工作，3-4s 快速中止比旧版 96s hang 好得多。代码级特性，非配置可修复。

## 3. 容器状态

- 重启时间: 2026-07-10T19:03:27Z (15.5h 前)
- 运行状态: Up 8 hours (healthy)
- compose md5: 7975939c245761e451a8813852dcb9bf (自 R1133 未变)

## 4. 当前参数 (全部 floor/optimal)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=198
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NV_INTEGRATE_KEY_COOLDOWN_S=0
```

## 5. 决策: NOP (Zero Param)

**理由**:
1. 所有失败 = zombie_empty_completion (NVCF content-filter, 代码级特性)
2. Gateway zombie 检测正确 — 3-4s 快速中止，比 96s hang 好
3. 0 dsv4p_nv / ms_gw 流量 — 所有其他参数当前未被使用
4. 0 ATE, 0 fallback 触发 — 系统无其他故障模式
5. compose md5 自 R1133 未变 — 无配置漂移
6. 所有参数在 floor/optimal — 无优化空间
7. NVCF content-filter 非配置可修复

**Zero param changes. 铁律: 只改HM1不改HM2 ✓**

## 6. 触发分析

- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (R1133 chain 第30轮)
- HM1 compose 未变更，数据与 R1160 一致
- R1133→R1161: 30轮连续 false-trigger NOP, compose md5 不变 48h+

## ⏳ 轮到HM1优化HM2

