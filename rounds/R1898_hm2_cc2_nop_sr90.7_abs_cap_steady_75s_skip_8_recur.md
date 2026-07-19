# R1898 (HM2 cc2) — NOP 巡检 R52

> 时间: 2026-07-19 ~14:54 CST / 06:54 UTC 拉取. git pull 已含 peer R1897(HM2→HM1 TIER_BUDGET 178→176)+上一session R1896 (commit b37fab8, 巡检 R51).
> 本轮做 **R1898** (R1897+1, 防 peer 抢号, git pull 已确认 697a40e 为最新).

## 模式
nv 直连 (cc4101→nv_gw), R1839 bug8 真降级兜底 in-vivo 生效, R1841-R1896 连续 51 轮巡检确认.
本轮 R1898 = 第 52 轮巡检.

## 数据 (30min 窗 + 10min burst, 14:24-14:54 CST)
- **SR 39/43 = 90.7%** (200:39 / 502:4). 10min burst 12/13=92.3%.
  近轮 SR: 96.7/93.65/94.2/88.9/89.7/87.6/90.9/93.0/93.9/94.1/92.2/90.7 (R1875→R1898), **当前 90.7 区间中段, 抖动区间常态近 52 轮在 80.9-99**, 非趋势性退化.
- **502 分类 (4 条)**:
  - stream_absolute_cap **1** (14:27:59 req=7df071ad) — NVCF 上游首字节慢被绝对上限截断, 已知, 非配置可解 (handlers.py:1159 绝对 wall-clock).
  - all_tiers_exhausted **2** (14:31/14:35/14:48/14:52 NV-MS-FB-ATTEMPT, req=fe540a01/c998d169/65bd1154/64a23524) — NVCF 上游全 key 耗尽, 已知.
  - stream_first_byte_timeout **1** (ttfb 单点复发) — R1896 单点复发续, 非批量.
  - 无 zombie / 无 gap / 无 deadline / 无 cfilter / 无 SSLEOF / 无 500_nv_error.
- **tier pexec**:
  - pexec_success **24** (干净基底).
  - pexec_empty_200 **4** (NVCF 偶发).
  - pexec_timeout **3** (↑ vs R1896=2; NVCF 上游慢, 非配置可修, 仍低量).
  - **pexec_SSLEOFError 30min tier=0 持续停根因闭合** (出口 IP 段 134.195.101.0/24 已实锤, 非新复发).
  - 无 pexec_429 (本轮 0; NVCF key ratelimit 波动). 无 conn_RemoteDisconnected. 无 500_nv_error.
- **abs_cap 持续态续确认** (R1891 6h 12 条 → R1892 30min 2 条 → R1894 30min 3 条 → R1895 30min 2 条 → R1896 30min 2 条 → R1898 30min 1 条): ~2-4/h 区间稳态持续 (本轮回落到 1), 非 NVCF 突发, 非 nv_gw config 可解.
  abs_cap 经 R1719/R1771 nv_breaker 吸收: 14:27 (7df071ad) 一条 NV-ANTH-BREAKER-FAIL → state=('CLOSED',1,0), 300s 窗内 < 阈值 5 → 不 OPEN.
- **fallback 8 条全 FALLBACK-OK, 全 75s SKIP-CIRCUIT (NOT counted), 0 双路全炸, 0 真中断**:
  - 14:25 req=fb4f1562 → 75s SKIP-CIRCUIT → ms 兜住.
  - 14:26 req=3375814e → 75s SKIP-CIRCUIT → ms 3647ms.
  - 14:28 req=6530dab9 → 75s SKIP-CIRCUIT → ms 2082ms.
  - 14:32 req=72151c8f → 75s SKIP-CIRCUIT → ms 27518ms.
  - 14:39 req=1bd7384e → 75s SKIP-CIRCUIT → ms 3814ms.
  - 14:41 req=ca6918d2 → 75s SKIP-CIRCUIT → ms 13358ms.
  - 14:45 req=54024a66 → 75s SKIP-CIRCUIT → ms 25780ms.
  - 14:49 req=ceecc5f5 → 75s SKIP-CIRCUIT → ms 10025ms.
  **非跳过类真请求失败 (120s 黑洞 / 真正 nv_gw 失败) 0 条 < 4 阈值**.
  全 8 条 75s SKIP-CIRCUIT 是 bug3 cc4101 preempt 设计内行为 (header/ttfb 75s 后 cc4101 抢先 fallback ms, NOT counted), 非跳过类真 nv_gw 失败.
  **新观察: 75s SKIP-CIRCUIT 涨到 8 (vs R1896=6, R1895≈0)**, NVCF 首字节慢信号在抬头, 但仍全 FALLBACK-OK 0 真中断, 未达介入线.
- **bug8**: 实战降级触发 0 (60min log 确认, 根除停巡, 连续 52 轮 0 触发).
- **breaker 30min: OPEN 事件 0** (全 CLOSED):
  - 4 次 NV-MS-FB-SERVED (ms 兜底成功, state=CLOSED): req=fe540a01/c998d169/65bd1154/64a23524.
  - 1 次 NV-ANTH-BREAKER-FAIL (abs_cap, req=7df071ad) → state CLOSED 不 OPEN.
  - **R1889 12:59 OPEN (HALF_OPEN probe 13:03 自回 CLOSED) 连续 7 轮 (R1890/R1891/R1892/R1894/R1895/R1896/R1898) 无复现** = 单次设计内动作非恶化.
- **env 无漂移** (KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 / TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 / MIN_OUTBOUND=0, 全与 R1850-R1896 一致).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c 宿主/容器一致 (R1839 改后字节码在位).
- nv_gw StartedAt = 2026-07-18T21:26:29Z (= R1836 restart, R1839 至 R1898 未再 restart), 确认跑改后字节码.

## 改动
NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 验证结果
- 链路稳态持续 (SR 90.7% 抖动区间常态近 52 轮).
- abs_cap ~2-4/h 稳态续确认走 R1719/R1771 nv_breaker 吸收 state CLOSED 不 OPEN 机制工作正常.
- breaker OPEN 0 复现连续 7 轮坐实 R1889 12:59 OPEN 是单次设计内动作.
- 非跳过类真请求失败 0 条 < 4, 0 双路全炸, 0 真中断 (8 条 75s SKIP 全被 ms_gw FALLBACK-OK 兜住, 0 真中断).
- bug8 0 触发 (根除停巡). SSLEOF 持续停 (出口 IP 段已实锤). 500_nv_error absorbed. ttfb 本轮单点复发 (非批量未达介入线).
- /health ok: {status:ok, nv_num_keys:5, nvcf_pexec_models:[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model:dsv4p_nv, port:40006}.
- docker ps 全 Up (nv_gw Up 9h / cc4101 Up 23h / ms_gw Up 2d / logs_db Up 2d), StartedAt 仍 21:26:29Z 0restart.
- 连续 NOP 巡检轮 (R1842-R1898), 链路稳态.

## 决策理由
介入触发四条全不满足:
1. SR 90.7% 仍在 80.9-99 抖动区间常态, 非持续跌破 80 退化.
2. 非跳过类真请求失败 (120s 黑洞 / 真正 nv_gw 失败) 0 条 < 4 次/30min 介入线. (8 条 75s SKIP-CIRCUIT 是 cc4101 preempt 设计内 NOT counted, 不算)
3. breaker OPEN 30min=0 (全 CLOSED), R1889 OPEN 连续 7 轮无复现, 未达 >=3 次/30min 介入线.
4. 无新可配置错误分类 (502 全 abs_cap/all_tiers_exhausted/ttfb NVCF 上游侧已知; SSLEOF 持续停; 500_nv_error absorbed; zombie 本轮无).
→ 硬改违反铁律 1 (改前必有数据 + 无据不改).
R1881-R1896 已穷尽 nv_gw 调参旋钮并反证 (TIER_BUDGET 收紧误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST + abs_cap wall-clock 非上游 TIER_BUDGET 可收紧 + UPSTREAM 改不动 NVCF 侧).

**注 (新观察, 未达介入线)**: 75s SKIP-CIRCUIT fallback 涨到 8 条/30min (R1895≈0 → R1896=6 → R1898=8), NVCF 首字节慢信号缓慢抬头. 但仍全 FALLBACK-OK + 0 真中断 + NOT counted, 未触发介入条件 #2 (非跳过类). 下次若持续涨且伴随非跳过类失败增加, 再评估介入.

## 文案备注
本轮 R1898 commit 单文件 (R1898 本身), 无 peer 误收, 文案准确.

## 给监督者/运维 (沿用 R1881-R1896)
- 处置指向查上游非调参: 换出口 IP 段 (5 mihomo 端口 7894-7899 走非 134.195.101.0/24 解 SSLEOF/500_nv_error/abs_cap 同源) + 联系 NVCF 运维查该 /24 段首字节为何拖到 abs_cap 截断及 all_keys_exhausted 短窗集中是否配额调度问题.
- 短期 cycle/breaker/fallback 三层吸收已在位, 兜底 SR 80.9-99 近 52 轮可接受, 0 真中断. breaker OPEN 自恢复机制工作正常, abs_cap 走 nv_breaker 吸收不 OPEN.

## 下轮 (R1899) 重点
- **75s SKIP-CIRCUIT 是否续涨** (8 vs R1896=6): 若持续涨到 >=12 且伴随非跳过类失败增加 → 评估介入 (查 cc4101 75s header/ttfb preempt 阈值是否需调, 但那是 cc4101 不是 nv_gw). 当前 8 条 NOT counted 0 真中断, 未达介入线.
- **abs_cap 是否续 ~2-4/h 稳态**: 当前回落到 1/30min. 若剧增 → 查上游换出口 IP 段.
- **breaker OPEN 是否复现** (连续 7 轮 0): >=3 次/30min 且不自回 → 真恶化.
- **SR 是否续在 80.9-99 抖动**: 当前 90.7 中段. 持续跌破 80 → 真退化.
- **SSLEOF / 500_nv_error / ttfb**: 当前 SSLEOF/500 停, ttfb 单点. 复发批量化 → 查 upstream.
