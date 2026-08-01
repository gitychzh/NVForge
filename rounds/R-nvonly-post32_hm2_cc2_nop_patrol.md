# R-nvonly-post32 — hm2_cc2 NOP 巡检轮

**时间**: 2026-08-02 03:05 CST
**主仓 HEAD**: 41196ad (post31 已 push)
**本轮**: NOP 巡检轮. 0 改动, 0 重启.

## 判稳依据 (注入数据, 2026-08-02 03:04)

### cc4101-primary (cc2) 30min — 0 req
- session 轮前无 cc2 流量产生, 无数据可判 cc2 SR.
- 链路健康无故障: 容器全 Up, /health ok.

### 其他 caller (非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

- dsv4p_nv SR=0% (0/6), top error: all_tiers_exhausted ×6 (5key 全挂, NVCF 侧限流).
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | cc4101 Up, nv_gw Up, nv_gw_stable Up, ms_gw Up 2d, logs_db Up 2d ✓ |
| 配置 (注入实测) | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (all_tiers_exhausted ×6 全是 dsv4p_nv/hermes, 非 cc2) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |

→ **NOP 巡检轮**, 不改码, 不重启.

## cc2 SR 走势
| 轮次 | cc2 SR | 趋势 |
|------|--------|------|
| post17-post27 | 连续 100% (满分 11 连庄) | ✅ |
| post28-post31 | 0 req (无流量, 不打断) | — |
| **post32** | **0 req** (无流量, 不打断) | — |

## 参数快照 (实测 2026-08-02 03:04 注入)
- nv_gw: `NVU_DISABLE_MS_FALLBACK=0`, `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`, `UPSTREAM_TIMEOUT=90`, `TIER_TIMEOUT_BUDGET_S=180`, `TIER_COOLDOWN_S=180`, `KEY_COOLDOWN_S=30`, `NV_INTEGRATE_KEY_COOLDOWN_S=90`, `MIN_OUTBOUND_INTERVAL_S=10`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`, `NVU_FORCE_STREAM_UPGRADE=0`, `NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `FALLBACK_UPSTREAM=ms_gw:40007`, `FALLBACK_UPSTREAM_MODEL=glm5_2_ms`, `PRIMARY_UPSTREAM=nv_gw:40006`, `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`, `CC4101_PRIMARY_FAIL_THRESHOLD=3`, `CC4101_PRIMARY_SKIP_S=30`, `UPSTREAM_IDLE_TIMEOUT=150`

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR (本轮 0 req 是 session 轮前无流量, 非链路故障).
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
