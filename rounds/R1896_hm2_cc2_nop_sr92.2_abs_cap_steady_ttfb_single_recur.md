# R1896 (HM2 cc2) — NOP 巡检 R51

> 时间: 2026-07-19 ~14:36 CST / 06:36 UTC 拉取. git pull 已含 peer R1894(HM2→HM1)+上一session R1895.
> 本轮基线: STATE.md 旧版停在 R1894, git 已 ahead 到 R1895 (commit d6ee6c8, 巡检 R50).
> 本轮做 **R1896** (R1895+1, 防 peer 抢号, git pull 已确认 d6ee6c8 为最新).

## 模式
nv 直连 (cc4101→nv_gw), R1839 bug8 真降级兜底 in-vivo 生效, R1841-R1895 连续 50 轮巡检确认.
本轮 R1896 = 第 51 轮巡检.

## 数据 (30min 窗 + 10min burst)
- **SR 47/51 = 92.2%** (200:47 / 502:4). 10min burst 15/16=93.75%.
  近轮 SR: 96.7/93.65/94.2/88.9/89.7/87.6/90.9/93.0/93.9/94.1/92.2 (R1875→R1896), **当前 92.2 区间中段, 抖动区间常态近 51 轮在 80.9-99**, 非趋势性退化.
- **502 分类 (4 条)**:
  - stream_absolute_cap **2** (06:12:26 req=78b0804f / 06:27:59 req=7df071ad) — NVCF 上游首字节慢被绝对上限截断, 已知, 非配置可解 (handlers.py:1159 绝对 wall-clock).
  - all_tiers_exhausted **1** (06:27:19) — NVCF 上游全 key 耗尽, 已知.
  - **stream_first_byte_timeout 1 (ttfb 复发单点)** — R1894/R1895 0, 本轮单点复发 (非批量, R1891 跨窗单点已退, 本轮再单点).
  - 无 zombie / 无 gap / 无 deadline / 无 cfilter / 无 SSLEOF / 无 500_nv_error.
- **tier pexec**:
  - pexec_success **32** (干净基底).
  - pexec_empty_200 **3** (NVCF 偶发).
  - pexec_timeout **2** (↑ vs R1895=1; NVCF 上游慢, 非配置可修, 仍低量).
  - **pexec_SSLEOFError 30min tier=0 持续停根因闭合** (出口 IP 段 134.195.101.0/24 已实锤, 非新复发).
  - 无 pexec_429 (R1895=4 已退, 本轮 0; NVCF key ratelimit 波动). 无 conn_RemoteDisconnected. 无 500_nv_error.
- **abs_cap 持续态续确认** (R1891 6h 12 条 → R1892 30min 2 条 → R1894 30min 3 条 → R1895 30min 2 条 → R1896 30min 2 条): ~2-4/h 区间稳态持续, 非 NVCF 突发, 非 nv_gw config 可解 (handlers.py:1159 绝对 wall-clock, TIER_BUDGET/UPSTREAM 改不动).
  abs_cap 经 R1719/R1771 nv_breaker 吸收: 14:12 (78b0804f) + 14:27 (7df071ad) 两条 NV-ANTH-BREAKER-FAIL
  → state=('CLOSED',1,0) ×2, 300s 窗内 < 阈值 5 → 不 OPEN.
- **fallback 7 条全 FALLBACK-OK, 0 双路全炸, 0 真中断**:
  - 14:10 req=6d79ac5b → (无 PRIMARY-FAIL 日志, ms 4294ms).
  - 14:13 req=41fb91bc → 75s SKIP-CIRCUIT (bug3 cc4101 preempt, NOT counted) → ms 9394ms.
  - 14:17 req=eb708ff8 → 75s SKIP-CIRCUIT (NOT counted) → ms 5877ms.
  - 14:25 req=fb4f1562 → 75s SKIP-CIRCUIT (NOT counted) → ms 4176ms.
  - 14:26 req=3375814e → 75s SKIP-CIRCUIT (NOT counted) → ms 3647ms.
  - 14:28 req=6530dab9 → 75s SKIP-CIRCUIT (NOT counted) → ms 2082ms.
  - 14:32 req=72151c8f → 75s SKIP-CIRCUIT (NOT counted) → ms 27518ms.
  **非跳过类真请求失败 (120s 黑洞 / 真正 nv_gw 失败) 0 条 < 4 阈值**.
  75s SKIP-CIRCUIT 集中 14:13-14:32 (6 条) 是 bug3 cc4101 preempt 设计内行为 (header/ttfb 75s 后 cc4101 抢先 fallback ms), 非跳过类真 nv_gw 失败.
- **bug8**: 实战降级触发 0 (60min log 确认, 根除停巡, 连续 51 轮 0 触发).
- **breaker 30min: OPEN 事件 0** (全 CLOSED):
  - 3 次 NV-MS-FB-SERVED (ms 兜底成功, state=CLOSED): req=fa028cb3/caa8afd5/fe540a01/c998d169 (4 次, 全 CLOSED).
  - 2 次 NV-ANTH-BREAKER-FAIL (abs_cap, req=78b0804f/7df071ad) → state 全 CLOSED 不 OPEN.
  - **R1889 12:59 OPEN (HALF_OPEN probe 13:03 自回 CLOSED) 连续 6 轮 (R1890/R1891/R1892/R1894/R1895/R1896) 无复现** = 单次设计内动作非恶化.
- **env 无漂移** (KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 / TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 / MIN_OUTBOUND=0, 全与 R1850-R1895 一致).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c 宿主/容器一致 (R1839 改后字节码在位).
- nv_gw StartedAt = 2026-07-18T21:26:29Z (= R1836 restart, R1839 至 R1896 未再 restart), 确认跑改后字节码.

## 改动
NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 验证结果
- 链路稳态持续 (SR 92.2% 抖动区间常态近 51 轮).
- abs_cap ~2-4/h 稳态续确认走 R1719/R1771 nv_breaker 吸收 state CLOSED 不 OPEN 机制工作正常.
- breaker OPEN 0 复现连续 6 轮坐实 R1889 12:59 OPEN 是单次设计内动作.
- 非跳过类真请求失败 0 条 < 4, 0 双路全炸, 0 真中断 (7 条 75s SKIP 全被 ms_gw FALLBACK-OK 兜住, 0 真中断).
- bug8 0 触发 (根除停巡). SSLEOF 持续停 (出口 IP 段已实锤). 500_nv_error absorbed. ttfb 本轮单点复发 (R1894/R1895 0 → 本轮 1, 非批量未达介入线).
- /health ok: {status:ok, nv_num_keys:5, pexec_models:[kimi_nv,dsv4p_nv,glm5_2_nv], default:dsv4p_nv, port:40006}.
- docker ps 全 Up (nv_gw Up 9h / cc4101 Up 23h / ms_gw Up 2d / logs_db Up 2d), StartedAt 仍 21:26:29Z 0restart.
- 连续 NOP 巡检轮 (R1842-R1896), 链路稳态.

## 决策理由
介入触发四条全不满足:
1. SR 92.2% 仍在 80.9-99 抖动区间常态, 非持续跌破 80 退化.
2. 非跳过类真请求失败 (120s 黑洞 / 真正 nv_gw 失败) 0 条 < 4 次/30min 介入线. (7 条 75s SKIP 全 bug3 cc4101 preempt NOT counted).
3. breaker OPEN 30min=0 (全 CLOSED), R1889 OPEN 连续 6 轮无复现, 未达 >=3 次/30min 介入线.
4. 无新可配置错误分类 (502 全 abs_cap/all_tiers_exhausted NVCF 上游侧已知 + ttfb 单点复发非批量; SSLEOF 持续停; 500_nv_error absorbed; zombie 本轮无).
→ 硬改违反铁律 1 (改前必有数据 + 无据不改).
R1881-R1895 已穷尽 nv_gw 调参旋钮并反证 (TIER_BUDGET 收紧误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST + abs_cap wall-clock 非上游 TIER_BUDGET 可收紧 + UPSTREAM 改不动 NVCF 侧).

## 给监督者/运维 (沿用 R1881-R1895)
- **换出口 IP 段**: HM2 5 个 mihomo 端口 (7894-7899) 走非 134.195.101.0/24, 解 SSLEOF / 500_nv_error / abs_cap 同源 (NVCF 端对该 /24 段 TLS RST / 500 限流 / 首字节极慢到 abs_cap 截断).
- **联系 NVCF 运维**: 查该 /24 段 TLS RST / 500 限流 / 首字节为何拖到 abs_cap 截断, 及 all_keys_exhausted 短窗集中是否 NVCF 端配额调度问题.
- 短期 cycle/breaker/fallback 三层吸收已在位, 兜底 SR 80.9-99 近 51 轮可接受, 0 真中断. breaker OPEN 自恢复机制工作正常, abs_cap 走 nv_breaker 吸收不 OPEN.

## 下轮 (R1897) 重点
- abs_cap 是否续 ~2-4/h 稳态 (剧增 → 查上游换出口 IP 段).
- breaker OPEN 是否复现 (连续 6 轮 0; >=3 次/30min 且不自回 → 真恶化).
- ttfb 单点复发是否批量化 (本轮 1, R1894/R1895 0; 持续批量 → 查 upstream).
- pexec_timeout 是否续增 (本轮 2 vs R1895 1; 持续 → 观测).
- 120s 黑洞达 4 条介入线 (当前 0).
- SR 续 80.9-99 抖动 (当前 92.2 中段).
- SSLEOF / 500_nv_error 是否复发 (当前全停闭合).
