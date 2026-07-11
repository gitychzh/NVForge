# HM2 Optimize HM1 — Round R1171

## 触发分析
- **cron 脚本输出**: `"这是我提交的, 不触发"` — 自提交误触发
- **最新 commit 作者**: opc2_uname (HM2), b1931e1
- **HM1 本地 git log**: 停留在 R821 (fbf0e43), 落后 350 轮
- **确认**: 误触发 (false trigger, 39th chain of R1133)
- **Symlink**: 已指向 R1170 (pre-run script 已写入) → double-dispatch

## 数据收集 (改前必有数据)

### 6h 窗口 (2026-07-11 04:00–12:00 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 35 |
| 成功 | 13 (37.1%) |
| 失败 | 22 (100% zombie_empty_completion) |
| 模型 | 100% glm5_2_nv integrate |
| dsv4p_nv | 0 traffic |
| kimi_nv | 0 traffic |
| minimax_m3_nv | 0 traffic |
| fallback_occurred | 0 |
| ms_gw fallback | 0 (no NV-MS-FB in logs) |
| compose md5 | 7975939c245761e451a8813852dcb9bf (48h+ unchanged) |

### 每小时 SR
| 小时 (UTC) | total | ok | fail | SR% |
|-----------|-------|-----|------|------|
| 22:00 | 5 | 1 | 4 | 20.0 |
| 23:00 | 9 | 4 | 5 | 44.4 |
| 00:00 | 7 | 1 | 6 | 14.3 |
| 01:00 | 4 | 2 | 2 | 50.0 |
| 02:00 | 4 | 2 | 2 | 50.0 |
| 03:00 | 4 | 2 | 2 | 50.0 |
| 04:00 | 2 | 1 | 1 | 50.0 |

### 错误详情
- 22× zombie_empty_completion (all glm5_2_nv integrate)
- NVCF content-filter: finish_reason=stop, content_chars=12, input 164K-169K
- Gateway detection + error-chunk correct: [NV-ZOMBIE-EMPTY] + [NV-ZOMBIE-ERROR-CHUNK]
- 3× 429_integrate_rate_limit (nv_tier_attempts, 0 elapsed_ms)
- 0 ATE, 0 NVCFPexecTimeout, 0 all_tiers_exhausted

### 容器状态
- nv_gw: Up 9h (restart 2026-07-10T19:03:27Z)
- tier_chain: ['glm5_2_nv'] (no fallback, 3model) — expected (FALLBACK_GRAPH={})
- ms_gw: 处理直接请求 (MS-OK-STREAM + MS-STREAM-DONE), 但 nv_gw 无 NV-MS-FB 流量

### 参数状态
所有参数 floor/optimal, 无需调整:
- TIER_TIMEOUT_BUDGET_S=198, UPSTREAM_TIMEOUT=66, KEY_COOLDOWN_S=25
- TIER_COOLDOWN_S=15, MIN_OUTBOUND_INTERVAL_S=0
- FASTBREAK=1 (pexec), FASTBREAK=1 (integrate), EMPTY_200_FASTBREAK=2
- NVU_PEER_FALLBACK_TIMEOUT=66, NVU_MS_GW_FALLBACK_TIMEOUT=180
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv

## 判定: NOP

**原因**: 所有失败均为 zombie_empty_completion — NVCF 上游 content-filter 行为 (stop+12chars, 164K-169K input)。Gateway 正确检测并发送 error-chunk 触发 openclaw fallback。这是代码级 zombie 检测功能 (R1107), 非 config 可修复。所有参数已在 floor/optimal。Compose md5 48h+ 未变。0 容器重启。0 配置变更。

**ms_gw**: 0 流量通过 nv_gw DB (ms_gw 直接处理请求, 不经过 nv_gw fallback)。ms_gw 日志显示 MS-OK-STREAM + MS-STREAM-DONE, 正常。

无代码修改

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2

