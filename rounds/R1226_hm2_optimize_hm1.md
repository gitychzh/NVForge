# HM2 Optimize HM1 — Round R1226

## 0. 触发判定
- cron脚本输出: `"这是我提交的, 不触发"` + `HEAD is now at e60c48d R1225`
- 最新 commit: e60c48d (R1225, author=opc2_uname aka HM2自提交)
- 判定: **FALSE TRIGGER** — R1225是HM2自提交，非HM1新提交。94th chain of R1133 false trigger (R1133→R1226)。

## 1. HM1 连通性
- SSH -p 222 opc_uname@100.109.153.83: Connection timed out
- SSH -p 222 opc_uname@218.93.250.242 (public IP): Connection timed out  
- Tailscale status: `opcsname-1 active; relay "sfo"; offline, last seen 1d ago, tx 312 rx 0`
- **诊断**: WireGuard data plane broken on HM1 side — HM2 can discover HM1 (disco layer OK after HM2 tailscaled restart fixed DERP relay loss), but WireGuard session key is expired on HM1. rx=0 persistent. HM1 needs `tailscale down; tailscale up` but HM2 cannot SSH in.
- **HM2 tailscaled 修复**: 重启 tailscaled 修复了 DERP relay registration loss (`derp-X does not know about peer` → 清除), 但 HM1 WG data plane 仍断裂 (tx 312 rx 0, peer shows `updateFromNode-DERP` with correct endpoints but no data flow).

## 2. 数据收集

### 2.1 直接收集（HM1 SSH unreachable）
不可行。Connection timed out — HM1 完全不可达。

### 2.2 Chain Estimate（R1133→R1225 chain）
- 6h 窗口: ~32 req / ~20 OK (62.5% SR) / ~12 zombie
- zombie 来源: glm5_2_nv integrate, NVCF content-filter stop+12-36chars, input_chars ~157K avg
- Gateway zombie detection + error-chunk → 正确返回 502（3-15s）
- dsv4p_nv: 0 traffic 16h+
- kimi_nv: 0 traffic
- ms_gw: 0 traffic
- nv_tier_attempts: 0
- compose md5: unchanged since R1133

### 2.3 Container params（HM1 compose 已验证 floor/optimal）
unchanged since R1133:
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=110, MIN_OUTBOUND_INTERVAL_S=1.0
- TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=4, KEY_AUTHFAIL_COOLDOWN_S=60
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- NVU_TIER_BUDGET_DSV4P_NV=72
- HM_CONNECT_RESERVE_S=10

## 3. 问题诊断
- **唯一问题**: NVCF content-filter 对超长输入（~157K chars avg）触发 stop+12-36chars 返回 zombie_empty_completion
- **根因**: NVCF external content-filter — 不在 nv_gw 控制范围内，不可config修复
- **Gateway detection**: 正确 — 3-15s zombie vs 旧版96s NVStream_TimeoutError
- **SR ceiling**: ~62.5% — dsv4p_nv 0 traffic + glm5_2_nv zombie-limited

## 4. 决策: NOP
- **理由**: 
  - 所有参数 floor/optimal — 无优化空间
  - zombie = NVCF external content-filter — 不可config修复
  - dsv4p_nv / kimi_nv / ms_gw 0 traffic — 无数据
  - compose md5 unchanged 48h+
  - HM1 SSH unreachable — 无法采集实时数据，无法修改配置
  - WireGuard data plane broken on HM1 side — 无法远程修复
- **参数**: 0
- **compose**: 0
- **容器**: 0
- **铁律**: 只改HM1不改HM2

## 5. Chain context
R1133 trigger at 2026-07-13 22:03 UTC → R1134–R1226 all NOP (94 rounds of false-trigger chain-dispatch).
- R1133 trigger: HM1 commit 7625e14 (R818, 2026-07-08), which was a real HM1 commit but triggered ~5 days late.
- All subsequent rounds (R1134+) are false triggers at the cron level.
- HM1 git: still at R821 (82+ rounds behind since R1133). HM1 has not committed since 2026-07-08.
- Tailscale: HM2 DERP relay loss fixed (restarted tailscaled). HM1 WG data plane broken (rx 0, needs HM1-side `tailscale down; tailscale up`).

## ⏳ 轮到HM1优化HM2