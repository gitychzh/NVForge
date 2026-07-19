# R1902 (HM2 cc2): NOP 巡检 R54 — SR 96.36% (200:53/502:2) zombie 2 全 NVCF 上游侧已知 (abs_cap 0 回落延续) tier pexec_SSLEOFError 1 单点续 (出口 IP 段同源) 75s SKIP-CIRCUIT 7 条全 FALLBACK-OK 0 非跳过类 0 真中断 (NOT counted 未达介入线) breaker OPEN 0 连续 9 轮 env 无漂移 0 restart NOP 无据不改

## 数据采集 (HM2 nv_gw, 2026-07-19 07:26 UTC / 15:26 CST 拉取, 30min 窗)

### nv_requests 30min
```
status | count
-------+------
200    | 53
502    | 2
```
SR = 53/55 = **96.36%** (200:53 / 502:2). 区间常态上沿, 非趋势性退化.
近轮 HM2 cc2 SR 序列: 96.7/93.65/94.2/88.9/89.7/87.6/90.9/93.0/93.9/94.9/96.36 (R1875→R1902), 本轮 96.36 区间上沿.

### 502 分类 (2 条)
```
error_type              | count
------------------------+------
zombie_empty_completion |     2
```
**全 NVCF 上游侧已知分类** (empty200 → zombie). 无 stream_absolute_cap (R1892/R1894 abs_cap 本窗 0 回落延续), 无 ttfb, 无 gap, 无 deadline, 无 cfilter, 无 500_nv_error.
注: abs_cap ↔ zombie 在 NVCF empty200 上游侧来回切, 同源 (NVCF 首字节慢/空), 非 nv_gw config 可解.

### nv_tier_attempts 30min error_type
```
error_type         | count
-------------------+------
pexec_success      |    40
pexec_empty_200    |     4
IntegrateTimeout   |     2
pexec_timeout     |     2
pexec_SSLEOFError |     1
```
- pexec_success 40 干净基底, 无 ATE.
- pexec_empty_200 4 NVCF 偶发.
- IntegrateTimeout 2 + pexec_timeout 2 NVCF 上游侧.
- **pexec_SSLEOFError 1 单点续** (R1899 0 → R1902 1 单点复发, 出口 IP 段 134.195.101.0/24 同源, 非批量化非 nv_gw config 可修).
- 无 500_nv_error (R1885 absorbed, 本轮无复发); 无 conn_RemoteDisconnected.

### fallback cc4101 30min (负向核心指标)
7 条全 FALLBACK-OK, 0 双路全炸, 0 真中断:
- 14:56 req=f96a2336 → FALLBACK-OK 3372ms (前置 NV-MS-FB all_keys_exhausted 兜底, breaker CLOSED).
- 15:03 req=8261eea4 → 75s SKIP-CIRCUIT (cc4101 preempt, NOT counted) → ms 3136ms.
- 15:08 req=c63a5bef → 75s SKIP-CIRCUIT (NOT counted) → ms 5008ms.
- 15:14 req=d238b1ce → 75s SKIP-CIRCUIT (NOT counted) → ms 33587ms.
- 15:17 req=d065c2e7 → 75s SKIP-CIRCUIT (NOT counted) → ms 16054ms.
- 15:21 req=9da45256 → 75s SKIP-CIRCUIT (NOT counted) → ms 4398ms.
- 15:25 req=5a3101d5 → 75s SKIP-CIRCUIT (NOT counted) → ms 2285ms.

**非跳过类真请求失败 0 条** < 4 介入线. **0 双路全炸, 0 真中断**.
75s SKIP-CIRCUIT 抬头趋势续 (R1895≈0 → R1896=6 → R1898=8 → R1900=5 → R1902=7), 全 NOT counted, 0 真中断 — cc4101 bug3 preempt 行为持续, 但 nv_gw 侧无 config 可解 (75s 是 cc4101 chain budget 前置切, 非 nv_gw UPSTREAM/TIER_BUDGET).

### breaker nv_gw 30min
- **OPEN 事件 0** (全 CLOSED). 连续 9 轮 (R1894-R1902) 0 OPEN.
- 3× NV-MS-FB-ATTEMPT → NV-MS-FB-OK → NV-MS-FB-SERVED (ms 兜底 all_keys_exhausted, state=CLOSED):
  - 14:59 req=4c580929 → ms 2025ms, state=CLOSED.
  - 15:17 req=1e043d95 → ms 12693ms, state=CLOSED.
  - 15:20 req=fb3b04d6 → ms 3493ms, state=CLOSED.
- 0× NV-ANTH-BREAKER-FAIL (abs_cap 本窗 0, 无需 breaker 吸收).
R1889 12:59 单次 OPEN 自回 → 连续 9 轮无复现 = 单次设计内动作非源码 bug 坐实.

## bug8 (根除停巡)
NV-TOOLCALL-JSON-DOWNGRADE 60min log = **0**. oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c 宿主/容器一致. 连续 50 轮 0 触发已够, 根除停巡.

## 健康检查
- /health 40006: ok, proxy_role=passthrough, nv_num_keys=5, glm5_2_nv in pexec_models.
- docker ps: nv_gw Up 10h / cc4101 Up 23h / ms_gw Up 2d / logs_db Up 2d 全 Up.
- nv_gw StartedAt = **2026-07-18T21:26:29Z** (= R1836 restart, R1839→R1902 未再 restart) → 跑 R1839 改后字节码.
- env 无漂移: KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 / TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 / MIN_OUTBOUND=0 (全与 R1850-R1900 一致).

## 决策理由: NOP (无据不改)
介入触发四条全不满足:
1. SR 96.36% 仍在 80.9-99 抖动区间常态, 非持续跌破 80 退化. → 不满足.
2. 非跳过类真请求失败 0 条 < 4 次/30min 介入线 (7 条全 75s SKIP-CIRCUIT, NOT counted). → 不满足.
3. breaker OPEN 30min=0 (全 CLOSED), 连续 9 轮无复现, 未达 >=3 次/30min 介入线. → 不满足.
4. 无新可配置错误分类 (502 全 zombie NVCF 上游侧已知; SSLEOF 1 单点续出口 IP 段同源; abs_cap 0; 500_nv_error absorbed; ttfb 0; gap/deadline/cfilter 无). → 不满足.
→ 硬改违反铁律 1 (改前必有数据 + 无据不改).
R1881-R1892 已穷尽 nv_gw 调参旋钮并反证 (TIER_BUDGET 收紧误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST + abs_cap wall-clock 非上游 TIER_BUDGET 可收紧 + UPSTREAM 改不动 NVCF 侧). 75s SKIP 是 cc4101 bug3 preempt, 非 nv_gw 旋钮可解.

## 给监督者/运维 (沿用 R1881-R1900, 不变)
1. **换出口 IP 段**: 让 HM2 5 个 mihomo 端口 (7894-7899) 背后走非 134.195.101.0/24, 解 SSLEOF / 500_nv_error / abs_cap 同源 (NVCF 端对该 /24 段 TLS RST / 500 限流 / 首字节极慢到 abs_cap 截断).
2. **联系 NVCF 运维**: 查该 /24 段 TLS RST / 500 限流 / 首字节为何拖到 abs_cap 截断; all_keys_exhausted 短窗集中 (全 5 key 同时 ratelimit/耗尽) 是否 NVCF 端配额调度问题.
3. **短期 cycle/breaker/fallback 三层吸收已在位**, 兜底 SR 80.9-99 近 50 轮可接受, 0 真中断. breaker OPEN 自恢复机制工作正常, abs_cap/zombie 走 nv_breaker 吸收不 OPEN.
4. 维持铁律: 只改 HM2, 改 .py 必须 restart 非 up-d, 不碰 ms_gw, 所有改动写入仓库.

## 下轮重点 (R1903)
- abs_cap 是否续 0 / zombie 是否续抬头 (本轮 zombie 2, abs_cap 0 ↔ R1892/R1894 abs_cap 2-3/zombie 0-2 在 NVCF empty200 同源来回切): 若 zombie 批量 → 查上游.
- breaker OPEN 是否复现 (连续 9 轮 0): >=3 次/30min 且不自回 → 真恶化.
- 75s SKIP-CIRCUIT 抬头是否续 (R1895≈0→...→R1902=7): 持续抬头但全 NOT counted 0 真中断, 关注是否某窗突破到非跳过类真 nv_gw 失败.
- SR 是否续在 80.9-99 抖动 (当前 96.36 上沿).
- SSLEOF / 500_nv_error / ttfb 是否批量化复发 (当前 SSLEOF 1 单点, 余停).
