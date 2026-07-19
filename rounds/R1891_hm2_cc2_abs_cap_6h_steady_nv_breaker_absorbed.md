# R1891 (HM2 cc2) — NOP 巡检 R47

> 时间: 2026-07-19 ~13:42-13:46 CST / 05:42-05:46 UTC 拉取. 本轮 = R1890 下一轮, NOP 巡检.
> 前序: R1890 (87d0712) SR 87.6% + ttfb 单点 + breaker 无新复现 0 真中断.
> 本轮从 R1891 起 (git pull 最新见 87d0712 R1890, 取 +1 = R1891, 防 peer 抢号).
> peer 可能继续往下调 HM1, 抢号区间; 本轮单文件不冲突.

## 数据 (30min 窗, 05:11-05:41 UTC 拉取, = CST 13:11-13:41)

### SR + 502 分类
- nv_requests 30min: total 66, 200=60, 502=6. **SR = 60/66 = 90.9%**.
- 35min 补测: 73/79 = 92.4% (上沿稳态持续).
- 502 分类 (6): all_tiers_exhausted 2 + zombie_empty_completion 2 + **stream_absolute_cap 1 (本轮窗内新出现)** + stream_first_byte_timeout 1.
- vs R1890: R1890 SR 87.6% (86/98), 502=12 (all_tiers_exhausted 8 + zombie 3 + ttfb 1, **0 abs_cap**).
  本轮 SR 90.9% 略高于 R1890, 仍在 80.9-99 抖动区间 (近 40 轮常态), 非趋势性退化.
  **abs_cap 1 条** (vs R1890 的 0) 是本轮窗内新观察; 详见下方 abs_cap 6h 稳态分析.

### abs_cap 6h 稳态分析 (本轮核心新观察)
- 6h (00:00-05:40 UTC) 累计 **12 条** abs_cap, 全 glm5_2_nv, 全 502, dur=168-414s, ttfb=168-251s (超长流式).
  时间分布: 00:00-01:00=2, 02:00-03:00=2, 03:00-04:00=4, 04:00-05:00=3, 05:00-06:00=1.
  **平均 ~2/h 稳态持续 6h, 非尖峰非突发**, 是 NVCF 上游侧持续现象 (首字节拖到 168-251s 被绝对上限截断).
- 代码路径 (handlers.py:1159 `_cap_elapsed > NVU_STREAM_ABSOLUTE_CAP_S`):
  abs_cap 在 anth path 的 ABSOLUTE_CAP wall-clock 检查处 set error_type + break, 是
  R1787 加的 anth path 绝对 wall-clock cap (镜像 passthrough path R1781). cap 基准用 cap_origin
  (R1818 bug7: ms fb 成功后会重置, 防误判).
- **R1719/R1771 nv_breaker 设计吸收**: abs_cap 退出循环后, 经 handlers.py:1350-1365 的
  R1719 anth mid-stream soft-fail record 路径 (error_type 非空 + mapped_model in NVU_MS_FALLBACK_MODELS +
  非 all_429 → record_nv_failure()), 进 nv_breaker 累计.
  nv_breaker (nv_breaker.py) R1771 time-windowed 语义: 300s 窗口 deque, 累计 >= 阈值 5 才 OPEN.
  abs_cap ~2/h 稀疏 (300s 窗内最多 ~2 条), 远低于阈值 5 → **state=('CLOSED', 2, 0) 不 OPEN**,
  设计内吸收态 (R1771 注释明确"sporadically-failing degraded chain 会 eventually trip" 但 abs_cap 太稀疏达不到).
- **本轮 13:40:52 NV-ANTH-BREAKER-FAIL** (req=0c91072d, 即 abs_cap 那条 05:40:52 UTC) →
  state=('CLOSED', 2, 0) 确认: abs_cap 被 nv_breaker 记录为第 2 个 failure, 未 OPEN.
- **结论**: abs_cap 是 R1881-R1890 已结论"nv_gw 调参旋钮已穷尽, 处置指向查上游"的又一实证.
  abs_cap 根因在 NVCF 上游侧 (首字节拖 168-251s 才被绝对上限截断), 非 nv_gw config 能解
  (TIER_BUDGET/UPSTREAM 改不动 NVCF 侧 abs_cap; R1882 反证 TIER_BUDGET 收紧误杀慢成功 SR 暴跌).
  R1719/R1771 nv_breaker 设计吸收机制工作正常 (state CLOSED(2,0) 未 OPEN), 保护后续同类 req 不死循环.
  给监督者/运维沿用 R1881-R1890: 查上游换出口 IP 段 / 联系 NVCF 运维查该 /24 段首字节为何拖 168-251s.

### 500_nv_error absorbed 确认 (R1885 结论续验)
- 120min tier 层 500_nv_error = 8 条, 对应 5 个 request_id, 全 dsv4p_nv tier, 04:35-04:46 UTC 集中.
- 对应 nv_requests 最终状态: **4/5 = 80% 被 NV-CYCLE 吸收成 200**, 1 个成 502 zombie_empty_completion.
  → R1885 "500_nv_error 80% 被 NV-CYCLE 吸收成 200" 结论**续成立**, 非 nv_gw 可配置分类.

### tier pexec (30min)
- pexec_success 36 (干净基底, 无 ATE).
- pexec_429 8 (NVCF 上游 key ratelimit, 非 config 可修; vs R1890 的 9, 持平).
- pexec_conn_RemoteDisconnected 1 (05:22:28 UTC, glm5_2_nv, 单点; vs R1890 也 1 条, 与 ttfb 05:23 同源时段).
- pexec_empty_200 1 (NVCF 侧偶发).
- **pexec_SSLEOFError 30min tier=0, 120min=1 持续停根因闭合** (R1881-R1883 出口 IP 段 134.195.101.0/24 已实锤, 非新复发).
- 注: 502 层 ttfb 1 条 (05:23:04 dsv4p_nv, 与 R1890 同一 req 跨窗延续, 非新发生) +
  tier 层 RemoteDisconnected 1 条 (05:22 glm5_2_nv) 时间相近不同 model 可能同源 (单点上游连接被打断 → ttfb),
  均单点未批量, 不足介入.

### fallback (cc4101 30min, 13:11-13:41 CST)
5 条全 FALLBACK-OK, 0 双路全炸, 0 真中断:
- 13:13 req=90cc9413 → 75s SKIP-CIRCUIT (bug3 cc4101 preempt, NOT counted) → ms 3783ms. (跨窗延续 R1890)
- 13:17 req=605cd3c0 → 75s SKIP-CIRCUIT → ms 2684ms. (跨窗延续 R1890)
- 13:29 req=d6e92661 → 75s SKIP-CIRCUIT → ms 4988ms. (新)
- 13:31 req=0f8214f5 → 75s SKIP-CIRCUIT → ms 2955ms. (新)
- 13:35 req=90ea17cf → 75s SKIP-CIRCUIT → ms 3456ms. (新)
- **全 5 条均 75s SKIP-CIRCUIT (cc4101 header/ttfb 75s 抢断 nv_gw, NOT counted), 0 非跳过类 120s 黑洞, 0 双路全炸, 0 真中断**.
- 注: 5 条 75s header/ttfb timeout 是 cc4101 的 header 阈值 (75s) 抢在 nv_gw TIER_BUDGET 180s 之前甩 ms,
  与 abs_cap 那些 ttfb 176-251s 同源 (NVCF 上游首字节极慢), 只是 cc4101 75s 先抢断.

### breaker (nv_gw 30min)
- 5 次 NV-MS-FB-SERVED (ms 兜底成功, breaker recorded failure state=CLOSED), 全 CLOSED.
- **13:40:52 NV-ANTH-BREAKER-FAIL req=0c91072d** (abs_cap 那条) → state=('CLOSED', 2, 0)
  (300s 窗内 2 failures < 阈值 5, 不 OPEN).
- **结论**: 30min 内 OPEN 事件 = 0. R1889 的 12:59 OPEN (HALF_OPEN probe 13:03 自回 CLOSED) 已稳态,
  本轮无新 OPEN. breaker OPEN 频率: **本窗 0 次/30min (设计内吸收态), 未达 >=3 次/30min 介入线**.
  abs_cap 走 nv_breaker R1719 路径被记录但太稀疏不 OPEN, 机制工作正常.

### env + 容器
- env 无漂移: KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 /
  TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 /
  MIN_OUTBOUND=0. 全与 R1850-R1890 一致.
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c 宿主/容器一致.
- /health ok: status ok, nv_num_keys=5, pexec_models [kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=dsv4p_nv, port 40006.
- docker ps 全 Up: nv_gw Up 8h / cc4101 Up 22h / ms_gw Up 2d / logs_db Up 2d.
- nv_gw StartedAt = 2026-07-18T21:26:29Z (= R1836 restart, R1839 至 R1891 未再 restart) → 仍跑 R1839 改后字节码.

## 决策: NOP (不改)
介入触发四条全不满足:
1. **SR 连破但 R1881-R1883 已穷尽 nv_gw 调参旋钮并反证** (TIER_BUDGET 收紧误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST + UPSTREAM 改不动 NVCF 侧 abs_cap/zombie) → 处置指向查上游非调参. 本轮 SR 90.9% > 80 仍在抖动区间常态, #1 不满足真退化线.
2. **非跳过类真请求失败 (120s 黑洞) 0 条 < 4 阈值**. (本窗 5 条全 75s SKIP-CIRCUIT NOT counted)
3. **breaker OPEN 0 次/30min (设计内吸收态), 未达 >=3 次/30min 介入线**.
   abs_cap 走 nv_breaker R1719 路径被记录但 state=('CLOSED',2,0) 太稀疏不 OPEN, 机制工作正常非源码 bug.
4. **无新 nv_gw 可配置错误分类批量化**:
   - abs_cap (stream_absolute_cap) 30min=1, 6h=12 (~2/h 稳态持续 6h 非突发) → 非"本轮新复现批量",
     是 R1881-R1890 已结论的 NVCF 上游侧持续现象的首次专门记录; 根因首字节拖 168-251s 在上游, 非 nv_gw config 能解.
   - 500_nv_error 120min=8 → 4/5 (80%) 被 NV-CYCLE 吸收成 200, R1885 absorbed 结论续成立, 非新分类.
   - ttfb 1 条 (跨窗延续 R1890 单点), RemoteDisconnected 1 条 (单点), SSLEOF 30min=0/120min=1 持续停根因闭合.
   - all_tiers_exhausted 2 是 NVCF 上游 key 耗尽兜底, zombie 2 是 content-filter, 全 NVCF 上游侧已知分类.
→ 硬改违反铁律 1 (改前必有数据 + 无据不改).

## 本轮价值
1. **首次专门记录 abs_cap 6h 稳态现象 (12 条 ~2/h)**: R1885-R1890 多轮 0 abs_cap 或未单独统计,
   本轮 120min=5 + 6h=12 把它坐实为 NVCF 上游侧持续现象 (非尖峰非突发). 根因首字节拖 168-251s
   被绝对上限截断, 在上游侧 (egress_ip 仍 NULL 是 R1883 数据盲区, 但出口 IP 段 134.195.101.0/24 已实锤).
2. **坐实 abs_cap 走 nv_breaker R1719 设计吸收**: handlers.py:1159 set error_type + break →
   handlers.py:1350-1365 R1719 record_nv_failure() → nv_breaker R1771 300s 窗口 deque 累计 (阈值 5).
   abs_cap ~2/h 稀疏 → 300s 窗最多 ~2 条 < 5 → state=('CLOSED',2,0) 不 OPEN, 设计内吸收态.
   **这就是为什么 abs_cap 持续 6h 12 条 但 breaker 从未因 abs_cap OPEN**: 稀疏性使然, 非源码 bug.
3. **500_nv_error absorbed 续验**: 4/5 (80%) 被 NV-CYCLE 吸收成 200, R1885 结论续成立.
4. **breaker OPEN 0 新复现**: R1889 的 12:59 OPEN 已稳态, 本轮 0 OPEN.
5. **接续 R1881-R1890 结论**: nv_gw 调参旋钮已穷尽, 处置指向查上游 (换出口 IP 段 / 联系 NVCF 运维查该 /24 段首字节为何拖 168-251s).

## 给监督者/运维 (沿用 R1881-R1890, 新增 abs_cap 实证)
1. **换出口 IP 段**: HM2 5 mihomo 端口 (7894-7899) 背后走非 134.195.101.0/24, 解 SSLEOF / 500_nv_error /
   all_keys_exhausted / **abs_cap 同源** (NVCF 端对该 /24 段首字节拖 168-251s + TLS RST / 500 限流).
2. **联系 NVCF 运维**: 查该 /24 段首字节为何拖 168-251s (abs_cap 根因) + TLS RST / 500 限流策略 +
   all_keys_exhausted 短窗集中 (全 5 key 同时 ratelimit/耗尽) 是否 NVCF 端配额调度问题.
3. **短期 cycle/breaker/fallback 三层吸收已在位**, 兜底 SR 80.9-99 近 40 轮可接受, 0 真中断.
   abs_cap 走 nv_breaker R1719 设计吸收 (state CLOSED(2,0) 未 OPEN), breaker OPEN 自恢复机制工作正常.
4. 维持铁律: 只改 HM2, 改 .py 必须 restart 非 up-d, 不碰 ms_gw, 所有改动写入仓库.

## 下轮 R1892 重点
- **abs_cap 是否续 ~2/h 稳态 / 或骤升批量化** (本轮 6h=12 稳态, 若骤升 >=5/h 且伴随 breaker 因 abs_cap 累计 OPEN
  → 真正 NVCF 上游侧恶化信号, 需查上游换出口 IP 段; 仍非 nv_gw 调参能解).
- **breaker OPEN 是否新复现** (本轮 0 OPEN, 若 >=3 次/30min 且不自回 CLOSED → 真软挂恶化信号).
- **双路全炸窗口是否复现** (本轮 0 新, 若 >=3 次/30min → 用户体验真退化需查 ms_gw 为何也 503, 但热备不改源码只能查 upstream).
- **120s 黑洞是否达 4 条/30min 介入线** (本轮 0 条).
- **SR 续在 80.9-99 抖动** (本轮 90.9%, 若持续跌破 80 → 真退化).
- **SSLEOF / 500_nv_error / ttfb / RemoteDisconnected 复发** (当前停根因闭合或 absorbed 或单点, 若批量 → 查 upstream).

介入触发条件 (任一满足才动手, 否则继续 NOP):
1. SR 持续跌破 80% (真退化, 非抖动).
2. fallback 中非跳过类 (120s 黑洞 / FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min.
3. breaker OPEN 频繁复现 (>=3 次/30min) 且不自回 CLOSED.
4. 出现新可配置错误分类批量化 (非 NVCF 侧 zombie/timeout/gap/cap/all_keys_exhausted/500_nv_error absorbed;
   SSLEOFError/RemoteDisconnected/abs_cap 属 NVCF 侧 TLS/连接/上游截断层非 config 可修,
   批量化需查 upstream 换出口 IP 段).

注: 连续 NOP 巡检 (R1842-R1891) 链路稳态. SR 近轮 96.7/93.65/94.2/88.9/89.7/87.6/90.9 (R1875/R1877/R1878/R1879/R1887/R1889/R1890/R1891),
本轮 90.9 是抖动区间常态 (略高于 R1890 87.6 非趋势), 不主动改.

本轮 R1891 commit 单文件 (本 round 文件), 无 peer 误收. 文案准确.
