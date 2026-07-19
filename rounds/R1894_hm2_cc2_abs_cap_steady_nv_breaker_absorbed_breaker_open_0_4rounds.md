# R1894 (HM2 cc2) — NOP 巡检 R49: SR 93.9% abs_cap 3条续~2-6/h稳态走nv_breaker吸收state CLOSED不OPEN breaker OPEN0连续4轮无复现

> bug8 降级兜底 in-vivo 后第 49 轮巡检 (R1841→R1894). 0 改动, 0 restart. 巡检轮.
> 上轮: R1892 (7bdc552, NOP 巡检 R48). peer 抢号推 R1893 (4ccc586, HM2→HM1 调 KEY/TIER_COOLDOWN 42→60 只改 HM1 对 HM2 0 影响).
> 本轮从 R1894 起.

## 数据 (30min 窗, 本 session ~06:08 UTC / 14:08 CST 拉取)
- **SR 62/66 = 93.9%** (200:62 / 502:4). 近轮 96.7/93.65/94.2/88.9/89.7/87.6/90.9/93.0/93.9 (R1875→R1894), **当前 93.9 区间上沿, 抖动区间常态近 49 轮在 80.9-99, 非趋势性退化**.
- 502 分类 (4 条): **stream_absolute_cap 3** + all_tiers_exhausted 1.
  **全 NVCF 上游侧已知分类, 非新可配置分类** (无 ttfb / 无 gap / 无 deadline / 无 cfilter / 无 zombie / 无 SSLEOF / 无 500_nv_error).
  vs R1892 (abs_cap 2/zombie 2/all_tiers_exhausted 1): 本轮 abs_cap 3 略增 (仍 NVCF 上游首字节慢被绝对上限截断), 无 zombie (R1892 的 2 退), 无 ttfb.
- abs_cap 持续态续确认 (R1891 6h 12 条 → R1892 30min 2 条 → R1894 30min 3 条):
  ~2-6/h 区间稳态持续, 非 NVCF 突发, 非 nv_gw config 可解 (handlers.py:1159 绝对 wall-clock, TIER_BUDGET/UPSTREAM 改不动).
  abs_cap 经 R1719/R1771 nv_breaker 吸收: 本轮 13:40 (0c91072d) + 13:49 (4f887528) + 14:04 (a8f3def5) 三条 NV-ANTH-BREAKER-FAIL
  → state=('CLOSED',2,0)/('CLOSED',1,0)/('CLOSED',2,0), 300s 窗内 < 阈值 5 → 不 OPEN.
- tier pexec: pexec_success 41 (干净基底, 无 ATE); pexec_empty_200 5 (NVCF 偶发); pexec_429 4 (NVCF 上游 key ratelimit, 非 config 可修); pexec_timeout 1.
  **pexec_SSLEOFError 30min tier=0 持续停根因闭合** (R1881-R1883 出口 IP 段 134.195.101.0/24 已实锤, 非新复发).
  无 500_nv_error (R1885 absorbed, 本轮无复发); 无 conn_RemoteDisconnected; 无 ttfb (R1891 跨窗单点已退).
- fallback 4 条全 FALLBACK-OK, 0 双路全炸, 0 真中断:
  - 13:47 req=68bfe6bd → 75s SKIP-CIRCUIT (bug3 cc4101 preempt, NOT counted) → ms 6249ms.
  - 13:52 req=60d20ac7 → 120s 黑洞 (primary timeout after 120106ms, 非跳过类, 真 nv_gw 失败) → ms 2797ms. (R1892 已记同 req, 跨窗延续同一事件)
  - 13:59 req=13a32e93 → 75s SKIP-CIRCUIT (NOT counted) → ms 2678ms.
  - 14:02 req=282947ef → 75s SKIP-CIRCUIT (NOT counted) → ms 2582ms.
  **非跳过类真请求失败 (120s 黑洞) 1 条 < 4 阈值. 0 双路全炸, 0 真中断**. R1889 双路全炸 1 次未复现 (连续 4 轮无).
- bug8: 实战降级触发 0 (60min log 确认, 根除停巡).
- breaker 30min: **OPEN 事件 0** (全 CLOSED):
  - 3 次 NV-MS-FB-SERVED (ms 兜底成功, state=CLOSED): req=0c91072d/d3c2c430/a8f3def5.
  - 3 次 NV-ANTH-BREAKER-FAIL (abs_cap, req=0c91072d/4f887528/a8f3def5) → state 全 CLOSED 不 OPEN.
  - **R1889 12:59 OPEN (HALF_OPEN probe 13:03 自回 CLOSED) 连续 4 轮 (R1890/R1891/R1892/R1894) 无复现** = 单次设计内动作非恶化.
- env 无漂移 (KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 /
  TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 /
  MIN_OUTBOUND=0, 全与 R1850-R1892 一致).
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c 宿主/容器一致.
- /health ok (passthrough, 5 keys, glm5_2_nv in tiers). docker ps 全 Up (nv_gw Up 9h / cc4101 Up 22h / ms_gw Up 2d / logs_db Up 2d).
- StartedAt 仍 2026-07-18T21:26:29Z = R1836 restart, R1839→R1894 未再 restart, 跑改后字节码.

## 决策: NOP (不改)
介入触发四条全不满足:
1. SR 93.9% 仍在 80.9-99 抖动区间常态, 非持续跌破 80 退化.
2. 非跳过类真请求失败 (120s 黑洞) 1 条 < 4 次/30min 介入线.
3. breaker OPEN 30min=0 (全 CLOSED), R1889 OPEN 连续 4 轮无复现, 未达 >=3 次/30min 介入线.
4. 无新可配置错误分类 (502 全 abs_cap/all_tiers_exhausted NVCF 上游侧已知; SSLEOF 持续停; 500_nv_error absorbed; ttfb 退; zombie 本轮无).
→ 硬改违反铁律 1 (改前必有数据 + 无据不改).
R1881-R1892 已穷尽 nv_gw 调参旋钮并反证 (TIER_BUDGET 收紧误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST + abs_cap wall-clock 非上游 TIER_BUDGET 可收紧 + UPSTREAM 改不动 NVCF 侧).

## 验证结果
链路稳态持续 (SR 93.9% 抖动区间上沿近 49 轮常态) +
abs_cap ~2-6/h 稳态续确认走 R1719/R1771 nv_breaker 吸收 state CLOSED 不 OPEN 机制工作正常 +
breaker OPEN 0 复现连续 4 轮坐实 R1889 12:59 OPEN 是单次设计内动作 +
非跳过类 120s 黑洞 1 条 < 4 + 0 双路全炸 + 0 真中断 (1 条 120s 黑洞被 ms_gw 2797ms 兜住) +
bug8 0 触发 (根除停巡) + SSLEOF 持续停 (出口 IP 段已实锤) + 500_nv_error absorbed +
/health ok + docker ps 全 Up + StartedAt 仍 21:26:29Z 0 restart.
连续 NOP 巡检轮 (R1842-R1894), 链路稳态.

## 给监督者/运维 (沿用 R1881-R1892)
1. 换出口 IP 段: 让 HM2 5 个 mihomo 端口 (7894-7899) 背后走非 134.195.101.0/24, 解 SSLEOF / 500_nv_error / abs_cap 同源 (NVCF 端对该 /24 段 TLS RST / 500 限流 / 首字节极慢到 abs_cap 截断).
2. 联系 NVCF 运维: 查该 /24 段首字节为何拖到 abs_cap 截断策略, 以及 all_keys_exhausted 短窗集中 (全 5 key 同时 ratelimit/耗尽) 是否 NVCF 端配额调度问题.
3. 短期 cycle/breaker/fallback 三层吸收已在位, 兜底 SR 80.9-99 近 49 轮可接受, 0 真中断. breaker OPEN 自恢复机制工作正常, abs_cap 走 nv_breaker 吸收不 OPEN.
4. 维持铁律: 只改 HM2, 改 .py 必须 restart 非 up-d, 不碰 ms_gw, 所有改动写入仓库.

## 下一轮 (R1895) 重点
- abs_cap 是否续 ~2-6/h 稳态: 若剧增 → 查上游换出口 IP 段. 若持续 → 继续观测, nv_breaker 吸收机制兜底.
- breaker OPEN 是否复现 (连续 4 轮 0): 若 >=3 次/30min 且不自回 CLOSED → 真正软挂恶化信号.
- 120s 黑洞 (非跳过类) 是否达 4 条/30min: 当前 1 条 (跨窗延续 60d20ac7) 远低介入线.
- SR 是否续在 80.9-99 抖动: 当前 93.9 上沿, 近 49 轮常态. 持续跌破 80 → 真退化.
- SSLEOF / 500_nv_error / ttfb 是否复发: 当前全停闭合.
