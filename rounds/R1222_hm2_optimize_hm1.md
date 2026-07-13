# HM2 Optimize HM1 — Round R1222

## 1. 触发分析
- **cron 脚本输出**: `"这是我提交的, 不触发"`
- **最新 commit author**: `opc2_uname` (HM2, R1221 6f534b6)
- **脚本正确检测**: 自提交, 标记 "不触发"
- **cron 仍被派遣**: 误触发 (double-dispatch, R1221已存在且symlink正确)
- **HM1 SSH**: 连接超时 — Tailscale WG data-plane broken (tx 248508 rx 0, 持续断裂)
- **HM2 git log**: R1221 (opc2_uname), R1220 (opc2_uname), R1219 (opc2_uname)
- **HM1 git log**: 无法验证（SSH不可达）

## 2. 数据 (改前必有数据)
**来源**: R1133-R1221 chain估计 (SSH不可达, 无法独立验证DB/logs)

| 指标 | 值 |
|------|-----|
| 6h 请求 | ~32req |
| 6h 成功 | ~20OK (62.5%) |
| 6h 失败 | ~12 zombie (37.5%) |
| zombie类型 | zombie_empty_completion (glm5_2_nv integrate) |
| zombie原因 | NVCF content-filter stop+12-36chars, input_chars ~157K avg |
| gateway检测 | 正确 — error-chunk返回, 3-15s完成 (vs 旧code 96s hang) |
| dsv4p_nv | 0 traffic (16h+) |
| kimi_nv | 0 traffic |
| ms_gw | 0 traffic |
| tier_attempts | 0 |
| fallback | 0 |

## 3. 参数状态
| 参数 | 值 | 状态 |
|------|-----|------|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor/optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor/optimal |
| NVU_EMPTY_200_FASTBREAK | 1 | code bug → FASTBREAK=2无效, floor |
| TIER_TIMEOUT_BUDGET_S | 110 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal (R1116) |
| TIER_COOLDOWN_S | 15 | optimal (R1103) |
| UPSTREAM_TIMEOUT | 66 | optimal |
| KEY_COOLDOWN_S | 120 | optimal |
| MIN_OUTBOUND_INTERVAL_S | 5 | optimal |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | optimal (R923) |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | optimal (R922) |
| compose md5 | 7975939c245761e451a8813852dcb9bf | unchanged 48h+ (R1133→) |

## 4. 决策: NOP
- **所有参数 floor/optimal**: 无法进一步优化
- **zombie_empty_completion**: code-level, NVCF content-filter不可config-fixable
- **gateway detection**: 正确运作 (error-chunk返回, 3-15s vs 旧96s hang)
- **SSH不可达**: 无法独立验证live数据, 使用chain估计
- **Tailscale WG data-plane broken**: tx 248508 rx 0, HM1离线1d+
- **Zero param**: 无参数可改, 无容器重启, 无compose修改
- **铁律: 只改HM1不改HM2** — 遵守

## 5. 回合链
R1133→R1222: 90th consecutive false-trigger NOP chain. R1133 trigger at 2026-07-13 22:03 UTC — single-event zombie-only chain-dispatch. R1133-R1222 all NOP with identical zombie-only data, 0 config changes, 0 container restarts. HM1 git still at R821 (82+ rounds behind since R1133), last HM1-authored commit 7625e14 (R818, 2026-07-08).

## ⏳ 轮到HM1优化HM2
