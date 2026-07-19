# R1890 (HM2 cc2) — NOP 巡检 R46

> 时间: 2026-07-19 ~13:25 CST / 05:25 UTC 拉取. 本轮 = R1889 下一轮, NOP 巡检.
> 前序: R1889 (b786c6e) SR 89.7% 抖动区间 + breaker 短暂 OPEN 自恢复 + 双路全炸 1 次仍 0 真中断.
> 同号双 commit 已发生: peer 用 R1889 号写 `R1889_hm2_optimize_hm1.md` (HM2→HM1, 加 dsv4p_nv 到 BIG_INPUT breaker,
> commit a16aa56, 仅改 HM1 round 文件未碰 HM2 nv_gw 源码); 我用 R1889 号写 `R1889_hm2_cc2_breaker_open_self_recovered.md`.
> 本轮从 R1890 起 (git pull 最新见 b786c6e/a16aa56 双 R1889, 取 +1 = R1890, 防 peer 抢号).

## 数据 (30min 窗, 05:00-05:25 UTC 拉取, = CST 12:55-13:25)

### SR + 502 分类
- nv_requests 30min: total 98, 200=86, 502=12. **SR = 86/98 = 87.6%**.
- 502 分类 (12): all_tiers_exhausted 8 + zombie_empty_completion 3 + **stream_first_byte_timeout 1 (本轮新增)**.
- **vs R1889**: R1889 SR 89.7% (95/106), 502=11 全 all_tiers_exhausted 8 + zombie 3 (无 ttfb).
  本轮 SR 87.6% 略低于 R1889 但仍在 80.9-99 抖动区间 (近 40 轮常态), 非趋势性退化.
- ttfb 单点详情: 2026-07-19 05:23:04 UTC req (DB). **R1889 是 0 ttfb, 本轮出现 1 条单点**.
  单点未批量化, 非新可配置分类定型 (stream_first_byte_timeout 是已知 tier→app 聚合终态, 非 abs_cap/ttfb batch).

### tier pexec (30min)
- pexec_success 69 (干净基底, 无 ATE).
- pexec_429 9 (NVCF 上游 key ratelimit, 非 config 可修; vs R1889 的 6, 略升仍 NVCF 上游侧).
- **pexec_conn_RemoteDisconnected 1 (本轮新增, vs R1889 无)**. 单点, 非 SSL 层 (与 SSLEOF 不同类), 非新可配置分类.
- pexec_empty_200 1 (NVCF 侧偶发).
- pexec_SSLEOFError 30min tier=0, **120min=1 持续停根因闭合** (R1881-R1883 出口 IP 段 134.195.101.0/24 已实锤, 非新复发).
- 注: 502 层 ttfb 1 与 tier 层 pexec_conn_RemoteDisconnected 1 可能同源 (单点上游连接被打断 → ttfb),
  均单点未批量, 不足介入.

### fallback (cc4101 30min, 12:55-13:25 CST)
5 条 FALLBACK-OK + 1 条双路全失败:
- 12:58 req=96016e47 → 双路全失败: nv 75s SKIP-CIRCUIT (bug3 抢断 cc4101 preempt, NOT counted) + ms 503 → **FALLBACK-FAIL → CC outer retry 兜住, 0 真中断**. (跨窗延续 R1889 同 req ID)
- 13:00 req=1765d8d7 → 75s SKIP-CIRCUIT → FALLBACK-OK ms 3158ms. (跨窗延续)
- 13:05 req=a18c8283 → **120s 黑洞 (nv 120107ms, 非跳过类) → FALLBACK-OK ms 4379ms**. (跨窗延续 R1889 同 req ID)
- 13:11 req=c6c8ee08 → 75s SKIP-CIRCUIT → FALLBACK-OK ms 6885ms. (新)
- 13:13 req=90cc9413 → 75s SKIP-CIRCUIT → FALLBACK-OK ms 3783ms. (新)
- 13:17 req=605cd3c0 → 75s SKIP-CIRCUIT → FALLBACK-OK ms 2684ms. (新)
- **非跳过类真请求失败 (120s 黑洞) 本窗 1 条 (a18c8283) < 4 阈值. 0 真中断 (96016e47 被 CC outer retry 兜住).**

### breaker (nv_gw 30min)
- 12:59:02.4 NV-MS-FB-FAIL req=c377ae47 breaker=OPEN (12:58-12:59 all_keys_exhausted 短窗集中, ms_gw 又 503).
- 12:59:02.8 NV-MS-FB-BREAKER-OPEN req=7a75d5b2 state=('OPEN',5,29) → BREAKER-OPEN-MSFAIL falling through HALF_OPEN probe.
- 13:03:04.9 NV-MS-FB-SERVED req=dd2f8544 state=CLOSED — HALF_OPEN probe nv chain 恢复成功, breaker 自回 CLOSED.
- 13:03:33 / 13:09:17 / 13:13:54 / 13:16:40 / 13:20:23 — 全 NV-MS-FB-SERVED state=CLOSED, 稳态吸收.
- **结论**: 30min 内 OPEN 事件 = **1 次 (12:59, 与 R1889 同一事件跨窗延续, 非新复现)**, HALF_OPEN probe 13:03 自回 CLOSED 后无再 OPEN.
  - 即: R1889 记的 12:59 OPEN 在本轮 30min 窗边界内 (12:55-13:25), 仍是那 1 次, 不是"复现".
  - breaker OPEN 频率: **本窗 1 次/30min (设计内吸收态), 未达 >=3 次/30min 介入线**.
  - 与 R1879 关切的 state 漂移一致 (state 第二字段 OPEN 时=5 → 自回 CLOSED=0, 设计内吸收态).

### env + 容器
- env 无漂移: KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 /
  TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 /
  MIN_OUTBOUND=0. 全与 R1850-R1889 一致.
- NV_INTEGRATE_EGRESS_IPS=134.195.101.193,134.195.101.193,134.195.101.195,134.195.101.193,134.195.101.180
  → **出口 IP 仍 134.195.101.0/24 段未换** (R1881-R1889 实锤的 SSLEOF/500_nv_error/all_keys_exhausted 同源段).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c 宿主/容器一致 (host format/ 子目录 vs container /app/gateway/format/).
- /health ok: status ok, nv_num_keys=5, pexec_models [kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=dsv4p_nv, port 40006.
- docker ps 全 Up: nv_gw Up 8h / cc4101 Up 21h / ms_gw Up 2d / logs_db Up 2d.
- nv_gw StartedAt = 2026-07-18T21:26:29Z (= R1836 restart, R1839 至 R1890 未再 restart) → 仍跑 R1839 改后字节码.

## 决策: NOP (不改)
介入触发四条全不满足:
1. **SR 连破但 R1881-R1883 已穷尽 nv_gw 调参旋钮并反证** (TIER_BUDGET 收紧误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST + UPSTREAM 改不动 NVCF 侧 abs_cap/zombie) → 处置指向查上游非调参. 本轮 SR 87.6% > 80 仍在抖动区间常态, #1 不满足真退化线.
2. **非跳过类真请求失败 (120s 黑洞) 1 条 < 4 阈值**. (a18c8283 跨窗延续单点)
3. **breaker OPEN 单次 (12:59 R1889 延续) 自回 CLOSED, 未达 >=3 次/30min 介入线**. OPEN 是设计内动作 (R1839 "宁可 OPEN 走 ms 也不死循环"), HALF_OPEN probe 13:03 自回 CLOSED 后稳态吸收, 非源码 bug. 真正该看的是 OPEN 频率非 state 数字, 本窗 1 次未恶化.
4. **无新可配置错误分类批量化**:
   - ttfb (stream_first_byte_timeout) 1 条单点未批量 → 不算新分类定型 (已知 tier→app 聚合终态).
   - pexec_conn_RemoteDisconnected 1 条单点 → 非 SSL 层非新可配置类别.
   - SSLEOF 30min tier=0 / 120min=1 持续停根因闭合.
   - 500_nv_error 已确认 absorbed (R1885 闭合).
   - all_tiers_exhausted 8 是 NVCF 上游 key 耗尽兜底, zombie 3 是 content-filter, 全 NVCF 上游侧已知分类.
→ 硬改违反铁律 1 (改前必有数据 + 无据不改).

## 本轮价值
1. **确认 breaker OPEN 无新复现**: R1889 记的 12:59 OPEN 在本轮 30min 窗边界内仍是那 1 次, HALF_OPEN probe 13:03 自回 CLOSED 后 13:09-13:20 全 CLOSED 稳态吸收. **"OPEN 是否复现/频率" 关切 (R1889 下一步首要) 答案: 否, 未复现, 设计内吸收态持续**.
2. **记录 ttfb 单点出现**: R1889 是 0 ttfb, 本轮 05:23 UTC 出现 1 条 stream_first_byte_timeout + tier pexec_conn_RemoteDisconnected 1, 可能同源 (单点上游连接被打断 → ttfb). 单点未批量, 监控是否续升.
3. **双路全炸窗口未续复现**: 12:58 req=96016e47 是跨窗延续单点 (R1889 同), 本窗无新双路全炸. 0 真中断 (CC outer retry 兜住).
4. **接续 R1881-R1889 结论**: nv_gw 调参旋钮已穷尽, 处置指向查上游 (换出口 IP 段 / 联系 NVCF 运维).

## 给监督者/运维 (沿用 R1881-R1889, 无新结论)
1. **换出口 IP 段**: HM2 5 mihomo 端口 (7894-7899) 背后走非 134.195.101.0/24, 解 SSLEOF / 500_nv_error / all_keys_exhausted 同源 (NVCF 端对该 /24 段 TLS RST / 500 限流). 本轮 env 快照确认出口 IP 仍该段未换.
2. **联系 NVCF 运维**: 查该 /24 段 TLS RST / 500 限流策略, all_keys_exhausted 短窗集中 (12:58-12:59 连续 4 req 全 key 耗尽) 是否 NVCF 端配额调度问题.
3. **短期 cycle/breaker/fallback 三层吸收已在位**, 兜底 SR 80.9-99 近 40 轮可接受, 0 真中断. breaker OPEN 自恢复机制工作正常.
4. 维持铁律: 只改 HM2, 改 .py 必须 restart 非 up-d, 不碰 ms_gw, 所有改动写入仓库.

## 下轮 R1891 重点
- **ttfb 是否续升/批量化** (本轮 1 条单点, 若 >=3/30min → 需查是否 TIER_BUDGET 可收紧, 但 R1882 已反证收紧误杀慢成功, 谨慎).
- **pexec_conn_RemoteDisconnected 是否续升** (本轮 1 条单点, 非新可配置分类, 若批量 → 查上游连接层).
- **breaker OPEN 是否新复现** (本轮 0 新 OPEN, R1889 的 12:59 已自回 CLOSED 稳态. 若 >=3 次/30min 且不自回 → 真软挂恶化信号).
- **双路全炸窗口是否复现** (本轮 0 新, 跨窗 96016e47 单点. 若 >=3 次/30min → 用户体验真退化需查 ms_gw 为何也 503, 但热备不改源码只能查 upstream).
- **SR 续在 80.9-99 抖动** (本轮 87.6%, 若持续跌破 80 → 真退化).
- **SSLEOF / 500_nv_error 复发** (当前停根因闭合, 若批量 → 查 upstream 换出口 IP 段).

介入触发条件 (任一满足才动手, 否则继续 NOP):
1. SR 持续跌破 80% (真退化, 非抖动).
2. fallback 中非跳过类 (120s 黑洞 / FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min.
3. breaker OPEN 频繁复现 (>=3 次/30min) 且不自回 CLOSED.
4. 出现新可配置错误分类批量化 (非 NVCF 侧 zombie/timeout/gap/cap/all_keys_exhausted/500_nv_error absorbed; SSLEOFError/RemoteDisconnected 属 NVCF 侧 TLS/连接层非 config 可修, 批量化需查 upstream 换出口 IP 段).

注: 连续 NOP 巡检 (R1842-R1890) 链路稳态. SR 近轮 96.7/93.65/94.2/88.9/89.7/87.6 (R1875/R1877/R1878/R1879/R1887/R1889/R1890),
本轮 87.6 是抖动区间常态 (略低于 R1889 但非趋势), 不主动改.

本轮 R1890 commit 单文件 (本 round 文件), 无 peer 误收 (peer 已推到 a16aa56 R1889 HM2→HM1, 本轮 R1890 不冲突). 文案准确.
