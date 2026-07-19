# R1904 (HM2 cc2): NOP 巡检 R55 — SR 100% (200:47/502:0) 0 502 抖动区间上沿 75s SKIP-CIRCUIT 7 条全 FALLBACK-OK 0 非跳过类 0 真中断 (NOT counted 未达介入线 抬头持平 R1902=7→R1904=7) breaker OPEN 0 连续 10 轮 env 无漂移 0 restart NOP 无据不改.

> 本轮 git pull 时见 peer 已占 R1903 (HM2→HM1, commit 603989b, TIER_BUDGET 172→170, 只改 HM1 对 HM2 0 影响), 故本轮跳到 R1904.
> cc2 铁律: 只改 HM2 不碰 ms_gw.

## 数据 (30min 窗, 本 session ~15:40 CST / 07:40 UTC 拉取)
- **SR 47/47 = 100%** (200:47 / 502:0). 近轮 96.7/93.65/94.2/88.9/89.7/87.6/90.9/93.0/93.9/94.9/96.36/100 (R1875→R1904),
  **当前 100% 抖动区间上沿, 抖动区间常态近 50 轮在 80.9-99 (本轮突破到 100), 非趋势性退化**.
- **502 分类 (0 条)**: 无. **无 zombie / 无 stream_absolute_cap / 无 ttfb / 无 gap / 无 deadline / 无 cfilter / 无 SSLEOF / 无 500_nv_error**.
  注: abs_cap ↔ zombie 在 NVCF empty200 上游侧来回切同源 (首字节慢/空), 本窗两者都 0, 非 nv_gw config 可解.
- tier pexec: **pexec_success 27** (干净基底, 无 ATE); IntegrateTimeout 2; pexec_timeout 1; pexec_empty_200 1 (NVCF 偶发);
  **pexec_SSLEOFError 30min tier=1 单点续** (R1902 1 → R1904 1, 出口 IP 段 134.195.101.0/24 同源, 非批量化非 nv_gw config 可修).
  无 500_nv_error (absorbed); 无 conn_RemoteDisconnected; 无 ttfb.
- **fallback 7 条全 FALLBACK-OK, 0 双路全炸, 0 真中断**:
  - 15:17 req=d065c2e7 → 75s SKIP-CIRCUIT (cc4101 preempt, NOT counted) → ms 16054ms.
  - 15:21 req=9da45256 → 75s SKIP-CIRCUIT (NOT counted) → ms 4398ms.
  - 15:25 req=5a3101d5 → 75s SKIP-CIRCUIT (NOT counted) → ms 2285ms.
  - 15:28 req=8d3b4459 → 75s SKIP-CIRCUIT (NOT counted) → ms 7167ms.
  - 15:31 req=66b9135d → 75s SKIP-CIRCUIT (NOT counted) → ms 8097ms.
  - 15:35 req=cf51853c → 75s SKIP-CIRCUIT (NOT counted) → ms 10083ms.
  - 15:38 req=5561d784 → 75s SKIP-CIRCUIT (NOT counted) → ms NV-MS-FB-SERVED (ms 兜底).
  **非跳过类真请求失败 0 条 < 4 阈值. 0 双路全炸, 0 真中断**.
  75s SKIP-CIRCUIT 抬头持平 (R1895≈0→R1896=6→R1898=8→R1900=5→R1902=7→R1904=7), 全 NOT counted 0 真中断 — cc4101 bug3 preempt 行为持续, nv_gw 侧无 config 可解 (75s 是 cc4101 chain budget 前置切, 非 nv_gw UPSTREAM/TIER_BUDGET).
- **NV-CAP-RESET-MSFB (R1818 bug7 cap_origin reset) 30min = 5 次** (req=fb3b04d6/6909f5d4/e2fa01b5/9cc9f443/5561d784),
  `total_elapsed_pre_reset` = 243~250s. 这是 bug7 已修路径的正常工作: nv 侧首字节拖到 ~245s 被绝对上限截断 → 甩 ms_fb 兜底 → cap_origin reset. 与 R1891 观察的 abs_cap 同源 (NVCF 首字节拖 168-251s), 非 nv_gw config 可解. 机制工作正常.
- bug8: 实战降级触发 0 (60min log 确认, 根除停巡连续 50+ 轮 0 触发).
- breaker 30min: **OPEN 事件 0** (全 CLOSED):
  - 5 次 NV-MS-FB-SERVED (ms 兜底, state=CLOSED, 对应上面 5 次 cap_reset).
  - 0 次 NV-ANTH-BREAKER-FAIL (abs_cap 本窗 0, 无需 breaker 吸收).
  - **R1889 12:59 OPEN (HALF_OPEN probe 13:03 自回 CLOSED) 连续 10 轮 (R1890-R1904) 无复现** = 单次设计内动作非恶化.
- env 无漂移 (KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 /
  TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 /
  MIN_OUTBOUND=0, 全与 R1850-R1902 一致).
- oai_to_anth.py md5=4983bcec 宿主/容器一致.

## 验证结果
链路稳态持续 (SR 100% 抖动区间上沿近 50 轮常态, 本轮突破到 100) +
abs_cap/zombie 本窗均 0 (NVCF empty200 同源来回切, 本窗两者都 0 走 nv_breaker 吸收机制工作正常 (本窗 abs_cap 0 无需吸收)) +
breaker OPEN 0 复现连续 10 轮坐实 R1889 12:59 OPEN 是单次设计内动作 +
非跳过类真请求失败 0 条 + 0 双路全炸 + 0 真中断 (7 条 75s SKIP 全被 ms_gw 兜住) +
bug8 0 触发 (根除停巡) + SSLEOF 1 单点续 (出口 IP 段同源) + 500_nv_error absorbed +
/health ok + docker ps 全 Up (nv_gw Up 10h / cc4101 Up 24h / ms_gw Up 2d / logs_db Up 2d).
StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码. 连续 NOP 巡检轮 (R1842-R1904), 链路稳态.

## 决策理由 (NOP 无据不改)
介入触发四条全不满足:
1. **SR 100% 远高于 80 线**, 抖动区间上沿常态, 非持续跌破 80 退化.
2. **非跳过类真请求失败 0 条 < 4 次/30min 介入线** (7 条全 75s SKIP-CIRCUIT, NOT counted).
3. **breaker OPEN 30min=0 (全 CLOSED)**, 连续 10 轮无复现, 未达 >=3 次/30min 介入线.
4. **无新可配置错误分类** (502 全 0; SSLEOF 1 单点续出口 IP 段同源; abs_cap 0; zombie 0; 500_nv_error absorbed; ttfb 0; gap/deadline/cfilter 无).
   注: NV-CAP-RESET-MSFB 是 bug7 已修路径的正常工作 (nv 首字节拖到 abs_cap 截断 → 甩 ms_fb), 非 nv_gw config 可解.
→ 硬改违反铁律 1 (改前必有数据 + 无据不改).
R1881-R1892 已穷尽 nv_gw 调参旋钮并反证 (TIER_BUDGET 收紧误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST + abs_cap wall-clock 非上游 TIER_BUDGET 可收紧 + UPSTREAM 改不动 NVCF 侧).
75s SKIP 是 cc4101 bug3 preempt, 非 nv_gw 旋钮可解.

## 给监督者/运维 (沿用 R1881-R1902)
- **换出口 IP 段**: 让 HM2 5 个 mihomo 端口 (7894-7899) 背后走非 134.195.101.0/24, 解 SSLEOF / 500_nv_error / abs_cap 同源 (NVCF 端对该 /24 段 TLS RST / 500 限流 / 首字节极慢到 abs_cap 截断).
- **联系 NVCF 运维**: 查该 /24 段 TLS RST / 500 限流 / 首字节为何拖到 abs_cap 截断策略, 以及 all_keys_exhausted 短窗集中是否 NVCF 端配额调度问题.
- **短期 cycle/breaker/fallback 三层吸收已在位**, 兜底 SR 80.9-100 近 50 轮可接受, 0 真中断. breaker OPEN 自恢复机制工作正常, abs_cap/zombie 走 nv_breaker 吸收不 OPEN.

## 下一轮重点 (R1905)
- **abs_cap ↔ zombie 是否续在 NVCF empty200 同源来回切**: 本轮两者都 0 (vs R1902 zombie 2 / abs_cap 0). 若 zombie/abs_cap 批量化 → 查上游.
- **breaker OPEN 是否复现** (连续 10 轮 0): 若 >=3 次/30min 且不自回 CLOSED → 真正软挂恶化信号. 单次/0 → 设计内吸收态.
- **75s SKIP-CIRCUIT 抬头是否续** (R1902=7→R1904=7 持平): 全 NOT counted 0 真中断, 关注是否某窗突破到非跳过类真 nv_gw 失败 (>=4 次/30min 才介入).
- **SR 是否续在 80.9-100 抖动**: 当前 100 上沿, 近 50 轮常态. 持续跌破 80 → 真退化.
- **SSLEOF / 500_nv_error / ttfb 是否批量化复发**: 当前 SSLEOF 1 单点续, 余停闭合. 批量化 → 查 upstream.

**介入触发条件** (任一满足才动手, 否则继续 NOP 巡检):
1. SR 持续跌破 80% (真退化, 非抖动).
2. fallback 中**非跳过类** (120s 黑洞 / FALLBACK-OK 真正 nv_gw 失败, 非 75s SKIP) >=4 次/30min.
3. **breaker OPEN 频繁复现** (>=3 次/30min) 且不自回 CLOSED.
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap/all_keys_exhausted/500_nv_error absorbed).
若以上都不满足, 继续 NOP 巡检轮.
