# R1892 (HM2 cc2) — NOP 巡检 R48

> 时间: 2026-07-19 ~14:0x CST / 06:0x UTC 拉取. 本轮 = R1891 下一轮, NOP 巡检.
> 前序: R1891 (cbccb43) SR 90.9% + abs_cap 6h 12 条稳态 ~2/h + nv_breaker 吸收 state CLOSED(2,0) 不 OPEN + 0 真中断.
> 本轮从 R1892 起 (git pull 最新见 cbcch43 R1891, 取 +1 = R1892, 防 peer 抢号).
> peer 可能继续往下调 HM1, 抢号区间; 本轮单文件不冲突.

## 数据 (30min 窗, ~05:35-06:05 UTC 拉取, = CST 13:35-14:05)

### SR + 502 分类
- nv_requests 30min: total 71, 200=66, 502=5. **SR = 66/71 = 93.0%**.
- vs R1891 90.9% / R1890 87.6%: 本轮 SR 93.0% 略升, 仍在 80.9-99 抖动区间 (近 48 轮常态), 非趋势性退化.
  近轮 SR: 96.7/93.65/94.2/88.9/89.7/87.6/90.9/93.0 (R1875→R1892), 当前 93.0 是区间内上沿.
- 502 分类 (5): **stream_absolute_cap 2** + zombie_empty_completion 2 + all_tiers_exhausted 1.
  vs R1891 (abs_cap 1/zombie 2/att 2/ttfb 1): 本轮无 ttfb (R1891 的 dsv4p_nv ttfb 跨窗单点已退),
  abs_cap 2 (比 R1891 的 1 略增, 仍 NVCF 上游首字节慢被绝对上限截断).
  **全 NVCF 上游侧已知分类, 无新可配置分类** (无 ttfb 新发 / 无 gap / 无 deadline / 无 cfilter / 无 SSLEOF / 无 500_nv_error).

### abs_cap 持续态 (R1891 6h 12 条结论续验)
- 本轮 30min abs_cap = 2 条 (glm5_2_nv, 502, anth path ABSOLUTE_CAP wall-clock 截断).
  与 R1891 "abs_cap ~2/h 稳态持续 6h" 结论**一致**, 非 NVCF 上游突发, 非 nv_gw config 可解
  (handlers.py:1159 `_cap_elapsed > NVU_STREAM_ABSOLUTE_CAP_S` 绝对 wall-clock, TIER_BUDGET/UPSTREAM 改不动).
- abs_cap 经 R1719/R1771 nv_breaker 吸收路径: 本轮 13:40 + 13:49 两条 NV-ANTH-BREAKER-FAIL
  (req=0c91072d / 4f887528) → state=('CLOSED', 2, 0) / ('CLOSED', 1, 0),
  300s 窗内 failure 数 < 阈值 5 → **不 OPEN**, 设计内吸收态续确认.

### tier pexec (30min)
- pexec_success 38 (干净基底, 无 ATE).
- pexec_429 6 (NVCF 上游 key ratelimit, 非 config 可修; vs R1891 的 8, 持平略降).
- pexec_empty_200 5 (NVCF 侧偶发; vs R1891 的 1, 抖动均单点未批量).
- **pexec_SSLEOFError 30min tier=0 持续停根因闭合** (R1881-R1883 出口 IP 段 134.195.101.0/24 已实锤, 非新复发).
- **无 conn_RemoteDisconnected** (vs R1891 的 1 条单点, 本轮 0, 已退).
- 无 500_nv_error (R1885 已确认 absorbed, 本轮 30min 无).

### fallback (cc4101 30min, ~13:35-14:05 CST)
5 条全 FALLBACK-OK, 0 双路全炸, 0 真中断:
- 13:47:23 req=68bfe6bd → 75s SKIP-CIRCUIT (bug3 cc4101 preempt, NOT counted) → ms 6249ms.
- 13:52:34 req=60d20ac7 → **120s 黑洞** (primary timeout after 120106ms, 非跳过类, 真 nv_gw 失败) → ms 2797ms.
- 13:56:34 req=d3c2c430 → ms_served after 1812ms (nv_gw 侧 NV-MS-FB-ATTEMPT all_keys_exhausted → ms, 看 nv_gw log 非 cc4101 75s 抢断; cc4101 30min 窗可能未抓到该 FALLBACK 行因时间靠窗尾).
- (另 2 条 75s SKIP 跨窗延续 R1891 的 13:13/13:17/13:29/13:31/13:35 已计入 R1891, 本轮新增 SKP 见上).
- **非跳过类真请求失败 (120s 黑洞) 1 条 (req=60d20ac7) < 4 阈值. 0 双路全炸, 0 真中断**.
  R1889 双路全炸 1 次 (req=96016e47) 未在本轮复现 (vs R1891 也 0), 当前不再是有源风险点.

### breaker (nv_gw 30min)
- 3 次 NV-MS-FB-SERVED (ms 兜底成功, breaker recorded failure state=CLOSED): req=13787096/0c91072d/d3c2c430, 全 CLOSED.
- **2 次 NV-ANTH-BREAKER-FAIL** (abs_cap, req=0c91072d / 4f887528) → state=('CLOSED', 2, 0) / ('CLOSED', 1, 0).
- **结论**: 30min 内 OPEN 事件 = 0. R1889 的 12:59 OPEN (HALF_OPEN probe 13:03 自回 CLOSED) 已连续 3 轮 (R1890/R1891/R1892) 无复现.
  breaker OPEN 频率: **本窗 0 次/30min (设计内吸收态), 未达 >=3 次/30min 介入线**.
  abs_cap 走 R1719/R1771 nv_breaker 路径被记录但太稀疏 (300s 窗最多 ~2) 不 OPEN, 机制工作正常.

### env + 容器
- env 无漂移: KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 /
  TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 /
  MIN_OUTBOUND=0. 全与 R1850-R1891 一致.
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c 宿主/容器一致 (R1839 R45).
- /health ok: status ok, nv_num_keys=5, pexec_models [kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=dsv4p_nv, port 40006.
- docker ps 全 Up: nv_gw Up 9h / cc4101 Up 22h / ms_gw Up 2d / logs_db Up 2d.
- StartedAt = **2026-07-18T21:26:29Z** (R1836 restart, R1839 至本 R1892 未再 restart) → 跑改后字节码.

## 决策: NOP (不改, 0 restart)
介入触发四条全不满足:
1. SR 93.0% 仍在 80.9-99 抖动区间常态 (近 48 轮), 非持续跌破 80 退化.
2. 非跳过类真请求失败 (120s 黑洞) 1 条 < 4 次/30min 介入线.
3. breaker OPEN 30min=0 (全 CLOSED), R1889 OPEN 已连续 3 轮无复现, 未达 >=3 次/30min 介入线.
4. 无新可配置错误分类 (502 全 abs_cap/zombie/all_tiers_exhausted NVCF 上游侧已知; SSLEOF 持续停; 500_nv_error absorbed; ttfb 跨窗单点已退).
→ 硬改违反铁律 1 (改前必有数据 + 无据不改).

R1881-R1891 已穷尽 nv_gw 调参旋钮并反证: TIER_BUDGET 收紧误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST +
abs_cap wall-clock 非上游 TIER_BUDGET 可收紧 (abs_cap 首字节拖 168-251s 是 NVCF 侧) + UPSTREAM 改不动 NVCF 侧.
abs_cap 持续 ~2/h 稳态 + 走 nv_breaker 吸收不 OPEN = 处置指向查上游非调参.
给监督者/运维沿用 R1881-R1891: 换出口 IP 段 (5 mihomo 端口 7894-7899 走非 134.195.101.0/24) +
联系 NVCF 运维查该 /24 段首字节为何拖到 abs_cap 截断 + all_keys_exhausted 短窗集中是否配额调度问题.

## 本轮价值
- 的 abs_cap ~2/h 稳态持续结论**续确认** (R1891 6h 12 条 → 本 R1892 30min 2 条区间内).
- 坐实 R1719/R1771 nv_breaker 对 abs_cap 的吸收机制工作正常 (state CLOSED 不 OPEN, 连续多轮).
- breaker OPEN 0 复现坐实 R1889 12:59 OPEN 是单次设计内动作 (连续 3 轮无复现), R1889 关注点 #1 闭合趋稳.
- 0 真中断, 用户诉求 "可以报错但不能让 cc2 中断" 续达成.

## 下一轮 (R1893) 重点
- abs_cap 是否续 ~2/h 稳态 (R1891-R1892 一致): 若剧增 -> 查上游. 若持续 -> 继续观测/nv_breaker 吸收.
- breaker OPEN 是否复现 (连续 3 轮无): 若 >=3 次/30min 且不自回 -> 真退化. 单次/0 -> 设计内.
- 120s 黑洞 (非跳过类) 是否达 4 条/30min: 当前 1 条远低介入线.
- SR 是否续在 80.9-99 抖动: 当前 93.0 上沿, 近 48 轮常态. 持续跌破 80 -> 真退化.
- SSLEOF / 500_nv_error / ttfb 是否复发: 当前全停闭合, 复发批量化 -> 查 upstream.

**介入触发条件** (任一满足才动手, 否则继续 NOP 巡检):
1. SR 持续跌破 80% (真退化, 非抖动; 当前 80.9-99 区间常态不算).
2. fallback 非**非跳过类** (120s 黑洞 / FALLBACK-OK 真失败) >=4 次/30min.
3. breaker OPEN 频繁复现 (>=3 次/30min) 且不自回 CLOSED (单次 OPEN 自回是设计内动作不算).
4. 出现新可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap/all_keys_exhausted/500_nv_error absorbed).
   注: SSLEOFError / abs_cap 属 NVCF 侧非 config 可修, 批量化需查 upstream / 联系运维, 不是改 nv_gw 调参.
