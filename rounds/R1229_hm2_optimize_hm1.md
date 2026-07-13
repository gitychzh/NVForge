# HM2 Optimize HM1 — Round R1229

## 触发分析

- **cron 脚本输出**: HM1 commit `0482410` "R1228: HM2→HM1 — NOP ... 这是我提交的, 不触发" — 自提交声明不触发
- **最新 commit**: 0482410 (R1228, author=opc2_uname) — HM2 前轮 NOP
- **触发类型**: FALSE TRIGGER — 97th chain of R1133, DOUBLE-DISPATCH (HM1 明确声明不触发, cron 检测仍触发因 NR 脚本预运行)
- **HM1 SSH**: 不可达 (Connection timed out, WG data-plane broken, rx 0 since R1209, 持续 1d+)
- **HM1 Tailscale**: Online=False, relay=sfo, tx 60372 rx 0, LastWrite=2026-07-13T15:54:14+08

## 数据收集

### SSH 连接状态
- SSH to HM1 (100.109.153.83:222): **Connection timed out**
- Tailscale ping: timed out, no reply
- 无法独立验证实时数据 — 使用链估计 (R1133→R1228)

### 网络诊断

| 指标 | 值 | 诊断 |
|------|-----|------|
| HM1 Online | False | 离线 |
| HM1 TxBytes | 60372 (since last seen 1d ago) | HM1 有少量出站 |
| HM1 RxBytes | 0 | **WG data-plane broken** — HM1 完全无法接收数据 |
| HM1 Relay | sfo | DERP relay 可用但数据面断 |
| HM2 Relay | tok | HM2 DERP 正常 |
| HM2→HM1 SSH | Connection timed out | 全路径不可达 |
| HM2→HM1 TS ping | timed out, no reply | ICMP over TS 也不通 |

### 估计数据 (from R1133→R1228 chain, 96 rounds)
- **6h 窗口**: ~32req/20OK(62.5%)/12zombie
- **失败模式**: zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12-36chars, input_chars ~157K avg)
- **Gateway 行为**: detection+error-chunk 正确, 502 在 3-15s (vs 旧 96s hang)
- **dsv4p_nv**: 0 traffic (16h+)
- **kimi_nv**: 0 traffic
- **ms_gw**: 0 traffic
- **tier_attempts**: 0
- **fallback**: 0 triggers
- **compose md5**: 7975939c245761e451a8813852dcb9bf (不变 since R1133 22:03 UTC, >48h)

### 当前配置快照 (最后已知, R1133→R1228)
- UPSTREAM_TIMEOUT=28
- TIER_TIMEOUT_BUDGET_S=90
- MIN_OUTBOUND_INTERVAL_S=0.4
- CONNECT_RESERVE=2
- KEY_COOLDOWN_S=25
- TIER_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=3
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NV_INTEGRATE_KEY_COOLDOWN_S=105
- PEER_FALLBACK_TIMEOUT=25
- SSLEOF_RETRY_DELAY_S=1.0
- FALLBACK_HEALTH_THRESHOLD=0.05
- FORCE_STREAM_UPGRADE_TIMEOUT=40
- FORCE_STREAM_UPGRADE=0
- NV_INTEGRATE_ENABLED=1
- NV_INTEGRATE_MODELS=dsv4p_nv,kimi_nv,glm5_1_nv,glm5_2_nv

## 决策

### NOP — 无优化空间

1. **zombie_empty_completion**: NVCF content-filter 行为 — 代码级 zombie 检测已正确返回 502。非 config 可修复。
2. **所有参数已在地板/最优**: compose md5 不变 (>48h)
3. **0 tier_attempts**: 无 tier 级错误需要调整
4. **0 fallback**: peer-fb 和 ms_gw 未触发
5. **HM1 SSH 不可达**: WG data-plane 损坏 (rx 0, Online=False) — 不能 SSH → 不能改 compose → 不能重启容器
6. **HM1 自提交声明 "不触发"**: 作者 opc2_uname 的前轮 NOP, 非实质参数变更
7. **铁律**: 只改 HM1 不改 HM2

### 参数变更: 0
### 容器重启: 0

## 连续 NOP 链 (R1133→R1229)

| 链 | 轮次 | 持续时长 | 模式 |
|----|------|---------|------|
| R1133→R1229 | 97 rounds | 2026-07-12 22:03 UTC → 2026-07-13 | zombie-only, NOP, SSH unreachable since R1209 |

## 恢复后补检清单
1. SSH 恢复后立即: `docker ps`, `docker logs nv_gw --tail 100`
2. DB 独立验证: 6h 窗口 nv_requests 统计, per-model SR, tier_attempts
3. compose 漂移检测: md5 对比, env 对比
4. 确认 zombie 模式是否持续 (NVCF content-filter 是否恢复)
5. 确认 dsv4p_nv/kimi_nv 流量是否恢复

## ⏳ 轮到HM1优化HM2