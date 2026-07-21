# R2176 (hm2_cc2): NOP 巡检轮 — 稳态延续, 0 改动 0 restart

## 上下文
全新 session 接棒 R2175。STATE.md 完整未被并发改, git pull 已是 70b7f77。
本轮纯巡检, 遵守"三阈值全满足才动, 否则冻结"。

## 数据 (HM2, 30min window)
- 78 请求 / 71 OK(200) / 7 错(502) → SR = **91.0%** (71/78, 较 R2175 89.5% 略升, 带内)
- by model: glm5_2_nv 67/69 = **97.1%** SR (2错: zombie_empty_completion 2); dsv4p_nv 4/9=44% (5错全 all_tiers_exhausted, NVCF function 74f02205 全挂非本域已知良性)
- 7 错全 NVCF 上游无害类: 5 all_tiers_exhausted + 2 zombie_empty_completion
- 无 content_filter / timeout / conn / 429 / NV-ANTH-BREAKER-FAIL
- nv_gw tier_attempts 30min: 62 pexec_success + 8 RemoteDisconnected + 6 SSLEOFError + 4 pexec_429 + 4 empty_200 + 1 NVCFRemote + 1 empty_200 (全 NVCF 上游瞬态, nv_gw 内部重试/tier 切换正常吸收)
- cc4101 30min fallback 计数 = **0** (较 R2175 的 4 次更干净, 0 真中断)
- nv_requests.fallback_occurred=true 8 条 (nv_gw 内部 tier 切换 glm5_2_nv→glm5_2_ms, 非 cc4101 层 fallback)
- 75s_timeout = **0** (R2154 动态 header timeout 持续生效, cc4101 无误杀)
- STREAM-STALL-FAIL / UPSTREAM-ERROR-SEEN = 0
- nv_gw BREAKER / big_input / nv_breaker: 30min **0 条触发**
- 容器无漂移: nv_gw Up 8h, cc4101 Up 4h, 全栈 Up

## 决策: NOP 巡检不改代码
三触发改动阈值全不满足:
- SR 91.0% > 85% ✅ 在阈值之上 (较上轮略升)
- cc4101 fallback 0 < 5 ✅ 在阈值之下 (比上轮还干净)
- 无新错误类型 (仍 ATE+zombie) ✅

glm5_2_nv 97.1% 稳态带内 (R2175 96.7% / R2157 98.4%, 同带宽正常波动)。
四重佐证 nv_gw 稳: 7错全上游无害类 / 无参数误杀(75s_timeout=0 STALL=0) /
breaker 不触发(0) / 容器无漂移。改了反而破坏 R2154 稳定带。

## 验证
0 改动 0 restart 无需验证改动。
- curl /health: ok (nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv])
- docker ps: 全栈 Up
- DB 30min 窗口稳态带内 (见上)
- 参数 env 与 R2175 基线逐项一致 (KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=180,
  UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120,
  NVU_BIG_INPUT_FAIL_N=1 等全无漂移)

## 下一轮
继续巡检。盯 75s_timeout 持续归零 / fallback 仍全 NVCF 上游类 /
glm5_2_nv SR 长期 >95% 无慢退化。三阈值全满足才动, 否则冻结。
铁律: 只改 HM2, 不碰 ms_gw(40007 重启窗口热备), 不改 HM1。
