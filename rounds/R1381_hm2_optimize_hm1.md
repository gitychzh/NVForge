# R1381: HM2→HM1 — NOP (false trigger, double-dispatch, 零可修故障, 540th chain of R1133)

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author: opc2_uname (HM2)
- 预运行脚本已提交 R1380 NOP, symlink 正确指向 R1380
- cron 仍被派遣 → double-dispatch (R884+ pattern)
- HM1 无新提交, 此轮为误触发

## 数据收集 (改前必有数据)
- 容器状态: nv_gw Up 2h, logs_db Up 11h, ms_gw Up 11h (all healthy)
- 6h nv_requests: 30req/22OK/8fail = 73.3% SR
- 8 失败全部 zombie_empty_completion (glm5_2_nv integrate, avg 10,059ms)
  - code-level zombie detection — not config-fixable
  - 典型: finish_reason=stop, content_chars=12, input_chars ~200K
- 0 ATE 0 empty_200 0 timeout 0 tier_attempts 0 fallback
- 0 dsv4p_nv traffic in 6h — cannot validate R1370/R1374 budget fixes
- ms_gw: 0 traffic — no secondary optimization opportunity
- Compose md5: f493494e — unchanged since container restart
- Key params all floor/optimal:
  - UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205, TIER_COOLDOWN_S=15
  - NVU_TIER_BUDGET_DSV4P_NV=106, NVU_TIER_BUDGET_GLM5_2_NV=96
  - NVU_EMPTY_200_FASTBREAK=2, NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
  - NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_PEER_FB_SKIP_MODELS=<empty>
  - KEY_COOLDOWN_S=25, NV_INTEGRATE_KEY_COOLDOWN_S=0

## 评判
- 零可修故障: zombie_empty_completion 为 code-level zombie detection → 快速 abort (3-15s vs old 96s hang)
- 无 dsv4p_nv 流量 → R1370/R1374 budget fix 待 HM1 agent 产生流量后验证
- 无参数调整空间 — 所有参数已达 floor/optimal
- 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2
