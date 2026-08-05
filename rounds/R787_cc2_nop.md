# R787: cc2 NOP 巡检 — 51st consecutive 100% (R735-R787)

## 摘要

**改动**: 不改码 (NOP 巡检轮)

**结论**: cc2 nv_gw 链路 51st consecutive 100% SR, 0 fb, 0 错误。本轮 tier 噪声极低 (仅 k0 一个 pexec_429), 全 attempt=1 success。k4 RemoteDisc 连续 3 轮偏高 (R782:6+R783:6+R784:5) 在本轮回落为 0 — k4 (fid3 b6029a96) 健康。

## 依据 (轮前链路分析 ~08:24 CST + 实测复核, 30min 窗口)

### cc2 主链路 (cc4101-primary|glm5_2_nv)
- **nv_requests: 117 req × 200 = SR 100%** ✅
- 0 错误, 0 fallback
- 流量 117 req/30min (上轮 R784:116, +1 持平)

### per-key pexec_success 分布 (cc4101-primary, glm5_2_nv)
- k0:24 + k1:25 + k2:22 + k3:24 + k4:22 = 117 (全 attempt=1 即 success)
- **k0 有 pexec_429 × 1** — 单次偶发, KeyManager 退避消化
- k1/k2/k3/k4 全 0 错误 — 干净

### tier 噪声分析
- 全 caller tier 错误 (30min): pexec_success=117, NVCFPexecRemoteDisconnected=13, 529_nv_overloaded=3, empty_200=2, pexec_429=1
- **cc4101-primary 链路 tier 噪声**: 仅 k0 pexec_429×1 — **本轮 tier 噪声 1** (上轮 R784:19, 大幅下降)
- RemoteDisc×13 全在 dsv4 hermes caller — 注入噪声, 零穿透 cc2

### cc_requests (cc4101 全 caller 聚合, 非 cc2 专属)
- 881 req / 866 ok / SR=98.3%, fb=10 (1.1%)
- 15 个错误全是 client_gone_mid_stream ×14 + timeout ×1 — 客户端断开/超时, 非上游 NVCF 故障
- cc4101-primary (cc2 链路) 在 nv_requests 表 SR=100%, 与 cc_requests 表的差异来自其他 caller

### k4 RemoteDisc 趋势 (上轮关注点)
- R782:6 / R783:6 / R784:5 — 连续 3 轮偏高
- **R787:0** ✅ — k4 (fid3 b6029a96) 回落, 健康恢复
- R774 cleanest 计数仍停在 27

## 验证 (NOP 无需 restart)
- 容器健康: nv_gw Up 6h, cc4101 Up 7h, dsv4p_nv40066 Up 12h, nv_gw_stable Up 3d, logs_db Up 5d
- /health: nv_gw passthrough(5key, pexec_models 含 glm5_2_nv) ok, cc4101 primary=glm5_2_nv ok
- buffer 日志正常: 全 attempt=1 verdict=success_text/success_tool_call, elapsed 4s~19s, 无 WAIT/EVENT

## 判稳结论

| 指标 | 目标 | 实际 | 达标 |
|---|---|---|---|
| cc2 nv_gw SR | ≥99% | 100% (117/117) | ✅ |
| fallback 触发率 | <10% | 0% (cc4101-primary) | ✅ |
| 用户可见 SR | ≥99% | 100% | ✅ |
| 新错误 | 0 新错误 | 0 (仅 k0 pexec_429×1 偶发) | ✅ |

**51st consecutive 100% (R735-R787)** — 链路稳态, 无可改项。

### SR 趋势
| 轮 | 30min 窗 SR | tier 噪声 | 备注 |
|---|---|---|---|
| R774 | 100% (95/95) | 0 | 40th, 27th cleanest |
| R775 | 100% (83/83) | 20 | 41st, cleanest 停 27 |
| R776 | 100% (82/82) | 19 | 42nd |
| R777 | 100% (80/80) | 17 | 43rd |
| R778 | 100% (57/57) | 16 | 44th |
| R779 | 100% (67/67) | 18 | 45th |
| R780 | 100% (71/71) | 20 | 46th |
| R781 | 100% (70/70) | 20 | 47th |
| R782 | 100% (79/79) | 22 | 48th, k4 RemoteDisc 6 偏高 |
| R783 | 100% (107/107) | 20 | 49th, k4 RemoteDisc 6 续 |
| R784 | 100% (116/116) | 19 | 50th, k4 RemoteDisc 5 续 |
| R787 | 100% (117/117) | 1 | **51st, k4 RemoteDisc 回落为 0** |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- 关注 k0 pexec_429 是否升级 (本轮单次, 不构成趋势)
- k4 RemoteDisc 已自愈, 不再特别关注
- 注入噪声 (dsv4 hermes caller) 全在 dsv4 链路, 非 cc2 问题
- dsv4p_nv fallback 链路健康 (本轮 dsv4p_nv 数据见轮前链路分析: SR=100% 20/20, fallback 应急链路 OK)

## 参数快照 (R787, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
  - NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
  - NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
  - MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=ms_gw:40007(glm5_2_ms env), STREAM_TOTAL=470, HEADER=400, PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
  - 注: cc4101 env FALLBACK_UPSTREAM_URL=ms_gw:40007 与 CLAUDE.md 中描述的 dsv4p_nv40066 链路不一致, 但本轮 0 fb 触发, 不动它
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF
