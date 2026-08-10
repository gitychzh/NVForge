# R1250: NOP — 30min SR 94.9%，NVCF pexec 上游 RemoteDisconnect 事件（非本容器可调杠杆）

## 修改
- **无参数修改**（NOP）。env 与 R1249 完全一致:
  - UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180
  - KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90
  - NVU_KEYMGR_429_BASE/MAX=120/120, CONN_*=30/60/3/120
  - NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3

## 依据 (30min 窗口 / 采集脚本)
- **SR = 94.9% (56/59)**, 略低于 NOP 阈值 95%，主因 3 个 all_tiers_exhausted (avg 145s ≈ tier budget 180s，请求烧满 budget 后整体失败)。
- **upstream 全 pexec** (57/56, SR=98.2%)，无 integrate 激活 — 架构与 R1245/R1249 一致。
- **net 429 = 0**; key_cycle_429s (k0=47/k1=7/k2=4/k3=1) 为 key manager 内部保护，已吸收。
- **5 key 负载均衡正常** (k0=10/k1=15/k2=14/k3=9/k4=8)，avg 21.7-42.3s，p95 36.6-123s，无单 key 劣化。

## 关键新信号: NVCFPexecRemoteDisconnected (上游劣化, 非本容器杠杆)
深入 2h tier_attempts 复核:
- **NVCFPexecRemoteDisconnected = 62** + NVCFPexecTimeout = 19 (R1245-R1249 健康窗无此错误类，新出现)。
- **均匀分布全部 5 key** (k0=7/k1=12/k2=10/k3=12/k4=21), avg ~34-42s — 非 key/SOCKS5 代理问题，是 **NVCF pexec 上游服务端远程断开**。
- **持续 2h 无 429 突发簇** (逐分钟散布 00:00-00:49, 每分钟 0-4 个)，非瞬时峰值过载，为持续上游抖动。
- 最近 10min: 7 次 tier 尝试全为错误行 (connected=0) — 上游抖动此刻仍在持续，但被 buffer/key-manager 重试吸收，请求级 SR 仍 ~95%。

## 判定 (为什么 NOP)
1. SR 94.9% 略低于 95% 阈值，但**未达 <85% 行动线**；3 错误均为烧满 budget 的 ATE，非单 key 集中。
2. 错误源为 **NVCF pexec 服务端 RemoteDisconnect**，均匀跨 5 key、跨 2h 持续 — 属 **NVCF 基础设施/上游负载**问题，非 dsvf0731_nv40666 本地参数可调杠杆。改 UPSTREAM_TIMEOUT/budget 无法阻止 NVCF 远程断开，只会伪装修复。
3. 24h all_tiers_exhausted = 292，与 R1249(291) 基本持平 — 不再滚动下降，叠加新 RemoteDisconnect 事件，确认**上游 NVCF 侧本期有逊化**，但非本容器能治理。
4. key manager + buffer 重试已成功把请求级 SR 兜在 ~95%，内部韧性机制工作正常。

## 验证
- [x] `docker exec dsvf0731_nv40666 env` 参数未变 (UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN=30, TIER_COOLDOWN=90)
- [x] /health = ok (dsvf0731_nv40666, 5 keys, port 40666, nv_default glm5_2_nv)

## 下一步建议
- **上报基础设施层**: `NVCFPexecRemoteDisconnected=62/2h` 跨 5 key 持续 = NVCF pexec 上游负载/可用性事件，建议 cc2/infra 层观察 NVCF 侧（而非在 40666 调参伪修）。
- 本容器继续 NOP: 若 30min SR 持续 <85% 或 ATE/RemoteDisconnect 进一步放大，再由 infra 层决定是否临时改路由/降载。
- 持续关注 24h ATE: 若在 RemoteDisconnect 持续下 24h ATE 跳跃性增长 (>200/日新累积)，确认 NVCF 侧正式劣化，本容器只能兜底不改 budget。
- 若 RemoteDisconnect 消退且 SR 重回 >95%，恢复纯 NOP 稳态观察。