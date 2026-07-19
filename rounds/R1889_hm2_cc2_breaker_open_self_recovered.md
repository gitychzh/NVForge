# R1889 (HM2 cc2): NOP 巡检 — breaker 短暂OPEN自恢复 双路全炸1次仍0真中断

## 改前数据 (30min 窗, 本 session ~13:10 CST / 05:10 UTC 拉取)

### nv_requests 30min
| status | count |
|--------|-------|
| 200 | 95 |
| 502 | 11 |

**SR = 95/106 = 89.7%** (与 R1887 89.7% 同, 抖动区间下沿常态近 40 轮在 80.9-99 区间).

### 502 分类 (status!=200)
| error_type | count |
|-----------|-------|
| all_tiers_exhausted | 8 |
| zombie_empty_completion | 3 |

**全 NVCF 上游 key 耗尽兜底 + zombie, 与 R1885-R1887 同构, 非新可配置分类**.
(无 stream_absolute_cap / 无 stream_first_byte_timeout / 无 stream_no_content_gap / 无 deadline / 无 cfilter).

### tier_attempts 30min
| error_type | count |
|-----------|-------|
| pexec_success | 83 |
| pexec_429 | 6 |
| 500_nv_error | 1 |
| pexec_SSLEOFError | 1 |
| pexec_empty_200 | 1 |

- pexec_success 83 干净基底, 无 ATE.
- **pexec_SSLEOFError 30min=1, 120min=1** (单点 04:53 UTC), 持续停根因闭合 (R1881-R1883 出口 IP 段 134.195.101.0/24 已实锤, 非新复发).
- 500_nv_error 1 = 已确认的"被 NV-CYCLE 吸收的非新分类" (R1885 闭合), 不是新错误分类.
- pexec_429 6 = NVCF 上游 key ratelimit, 非 nv_gw config 可修.

### fallback (cc4101 log 30min): 5 条 FALLBACK-OK + 1 条双路全失败
- 12:41 req=ab9d40a7 → 75s SKIP-CIRCUIT (bug3 抢断 cc4101 preempt) → FALLBACK-OK ms 3252ms.
- 12:44 req=c4cef6c0 → 75s SKIP-CIRCUIT → FALLBACK-OK ms 27293ms (27s 单点慢尖峰).
- **12:49 req=468be9f3 → 120s 黑洞 (nv 120042ms, 非跳过类) → FALLBACK-OK ms 3344ms**. 跨窗复现 (R1887 也记 468be9f3).
- **12:58 req=96016e47 → 双路全失败: nv 75s SKIP + ms 503 (FALLBACK-FAIL) → CC outer retry 兜住**. 1 次"体验中断"信号, 单点.
- 13:00 req=1765d8d7 → 75s SKIP-CIRCUIT → FALLBACK-OK ms 3158ms.
- **13:05 req=a18c8283 → 120s 黑洞 (nv 120107ms, 非跳过类) → FALLBACK-OK ms 4379ms**.

**非跳过类真请求失败 (120s 黑洞) 本窗 2 条 (468be9f3 + a18c8283) < 4 阈值. 0 真中断 (96016e47 被 CC outer retry 兜住).**

### breaker 30min: 1 次 OPEN 自恢复 (本轮新事件 vs R1887 全 CLOSED)
完整轨迹:
- 12:39 / 12:45 / 12:49 / 12:53 — 4× NV-MS-FB-SERVED (ms 兜底成功, breaker recorded failure state=CLOSED).
- **12:59:02.4 NV-MS-FB-FAIL req=c377ae47 breaker=OPEN** (state 字段首次变 OPEN, 因 12:58-12:59 all_keys_exhausted 短窗集中爆发: d735a80b/575bee05/8e82a836/c377ae47 连续 4 req 全 all_keys_exhausted, ms_gw 又返 503).
- **12:59:02.8 NV-MS-FB-BREAKER-OPEN req=7a75d5b2 state=('OPEN', 5, 29)** — breaker 跳过 nv chain 直接走 ms, ms 也 503 (15ms) → **BREAKER-OPEN-MSFAIL falling through to nv chain (HALF_OPEN probe)**.
- 12:59:08-12:59:14 ms_gw 仍 503 (72848ms / 45559ms 慢失败, req=8cc73bd9/8e82a836).
- **13:03:04.9 NV-MS-FB-SERVED req=dd2f8544 breaker state=CLOSED** — HALF_OPEN probe nv chain 恢复成功, breaker 自回 CLOSED.
- 13:03:33 NV-MS-FB-SERVED req=1264ccf2 state=CLOSED — 稳态恢复.

**结论**: breaker OPEN 是设计内动作 (R1839 "宁可 OPEN 走 ms 也不死循环"), 发生在 12:59 all_keys_exhausted 短窗集中 + ms_gw 也被拖垮的"双路全炸"尖峰; **HALF_OPEN probe 机制工作正常, 13:03 自回 CLOSED**, 不是源码 bug. 与 R1879 关切的"nv_breaker state 漂移"一致 (state 第二字段 R1879=2 → 本轮 OPEN 时=5 → 自回 CLOSED, 在设计内吸收态).

### env 无漂移 (与 R1850-R1887 全一致)
```
KEY_AUTHFAIL_COOLDOWN_S=60
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_FAIL_N=1
TIER_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=180
UPSTREAM_TIMEOUT=66
```

### oai_to_anth.py md5 = 4983bcec (宿主/容器一致, bug8 兜底在位 0 触发, 根除停巡).

## 改了什么
**NOP (不改). 无 compose env / 无 .py 改动. 0 restart.**

## 决策理由
介入触发四条全不满足"硬改"条件:
1. **SR 连破但 R1881-R1883 已穷尽 nv_gw 调参旋钮并反证**: TIER_BUDGET 收紧到 90 误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST + UPSTREAM 改不动 NVCF 侧 abs_cap/zombie. 处置指向查上游非调参. (STATE R1887 已明确.)
2. **非跳过类真请求失败 (120s 黑洞) 2 条 < 4 阈值**.
3. **breaker 短暂 OPEN 但已自回 CLOSED** (HALF_OPEN probe 工作): OPEN 是设计内动作非源码 bug, "出现 OPEN"≠"恶化"——真正该看的是 OPEN 是否频繁复现 (本轮仅 1 次 12:59 尖峰, 13:03 即自回). 真正该盯的是 OPEN 频率, 而非 state 数字.
4. **无新可配置错误分类**: 502 全 all_tiers_exhausted (NVCF 上游 key 耗尽) + zombie (NVCF content-filter), SSLEOF 已停根因闭合, 500_nv_error 已确认 absorbed. 全是 NVCF 上游侧已知分类.

**硬改违反铁律 1 (改前必有数据 + 无据不改).**

## 验证结果
- 链路稳态持续 (SR 89.7% 抖动区间常态, 近 40 轮在 80.9-99 区间).
- **breaker OPEN 自恢复机制工作正常** (12:59 OPEN → 13:03 HALF_OPEN probe → CLOSED), 设计内动作非 bug.
- 双路全炸 1 次 (12:58 req=96016e47 nv 75s + ms 503), CC outer retry 兜住, 0 真中断.
- 120s 黑洞 2 条 (468be9f3 + a18c8283) 非跳过类 < 4 阈值.
- bug8 0 触发 (根除停巡).
- SSLEOF 30/120min=1 持续停根因闭合 (出口 IP 段 134.195.101.0/24 已实锤).
- env 无漂移, /health ok, docker ps 全 Up (nv_gw Up 8h / cc4101 Up 21h / ms_gw Up 2d / logs_db Up 2d).
- StartedAt 仍 2026-07-18T21:26:29Z 确认跑 R1839 改后字节码. 0 restart.
- 连续 NOP 巡检轮 (R1842-R1889), 链路稳态.

## 本轮价值
1. **如实记录 breaker 短暂 OPEN + 自恢复** (R1887 写"全 CLOSED 未 OPEN", 本轮 12:59 实有 1 次 OPEN 尖峰, 但 HALF_OPEN probe 自回 CLOSED, 不掩盖).
2. **坐实"双路全炸"窗口存在** (12:58 nv 75s + ms 503), 但 CC outer retry 兜住 0 真中断 — 这是当前唯一真正的"用户体验风险点", 单点非趋势.
3. 接续 R1881-R1887 结论: nv_gw 调参旋钮已穷尽, 处置指向查上游.

## 给监督者 / 运维 (沿用 R1881-R1887, 本轮新增 breaker OPEN 证据)
1. **换出口 IP 段**: 让 HM2 5 个 mihomo 端口 (7894-7899) 背后走非 134.195.101.0/24, 解 SSLEOF / 500_nv_error / all_keys_exhausted 同源 (NVCF 端对该 /24 段 TLS RST / 500 限流, 23:00+03:00 UTC 密集可能夜间维护窗口).
2. **联系 NVCF 运维**: 查该 /24 段 TLS RST / 500 限流策略, 以及 12:59 all_keys_exhausted 短窗集中 (全 5 key 同时 ratelimit/耗尽) 是否 NVCF 端配额调度问题.
3. **短期 cycle/breaker/fallback 三层吸收已在位**, 兜底 SR 80.9-99 近 40 轮可接受, 0 真中断. breaker OPEN 自恢复机制工作正常.

## 下轮 R1890 重点
1. **breaker OPEN 是否复现 / 频率**: 本轮 1 次 (12:59) 自回 CLOSED. 若续频繁 OPEN (>=3 次/30min) 且不自回 → 真正的 nv_gw 软挂恶化信号 (届时需查 breaker 阈值 + nv chain 本身健康, 但仍非单纯调参).
2. **"双路全炸"窗口是否复现**: 12:58 req=96016e47 是单点. 若续复现 (>=3 次/30min) → 用户体验真退化, 需查 ms_gw 为何也 503 (但 ms_gw 是热备不改源码, 只能查 upstream).
3. **120s 黑洞是否达 4 条/30min 介入线** (当前 2 条).
4. **SR 是否续在 89-94 抖动** (近 40 轮常态, 非趋势).
5. **SSLEOF / 500_nv_error 是否复发** (当前停根因闭合).

## 文案备注
本轮 commit 单文件 (R1889 本身), 无 peer 误收. peer 抢号区间 (R1888 已是 peer HM2→HM1), 本轮 R1889 防冲突已确认.
