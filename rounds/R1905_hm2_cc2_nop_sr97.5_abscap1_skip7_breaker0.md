# R1905 (HM2 cc2) — NOP 巡检 R56

> 模式: nv 直连 (cc4101→nv_gw)。bug8 降级兜底 in-vivo 后第 52 轮巡检 (R1839 落地 → R1841-R1905)。
> 本轮 0 改动 0 restart。链路稳态持续。

## 数据 (30min 窗, 本 session ~15:55 CST / 07:55 UTC 拉取)

### SR
- 200:39 / 502:1 → **SR = 39/40 = 97.5%**
- 近轮 SR 序列 (R1875→R1905): 96.7 / 93.65 / 94.2 / 88.9 / 89.7 / 87.6 / 90.9 / 93.0 / 93.9 / 94.9 / 96.36 (R1902) / 100 (R1904 peer) / 97.5 (R1905)
- **当前 97.5 区间上沿, 抖动区间常态近 52 轮在 80.9-99, 非趋势性退化**

### 502 分类 (1 条)
- **stream_absolute_cap 1** = abs_cap 同源 (NVCF 首字节拖到 wall-clock 截断)
- **无 zombie** (R1902 zombie 2 → R1905 0): abs_cap ↔ zombie 在 NVCF empty200 上游侧来回切确认 (同源首字节慢/空)
- 无 ttfb / 无 gap / 无 deadline / 无 cfilter / 无 SSLEOF / 无 500_nv_error

### tier pexec (30min)
- pexec_success 25 (干净基底, 无 ATE)
- IntegrateTimeout 2
- pexec_empty_200 2 (NVCF 偶发)
- **pexec_SSLEOFError 30min tier=1 单点续** (R1899 0 → R1902 1 → R1905 1, 出口 IP 段 134.195.101.0/24 同源, 非批量化非 nv_gw config 可修)
- pexec_timeout 1
- 无 500_nv_error (absorbed); 无 conn_RemoteDisconnected; 无 ttfb

### fallback (8 条全 FALLBACK-OK, 0 双路全炸, 0 真中断)
- 15:28 req=8d3b4459 → NV-MS-FB all_keys_exhausted 兜底 (breaker CLOSED) → ms 7167ms
- 7 条 75s SKIP-CIRCUIT (cc4101 preempt, NOT counted) 全被 ms_gw 兜住:
  - 15:31 req=66b9135d → 75s SKIP → ms 8097ms
  - 15:35 req=cf51853c → 75s SKIP → ms 10083ms
  - 15:42 req=870aaefa → 75s SKIP → ms 15443ms
  - 15:45 req=63305313 → 75s SKIP → ms 2881ms
  - 15:49 req=b6055ee5 → 75s SKIP → ms 2873ms
  - 15:54 req=362ba5a5 → 75s SKIP → ms 7548ms
  - (1 条 15:28 req=8d3b4459 已计入上一行 NV-MS-FB)
- **非跳过类真请求失败 0 条 < 4 阈值**
- **0 双路全炸, 0 真中断** (用户诉求 "可以报错但不能让 cc2 中断" 仍达成)
- 75s SKIP 抬头趋势持平 (R1895≈0→R1896=6→R1898=8→R1900=5→R1902=7→R1904=7→R1905=7), 全 NOT counted 0 真中断 — cc4101 bug3 preempt 行为持续, nv_gw 侧无 config 可解 (75s 是 cc4101 chain budget 前置切, 非 nv_gw UPSTREAM/TIER_BUDGET)

### breaker (30min)
- **OPEN 事件 0** (全 CLOSED, 连续 10+ 轮无 OPEN 复现)
  - 6 次 NV-MS-FB-SERVED (ms 兜底 all_keys_exhausted, state=CLOSED) + bug7 cap_origin reset (R1818 路径正常工作, total_elapsed_pre_reset=242-268s = NVCF 首字节拖到截断甩 ms)
  - **1 次 NV-ANTH-BREAKER-FAIL** (15:50, state=('CLOSED', 2, 0)) = breaker 记录 1 次失败但未 OPEN, abs_cap 被 nv_breaker 吸收, 设计内吸收态
  - 0 次 breaker OPEN
- R1889 12:59 单次 OPEN (HALF_OPEN probe 13:03 自回 CLOSED) 连续 10+ 轮 (R1890-R1905) 无复现 = 单次设计内动作非源码 bug

### bug8
- NV-TOOLCALL-JSON-DOWNGRADE 60min log = 0 (根除停巡, 连续 52 轮 0 触发)

### env + 字节码
- env 无漂移 (KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 / TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 / MIN_OUTBOUND=0, 全与 R1850-R1902 一致)
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
- StartedAt 仍 2026-07-18T21:26:29Z (R1836 restart, R1839 至 R1905 未再 restart) → 跑改后字节码
- /health ok (nv_num_keys=5, nvcf_pexec_models 含 glm5_2_nv)
- docker ps 全 Up (nv_gw Up 10h / cc4101 Up 24h / ms_gw Up 2d / logs_db Up 2d)

## 决策: NOP (无据不改)

介入触发四条全不满足:
1. SR 97.5% 仍在 80.9-99 抖动区间常态, 非持续跌破 80 退化
2. 非跳过类真请求失败 0 条 < 4 次/30min 介入线 (8 条 fallback 中 7 条全 75s SKIP-CIRCUIT NOT counted, 1 条 NV-MS-FB all_keys_exhausted 兜底)
3. breaker OPEN 30min = 0 (全 CLOSED), 连续 10+ 轮无复现, 未达 >=3 次/30min 介入线; 1 次 NV-ANTH-BREAKER-FAIL 被 nv_breaker 吸收未 OPEN (设计内吸收态)
4. 无新可配置错误分类 (502 全 abs_cap NVCF 上游侧 wall-clock 已知; SSLEOF 1 单点续出口 IP 段同源; 500_nv_error absorbed; ttfb 0; gap/deadline/cfilter 无)

→ 硬改违反铁律 1 (改前必有数据 + 无据不改)

R1881-R1892 已穷尽 nv_gw 调参旋钮并反证:
- TIER_BUDGET 收紧到 90 误杀慢成功 SR 暴跌
- KEY/TIER_COOLDOWN 管不到 TLS 握手 RST
- UPSTREAM 改不动 NVCF 侧 abs_cap/zombie
- abs_cap wall-clock 非上游 TIER_BUDGET 可收紧
75s SKIP 是 cc4101 bug3 preempt, 非 nv_gw 旋钮可解

## 给监督者/运维 (沿用 R1881-R1904)
1. **换出口 IP 段**: 让 HM2 5 个 mihomo 端口 (7894-7899) 背后走非 134.195.101.0/24, 解 SSLEOF / 500_nv_error / abs_cap 同源 (NVCF 端对该 /24 段 TLS RST / 500 限流 / 首字节极慢到 abs_cap 截断)
2. **联系 NVCF 运维**: 查该 /24 段 TLS RST / 500 限流 / 首字节为何拖到 abs_cap 截断策略, 以及 all_keys_exhausted 短窗集中 (全 5 key 同时 ratelimit/耗尽) 是否 NVCF 端配额调度问题
3. **短期 cycle/breaker/fallback 三层吸收已在位**, 兜底 SR 80.9-99 近 52 轮可接受, 0 真中断. breaker OPEN 自恢复机制工作正常, abs_cap/zombie 走 nv_breaker 吸收不 OPEN

## 文案备注
本轮 R1905 单文件 (R1905 本身), 无 peer 误收。
pull 时见 peer 已推到 R1904 (HM2 cc2 `44a9cf4` SR100% 巡检 R55 + HM2→HM1 `d801ed9` UPSTREAM 32→30 HM1 侧), 故本轮跳到 R1905。
cc2 铁律: 只改 HM2, 不碰 ms_gw, 改 .py 必须 restart 非 up-d。

## 下轮 (R1906) 重点
- abs_cap ↔ zombie 是否续在 NVCF empty200 同源来回切 (本轮 abs_cap 1 / zombie 0; 若 zombie 批量化 → 查上游)
- breaker OPEN 是否复现 (连续 10+ 轮 0; 若 >=3 次/30min 且不自回 CLOSED → 真恶化)
- 75s SKIP-CIRCUIT 抬头是否续 (持续抬头但全 NOT counted 0 真中断, 关注是否某窗突破到非跳过类真 nv_gw 失败 >=4 次/30min 才介入)
- SR 是否续在 80.9-99 抖动 (当前 97.5 上沿近 52 轮常态)
- SSLEOF / 500_nv_error / ttfb 是否批量化复发 (当前 SSLEOF 1 单点续, 余停闭合)

介入触发条件不变: SR 持续跌破 80 / 非跳过类 fallback >=4 次/30min / breaker OPEN >=3 次/30min 不自回 / 新可配置错误分类出现。任一满足才动手, 否则继续 NOP 巡检。
