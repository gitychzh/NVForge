# R2179 — hm2_cc2 NOP 巡检轮

## 轮号基线
- 主仓 git (pull 前): `8f1b870 R2178 (hm2_cc2): NOP巡检 — 6h长窗口复核确认glm5_2_nv 98.2%稳态无慢退化, 0改动0restart`
- 上一轮 hm2_cc2: R2178 (NOP 6h 长窗口复核, commit 8f1b870)
- 本轮: **R2179 — hm2_cc2 NOP 巡检轮, 0 改动 0 restart**
- 轮文件: `rounds/R2179_hm2_cc2_nop_patrol.md`

## 数据 (HM2, 30min window, 18:08 时点)
- 97 请求 / 92 OK(200) / 5 错(502) → SR = **94.8%** (92/97, 较 R2177 94.4% 微升, 稳态带)
- by model: glm5_2_nv 72/73 = **98.6%** SR (1错: zombie_empty_completion 1);
  dsv4p_nv 20/24 = 83% (4错全 all_tiers_exhausted, NVCF function 74f02205 全挂非本域已知良性, 同 R2177 模式)
- 5 错全 NVCF 上游无害类: 4 all_tiers_exhausted + 1 zombie_empty_completion
- 无 content_filter / timeout / conn / 429 (nv_gw 入口侧)
- nv_gw tier_attempts 30min: 65 pexec_success + 12 pexec_conn_RemoteDisconnected + 4 pexec_429 + 2 NVCFPexecRemoteDisconnected + 2 pexec_500
  (全 NVCF 上游瞬态, nv_gw 内部重试/tier 切换正常吸收)
- cc4101 30min fallback 计数 = **0** (连续第 3 轮 0 真中断: R2177=R2178=R2179)
- nv_requests.fallback_occurred=true 8 条 → **nv_gw 内部 NV-MS-FB tier 兜底**
  (glm5_2_nv all_keys_exhausted → 甩 glm5_2_ms 热备), **非 cc4101 层 fallback**。
  日志佐证: 多次 [NV-MS-FB-ATTEMPT]+[NV-MS-FB-OK]+[NV-MS-FB-SERVED] 配对, **breaker state 全程 CLOSED**。
- NV-ANTH-BREAKER-FAIL: 日志未见 OPEN 事件 (state 全程 CLOSED)。
  注: 日志出现 1 条 [NV-TOOLCALL-JSON-BAD] frag 含 cc2 自己 Read STATE.md 内容 —— 是上游 SSE 把
  cc2 toolcall 文本透传误判所致, 与 breaker/上游分类无关, 已知良性噪音。
- 75s_timeout / STREAM-STALL-FAIL / UPSTREAM-ERROR-SEEN: 0
- 容器无漂移: nv_gw Up 8h / cc4101 Up 5h / logs_db Up 4d

## 决策: NOP 巡检, 0 改动 0 restart
STATE 三触发改动阈值全不满足:
- SR 94.8% > 85% ✅ 在阈值之上
- cc4101 fallback 0 < 5 ✅ 在阈值之下 (连续第 3 轮 0)
- 无新错误类型 (仍 all_tiers_exhausted + zombie) ✅

glm5_2_nv 98.6% 稳态带内 (R2174-R2178 长期>96%, R2178 已做 6h 复核 98.2% 无慢退化)。
四重佐证 nv_gw 稳: 5错全上游无害类 / 无参数误杀(75s_timeout=0 STALL=0) /
breaker 不真 OPEN(全 CLOSED) / 容器无漂移。改了反而破坏 R2154 稳定带。

## 验证
0 改动 0 restart 无需验证改动。
- curl /health ok: nv_num_keys=5, proxy_role=passthrough, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv]
- docker ps 全栈 Up (nv_gw Up 8h / cc4101 Up 5h / logs_db Up 4d)
- env 关键参数与 R2177 快照逐项一致 (MIN_OUTBOUND=10, KEY_COOLDOWN=60,
  UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, TIER_COOLDOWN=180)

## 备注
- 主仓 R21XX alternating -2s 是 HM1 peer 轮 (only HM1), HM2 不参与, 保持 HM2 稳态。铁律: 只改 HM2 不改 HM1。
- 长窗口 6h 复核已在 R2178 完成 (98.2% 无慢退化), 本轮回归 30min 巡检节奏。
