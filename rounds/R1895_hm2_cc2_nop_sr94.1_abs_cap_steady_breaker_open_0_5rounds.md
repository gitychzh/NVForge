# R1895 (HM2 cc2) — NOP 巡检 R50

> 模式: nv 直连 (cc4101→nv_gw)。bug8 真降级兜底 R1839 in-vivo 后第 50 轮巡检。
> 本轮 0 改动 0 restart。链路稳态续。

## 数据 (30min 窗, 本 session ~14:22 CST / 06:22 UTC 拉取)

### SR
- 200:48 / 502:3 = **94.1%** (48/51).
- 近轮 96.7/93.65/94.2/88.9/89.7/87.6/90.9/93.0/93.9/94.1 (R1875→R1895).
  **当前 94.1 区间上沿, 抖动区间常态近 50 轮在 80.9-99, 非趋势性退化.** vs R1894 93.9 略升.

### 502 分类 (3 条)
- **stream_absolute_cap 2** + **stream_first_byte_timeout 1**.
- 全 NVCF 上游侧已知分类, 非新可配置分类 (无 gap / 无 deadline / 无 cfilter / 无 zombie / 无 SSLEOF / 无 500_nv_error / 无 conn_RemoteDisconnected).
- vs R1894 (abs_cap 3 + all_tiers_exhausted 1): 本轮 abs_cap 2 略降, all_tiers_exhausted 退, **ttfb 复现 1 单点** (R1894/R1892 均 0). 单点不达批量介入线.

### abs_cap 持续态续确认
- R1891 6h 12 条 → R1892 30min 2 条 → R1894 30min 3 条 → **R1895 30min 2 条**.
- ~2-4/h 区间稳态持续, 非 NVCF 突发, 非 nv_gw config 可解 (handlers.py:1159 绝对 wall-clock, TIER_BUDGET/UPSTREAM 改不动).
- abs_cap 经 R1719/R1771 nv_breaker 吸收: 本轮 14:04 (req=a8f3def5) + 14:12 (req=78b0804f) 两条 NV-ANTH-BREAKER-FAIL
  → state=('CLOSED',2,0)/('CLOSED',1,0), 300s 窗内 < 阈值 5 → 不 OPEN. 机制工作正常.

### tier pexec 30min
- pexec_success 29 (干净基底, 无 ATE).
- pexec_empty_200 2 (NVCF 偶发).
- pexec_timeout 2.
- **pexec_SSLEOFError 30min tier=0 持续停根因闭合** (R1881-R1883 出口 IP 段 134.195.101.0/24 已实锤, 非新复发).
- 无 500_nv_error (R1885 absorbed); 无 conn_RemoteDisconnected; 无 pexec_429 (R1894 的 4 条退, 本轮 0).

### fallback (6 条全 FALLBACK-OK, 0 双路全炸, 0 真中断)
- 5 条全 **75s SKIP-CIRCUIT** (bug3 cc4101 preempt, NOT counted toward circuit):
  - 13:59 req=13a32e93 → 75s SKIP → ms 2678ms.
  - 14:02 req=282947ef → 75s SKIP → ms 2582ms.
  - 14:10 req=6d79ac5b → 75s SKIP → ms 4294ms.
  - 14:13 req=41fb91bc → 75s SKIP → ms 9394ms.
  - 14:17 req=eb708ff8 → 75s SKIP → ms 5877ms.
- abs_cap/all_keys_exhausted 走 NV-MS-FB-SERVED 全 CLOSED (ms 兜底成功):
  - 13:56 req=d3c2c430 → NV-MS-FB-ATTEMPT (all_keys_exhausted) → ms 1812ms.
  - 14:01 req=a8f3def5 → NV-MS-FB-ATTEMPT → ms 2530ms.
  - 14:15 req=fa028cb3 → NV-MS-FB-ATTEMPT → ms 2776ms.
  - 14:19 req=caa8afd5 → NV-MS-FB-ATTEMPT → ms 2403ms.
- **非跳过类 120s 黑洞 0 条** (vs R1894 的 1 条 req=60d20ac7 跨窗, 本轮窗已滑出). < 4 阈值.
- 1 条 `client gone mid-stream after 253341ms Broken pipe` (13:54:47) = 客户端主动断 (cc2 流式读一半断), **非 nv_gw 失败**, 正常行为.
- 0 双路全炸, 0 真中断 (R1889 双路全炸 1 次未复现, 连续 5 轮无).

### breaker 30min: OPEN 事件 0 (全 CLOSED)
- 4 次 NV-MS-FB-SERVED (ms 兜底成功, state=CLOSED): req=d3c2c430/a8f3def5/fa028cb3/caa8afd5.
- 2 次 NV-ANTH-BREAKER-FAIL (abs_cap, req=a8f3def5/78b0804f) → state 全 CLOSED 不 OPEN.
- **R1889 12:59 OPEN (HALF_OPEN probe 13:03 自回 CLOSED) 连续 5 轮 (R1890/R1891/R1892/R1894/R1895) 无复现** = 单次设计内动作非恶化.

### bug8
- 实战降级触发 0 (60min log 确认). 根除停巡 (连续 50 轮 0 触发已够).

### env 无漂移 + 容器状态
- KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 /
  TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 /
  MIN_OUTBOUND=0. 全与 R1850-R1894 一致.
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c 宿主/容器一致.
- /health ok: `{"status":"ok","nv_num_keys":5,"nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"],...}`.
- docker ps 全 Up: nv_gw Up 9h / cc4101 Up 22h / ms_gw Up 2d / logs_db Up 2d.
- StartedAt 仍 2026-07-18T21:26:29Z (R1836 restart, R1839 至 R1895 未再 restart) → 跑 R1839 改后字节码.

## 决策: NOP (不改)
介入触发四条全不满足:
1. SR 94.1% 仍在 80.9-99 抖动区间常态, 非持续跌破 80 退化.
2. 非跳过类真请求失败 (120s 黑洞) 0 条 < 4 次/30min 介入线 (比 R1894 的 1 条还好).
3. breaker OPEN 30min=0 (全 CLOSED), R1889 OPEN 连续 5 轮无复现, 未达 >=3 次/30min 介入线.
4. 无新可配置错误分类 (502 全 abs_cap/ttfb NVCF 上游侧已知; SSLEOF 持续停; 500_nv_error absorbed; pexec_429 本轮 0; zombie 本轮无).
→ 硬改违反铁律 1 (改前必有数据 + 无据不改).

R1881-R1892 已穷尽 nv_gw 调参旋钮并反证 (TIER_BUDGET 收紧误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST + abs_cap wall-clock 非上游 TIER_BUDGET 可收紧 + UPSTREAM 改不动 NVCF 侧).

## 给监督者/运维 (沿用 R1881-R1894)
- 换出口 IP 段: HM2 5 个 mihomo 端口 (7894-7899) 走非 134.195.101.0/24, 解 SSLEOF / 500_nv_error / abs_cap 同源 (NVCF 端对该 /24 段 TLS RST / 500 限流 / 首字节极慢到 abs_cap 截断).
- 联系 NVCF 运维: 查该 /24 段 TLS RST / 500 限流 / 首字节为何拖到 abs_cap 截断, all_keys_exhausted 短窗集中是否配额调度问题.
- 短期 cycle/breaker/fallback 三层吸收已在位兜底, SR 80.9-99 近 50 轮可接受, 0 真中断.
  breaker OPEN 自恢复机制工作正常, abs_cap 走 nv_breaker 吸收不 OPEN.

## 验证结果
链路稳态持续 (SR 94.1% 抖动区间上沿近 50 轮常态) +
abs_cap ~2-4/h 稳态续确认走 nv_breaker 吸收 state CLOSED 不 OPEN 机制工作正常 +
breaker OPEN 0 复现连续 5 轮坐实 R1889 12:59 OPEN 是单次设计内动作 +
非跳过类真失败 0 条 + 0 双路全炸 + 0 真中断 (5 条 75s SKIP 全被 ms_gw 兜住) +
bug8 0 触发 (根除停巡) + SSLEOF 持续停 + 500_nv_error absorbed +
/health ok + docker ps 全 Up + StartedAt 仍 21:26:29Z 0 restart. 连续 NOP 巡检轮 (R1842-R1895), 链路稳态.

## 文案备注
本轮 commit 单文件 (R1895 本身). 防 peer 抢号: git pull 确认 R1895 文件空闲, peer 最新推到 R1894 HM2→HM1 (commit 594084d).
