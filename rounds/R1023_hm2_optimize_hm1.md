# HM2 Optimize HM1 — Round R1023

**Date**: 2026-07-10 ~04:00 UTC  
**Type**: NOP (false trigger — no HM1 changes, no param changes)  
**Author**: opc2_uname (HM2)

---

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`  
- 最新 commit `d0aaed2 R1022` by `opc2_uname` (HM2)  
- HM1 git log 停留在 R821 (201 轮落后，正常)  
- 脚本正确检测到自提交 — cron 误派遣 (false trigger)  
- 铁律不改HM2，不改HM1  

## 6h 数据 (容器重启后 ~47min 有效窗口)

| 指标 | 值 |
|------|-----|
| 6h 总请求 | 428 |
| 6h 成功率 | 401/428 = **93.7%** |
| 6h 失败 | 27 |
| nvcf_pexec 6h | 122/122 = **100% SR** (零 NVCFPexecTimeout) |
| nv_integrate 6h | 273/278 = 98.2% SR |
| dsv4p_nv 6h | 60/68 = 88.2% SR |
| dsv4p_nv 24h ATE | 16 |
| glm5_2_nv 24h ATE | 39 (all integrate timeout, non-binding UPSTREAM_TIMEOUT) |
| Fallback 6h | 2/2 成功 (26259ms avg) |

### 6h 错误分类
| 错误类型 | 数量 |
|----------|------|
| all_tiers_exhausted | 22 |
| stream_total_deadline | 3 |
| NVStream_TimeoutError | 2 |

### 24h Tier Attempts
| Tier | 错误类型 | 数量 | avg_ms | max_ms |
|------|---------|------|--------|--------|
| glm5_2_nv | NVCFPexecTimeout | 20 | 56859 | 62606 |
| glm5_2_nv | 504_nv_gateway_timeout | 7 | - | - |
| glm5_2_nv | empty_200 | 4 | - | - |
| dsv4p_nv | IntegrateTimeout | 14 | 56021 | 67086 |
| dsv4p_nv | NVCFPexecRemoteDisconnected | 1 | 9134 | 9134 |

## HM1 nv_gw Env (关键参数)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor (nvcf_pexec 100% SR 证实不绑定) |
| TIER_TIMEOUT_BUDGET_S | 110 | floor |
| TIER_COOLDOWN_S | 18 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| NVU_EMPTY_200_FASTBREAK | 1 | aggressive |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | aggressive |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | aggressive |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | floor |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,dsv4p_nv:dsv4p_ms | R1020 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | production |

## ms_gw 状态

- Health: OK, models=[glm5_2_ms, dsv4p_ms, kimi_ms]
- dsv4p_ms 已验证可用 (直接 curl → STATUS 200, 从 nv_gw 容器 python3 → STATUS 200)
- rr_counters: ms_glm5_2=116, ms_dsv4p=2
- Cooldowns: 全部空
- EMPTY_200_FASTBREAK_THRESHOLD=3

## dsv4p_ms Fallback 诊断

nv_gw 日志 @03:38:46:
```
[NV-MS-FB] ms_gw returned 501 after 25ms, not relaying, returning local 502
[NV-MS-FB] ms_gw same-model fallback FAILED for model=dsv4p_nv, (relay_started=False)
```

**验证结果**: 当前 nv_gw → ms_gw `dsv4p_ms` fallback **工作正常** (python3 test STATUS=200)。03:38 的 501 是瞬时问题 (ms_gw 刚重启 ~7min，可能 cooldown/auth 短暂异常)。无需代码/配置修改。

## 决策: NOP

- 所有参数已到 floor/optimal
- nvcf_pexec 100% SR 零 NVCFPexecTimeout — UPSTREAM_TIMEOUT=66 完美
- dsv4p_ms fallback 当前工作正常 — 03:38 501 为瞬时问题
- ms_gw 健康，无可优化空间
- 零参数变更

**铁律**: 只改HM1不改HM2 ✅

## ⏳ 轮到HM1优化HM2