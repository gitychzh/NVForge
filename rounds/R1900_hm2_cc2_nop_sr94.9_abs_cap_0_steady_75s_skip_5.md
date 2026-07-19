# R1900 (HM2 cc2) — NOP 巡检 R53

> 时间: 2026-07-19 ~15:12 CST / 07:12 UTC 拉取. git pull 已含 peer R1899 (HM2→HM1 TIER_BUDGET 176→174) + 上一session cc2 R1898 (commit 13914a9, 巡检 R52).
> 本轮做 **R1900** (R1899+1, 防 peer 抢号, git pull 已确认 99a58fd 为最新).

## 模式
nv 直连 (cc4101→nv_gw), R1839 bug8 真降级兜底 in-vivo 生效, R1841-R1898 连续 52 轮巡检确认.
本轮 R1900 = 第 53 轮巡检.

## 数据 (30min 窗 + 10min burst, 14:42-15:12 CST)
- **SR 56/59 = 94.9%** (200:56 / 502:3). 10min burst 未单独拉, 主窗 94.9 区间上沿.
  近轮 SR: 96.7/93.65/94.2/88.9/89.7/87.6/90.9/93.0/93.9/94.1/92.2/90.7/94.9 (R1875→R1900), **当前 94.9 区间上沿, 抖动区间常态近 53 轮在 80.9-99**, 非趋势性退化.
- **502 分类 (3 条, 全 NVCF 上游侧已知)**:
  - all_tiers_exhausted **1** (06:52:09 req=6106844b) — NVCF 上游全 key 耗尽短窗集中, 已知.
  - zombie_empty_completion **2** (07:04:59 ea422ef1 / 07:05:04 1af3fa07) — NVCF content-filter 空完成, 已知.
  - 无 stream_absolute_cap (R1898 的 1 条回落到 0), 无 stream_first_byte_timeout (R1898 单点已退), 无 gap, 无 deadline, 无 cfilter, 无 SSLEOF, 无 500_nv_error (NVCF 上游侧).
- **tier pexec**:
  - pexec_success **45** (干净基底, 无 ATE).
  - pexec_empty_200 **4** (NVCF 偶发).
  - pexec_timeout **2** (NVCF 上游慢, 非配置可修, 仍低量).
  - IntegrateTimeout **1** (单点, NVCF 集成侧).
  - 无 pexec_429 (本轮 0; NVCF key ratelimit 波动).
  - **pexec_SSLEOFError 30min tier=0 持续停根因闭合** (出口 IP 段 134.195.101.0/24 已实锤, 非新复发). 无 conn_RemoteDisconnected. 无 500_nv_error.
- **abs_cap 本轮 0** (30min nv_gw log 无 stream_absolute_cap / NV-ANTH-BREAKER-FAIL): R1891 6h 12 条 → R1892 2 → R1894 3 → R1895 2 → R1896 2 → R1898 1 → R1900 **0**, ~2-6/h 区间稳态持续, 本轮回落到 0, 非 NVCF 突发, 非 nv_gw config 可解 (handlers.py:1159 绝对 wall-clock).
  无 abs_cap → 无 NV-ANTH-BREAKER-FAIL 触发, nv_breaker 不需吸收 (300s 窗内 0 < 阈值 5 → 不 OPEN).
- **fallback 6 条全 FALLBACK-OK, 5 条 75s SKIP-CIRCUIT (NOT counted) + 0 非跳过类, 0 双路全炸, 0 真中断**:
  - 14:45 req=54024a66 → 75s SKIP-CIRCUIT (header/ttfb timeout after 75s) → ms 25780ms.
  - 14:49 req=ceecc5f5 → 75s SKIP-CIRCUIT → ms 10025ms.
  - 14:56 req=f96a2336 → 75s SKIP-CIRCUIT → ms 3372ms.
  - 15:03 req=8261eea4 → 75s SKIP-CIRCUIT → ms 3136ms.
  - 15:08 req=c63a5bef → 75s SKIP-CIRCUIT → ms 5008ms.
  - 14:42 req=ca6918d2 → (非 SKIP, 上一窗延续) → ms 13358ms.
  **非跳过类真请求失败 (120s 黑洞 / 真正 nv_gw 失败) 0 条 < 4 阈值**.
  全 5 条 75s SKIP-CIRCUIT 是 bug3 cc4101 preempt 设计内行为 (header/ttfb 75s 后 cc4101 抢先 fallback ms, NOT counted), 非跳过类真 nv_gw 失败.
  **75s SKIP-CIRCUIT 抬头趋势续确认** (R1895≈0 → R1896=6 → R1898=8 → R1900=5): NVCF 首字节慢信号持续, 本轮从 8 回落到 5, 仍全 FALLBACK-OK + 0 真中断 + NOT counted, 未触发介入条件 #2 (非跳过类). 节奏 ~10-15min 一次, 跨整个窗.
- **bug8**: 实战降级触发 0 (60min log 确认, 根除停巡, 连续 53 轮 0 触发).
- **breaker 30min: OPEN 事件 0** (全 CLOSED):
  - 3 次 NV-MS-FB-SERVED (ms 兜底成功, state=CLOSED): req=65bd1154/64a23524/4c580929 (全 all_keys_exhausted → ms 7853/2020/2025ms).
  - 0 次 NV-ANTH-BREAKER-FAIL (abs_cap 本轮 0, 不触发吸收).
  - **R1889 12:59 OPEN (HALF_OPEN probe 13:03 自回 CLOSED) 连续 8 轮 (R1890/R1891/R1892/R1894/R1895/R1896/R1898/R1900) 无复现** = 单次设计内动作非恶化.
- **env 无漂移** (KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 / TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 / MIN_OUTBOUND=0, 全与 R1850-R1898 一致).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c 宿主/容器一致 (R1839 改后字节码在位).
- nv_gw StartedAt = 2026-07-18T21:26:29Z (= R1836 restart, R1839 至 R1900 未再 restart), 确认跑改后字节码.

## 改动
NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 验证结果
- 链路稳态持续 (SR 94.9% 抖动区间上沿近 53 轮).
- abs_cap 本轮回落到 0 (R1898 1 → R1900 0), ~2-6/h 稳态持续非突发.
- breaker OPEN 0 复现连续 8 轮坐实 R1889 12:59 OPEN 是单次设计内动作.
- 非跳过类真请求失败 0 条 < 4, 0 双路全炸, 0 真中断 (5 条 75s SKIP 全被 ms_gw FALLBACK-OK 兜住, 0 真中断).
- bug8 0 触发 (根除停巡). SSLEOF 持续停 (出口 IP 段已实锤). 500_nv_error absorbed (30min log 仅 1 单点). ttfb 本轮 0 (R1898 单点已退).
- /health ok: {status:ok, proxy_role:passthrough, nv_num_keys:5, nvcf_pexec_models:[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model:dsv4p_nv, port:40006}.
- docker ps 全 Up (nv_gw Up 10h / cc4101 Up 23h / ms_gw Up 2d / logs_db Up 2d), StartedAt 仍 21:26:29Z 0restart.
- 连续 NOP 巡检轮 (R1842-R1900), 链路稳态.

## 决策理由
介入触发四条全不满足:
1. SR 94.9% 仍在 80.9-99 抖动区间常态 (本轮上沿), 非持续跌破 80 退化.
2. 非跳过类真请求失败 (120s 黑洞 / 真正 nv_gw 失败) 0 条 < 4 次/30min 介入线. (5 条 75s SKIP-CIRCUIT 是 cc4101 preempt 设计内 NOT counted, 不算)
3. breaker OPEN 30min=0 (全 CLOSED), R1889 OPEN 连续 8 轮无复现, 未达 >=3 次/30min 介入线.
4. 无新可配置错误分类 (502 全 all_tiers_exhausted/zombie NVCF 上游侧已知; abs_cap 本轮 0 回落; SSLEOF 持续停; 500_nv_error absorbed; ttfb 本轮 0 退).
→ 硬改违反铁律 1 (改前必有数据 + 无据不改).
R1881-R1898 已穷尽 nv_gw 调参旋钮并反证 (TIER_BUDGET 收紧误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST + abs_cap wall-clock 非上游 TIER_BUDGET 可收紧 + UPSTREAM 改不动 NVCF 侧 + 75s SKIP 是 cc4101 75s header/ttfb preempt 非 nv_gw config 可解).

**注 (新观察, 未达介入线)**: 75s SKIP-CIRCUIT fallback 抬头趋势续确认 (R1895≈0 → R1896=6 → R1898=8 → R1900=5), 本轮从 8 回落到 5, NVCF 首字节慢信号持续但非恶化. 全 FALLBACK-OK + 0 真中断 + NOT counted, 未触发介入条件 #2 (非跳过类). 75s 是 cc4101 的 header/ttfb preempt 阈值, 不是 nv_gw 参数, nv_gw 侧无可调旋钮 (UPSTREAM=66s 撑不到 NVCF 拖到 75s+ 才首字节). 下次若持续涨且伴随非跳过类失败增加, 再评估介入 (查上游换出口 IP 段).

## 文案备注
本轮 R1900 commit 单文件 (R1900 本身), 无 peer 误收, 文案准确.

## 给监督者/运维 (沿用 R1881-R1898)
- 处置指向查上游非调参: 换出口 IP 段 (5 mihomo 端口 7894-7899 走非 134.195.101.0/24 解 SSLEOF/500_nv_error/abs_cap 同源) + 联系 NVCF 运维查该 /24 段首字节为何拖到 abs_cap 截断 / 75s+ preempt 及 all_keys_exhausted 短窗集中是否配额调度问题.
- 短期 cycle/breaker/fallback 三层吸收已在位, 兜底 SR 80.9-99 近 53 轮可接受, 0 真中断. breaker OPEN 自恢复机制工作正常, abs_cap 走 nv_breaker 吸收不 OPEN (本轮 abs_cap=0 不触发).

## 下轮 (R1901) 重点
- **75s SKIP-CIRCUIT 是否续抬头** (R1900=5 vs R1898=8): 回落趋势但 NVCF 首字节慢信号持续. 若持续涨到 >=12 且伴随非跳过类失败增加 → 评估介入 (但 75s 是 cc4101 preempt 非 nv_gw 参数, nv_gw 侧无可调旋钮). 当前 5 条 NOT counted 0 真中断, 未达介入线.
- **abs_cap 是否续 0 / 稳态**: 当前 0 (R1898 1 → R1900 0). 若剧增 → 查上游换出口 IP 段.
- **breaker OPEN 是否复现** (连续 8 轮 0): 若 >=3 次/30min 且不自回 CLOSED → 真恶化信号. 单次/0 → 设计内吸收态.
- **SR 是否续在 80.9-99 抖动**: 当前 94.9 上沿, 近 53 轮常态. 持续跌破 80 → 真退化.
- **zombie 是否续复发**: 当前 2 条 (R1898 本轮 0). 批量化 → 查 NVCF content-filter 侧.

**介入触发条件** (任一满足才动手, 否则继续 NOP 巡检):
1. SR 持续跌破 80% (真退化, 非抖动).
2. fallback 中**非跳过类** (120s 黑洞 / FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min.
3. breaker OPEN 频繁复现 (>=3 次/30min) 且不自回 CLOSED.
4. 出现新的可配置错误分类 (非 NVCF 侧已知).
   注: SSLEOFError / abs_cap / 75s SKIP-CIRCUIT 属 NVCF 侧 TLS/wall-clock/header-ttfb 非 nv_gw 配置可修, 不算 nv_gw 可介入分类——若批量化需查 upstream / 换出口 IP 段, 非改 nv_gw 调参旋钮.
若以上都不满足, 继续 NOP 巡检轮.
注: 连续 NOP 巡检 (R1842-R1900) 链路稳态. SR 近轮 96.7/93.65/94.2/88.9/89.7/87.6/90.9/93.0/93.9/94.1/92.2/90.7/94.9 (R1875→R1900), 本轮 94.9 是抖动区间上沿常态, 非趋势性退化, 不主动改.
