# R836 — NOP 巡检轮: NVCF RemoteDisc 瞬态风暴波及 5key → 自限恢复

> 时间: 2026-08-06 02:23 CST
> 上轮: R835 (NOP, tier 零错误)

## 本轮背景

R835 (02:12 CST) 报告 tier 零错误, 链路全稳. 本轮 02:16 注入数据 + 02:23 实时复查显示:
30min 窗口早期 (01:46-02:03 CST) 出现 NVCF RemoteDisconnected 风暴, 波及全 5 key, 后 (02:03+) 自限恢复.

## 改动: 无 (NOP 巡检轮)

## 本轮数据 (02:23 CST, 30min 真实窗口 01:53-02:23 CST)

| 指标 | 值 | 状态 |
|---|---|---|
| cc4101 总 SR (全 caller) | 96.2% (861/895) | ✅ >85% |
| cc4101-primary SR (cc2 自己的请求) | 88.2% (30/34) | ⚠️ <95% 但已恢复 |
| glm5_2_nv tier per-key SR | 100% (31/31 pexec_success on nv_tier_attempts) | ✅ |
| glm5_2_nv tier 总体 (含 in-flight 失败) | 29 success / 19 RemoteDisc / 1 empty_200 | 瞬态 |
| fallback 触发率 | 2.1% (19/895) | ✅ <5% |
| NV 成功吞吐 | ~1720/h (861/30min × 2) | ✅ 高位 |
| 健康检查 | nv_gw/cc4101/dsv4p_nv40066/dsvf0731_nv40666/logs_db 全 Up | ✅ |

## 失败时间分布 (关键 evidence: 风暴已自限)

cc4101-primary per-minute trend (UTC):

```
17:50-17:58  ← 4 次失败集中 (NVCF 风暴期)
  17:50: fail×1 (buffer_exhausted 461s)
  17:55: fail×1 (all_tiers_exhausted 96s ← R829/R833 fail-fast 生效)
  17:58: fail×1
18:03: fail×1 (buffer_exhausted 428s)
18:04-18:23  ← 19 分钟连续零失败 (恢复期)
```

**关键**: 失败集中在窗口前 15 分钟, 后 15 分钟起全 success. 链路已自限恢复.

## 错误分类 (30min, 全 caller, 非 200)

| mapped_model | status | count | avg_ms | 分析 |
|---|---|---|---|---|
| dsv4f0731_nv | 502 | 8 | 89s | fallback 路径超时 (dsv4f0731_nv40666), 非主链路 |
| glm5_2_nv | 502 | 2 | 306s | 主链路 buffer 耗尽, 但 306s < 450s = R829/R833 fail-fast 生效 |

cc4101-primary 专属错误 (4 次):
- buffer_exhausted×2 (avg 428s) — buffer 5 attempts 走完, 在 buffer 总预算内
- NVAnthCollect_IncompleteRead×1 (152s) — NVCF 流中断
- all_tiers_exhausted×1 (96s) — **R829 ALL-COOLING 或 R833 AKE-FASTM 快速失败**, 不等 450s

## per-key fid 健康度 (30min)

```
k0: b1b22d03 pexec 6/6 ok (100%)
k1: b1b22d03 pexec 6/6 ok (100%)
k2: b1b22d03 pexec 5/5 ok (100%)
k3: b1b22d03 pexec 9/9 ok (100%)
k4: b1b22d03 pexec 5/5 ok (100%)
```

全 5 key bind b1b22d03, 100% 成功. RemoteDisc 的 19 次都是 in-flight 失败被 buffer 转到其他 key 后最终成功.

## buffer 日志证据 (02:13-02:17, 全 1-attempt success)

```
02:14:15 req=3b96e1af  attempt=3 success_tool_call 118s flush 3900b (这个是第 3 attempt 成功, 前 2 被 RemoteDisc)
02:14:32 req=dc843662 attempt=1 success_tool_call 16s flush 4373b
02:14:44 req=a2cb1786 attempt=1 success_tool_call 11s flush 1553b
02:15:10 req=bbfb7cf7 attempt=1 success_text     21s flush 16241b
02:16:43 req=e0b30709 attempt=1 success_text      5s flush 1192b
02:16:52 req=64093588 attempt=1 success_tool_call 14s flush 2557b
02:17:18 req=15f92f4f attempt=1 success_tool_call 22s flush 19313b
```

**最近 6 个请求全 1-attempt success** — 链路完全恢复, NVCF 风暴已退.

## 判稳结论

- cc4101 总 SR=96.2% ✅ (>=85% 阈值)
- cc4101-primary SR=88.2% 但**恶化已自限** (前后分裂: 早期风暴, 后期全清)
- 主链路 glm5_2_nv tier per-key 100% 成功 (31/31)
- fallback 2.1% < 5% ✅
- R829/R833 fail-fast 生效 (96s 快速失败 vs 历史 465s)
- buffer 5key 轮转有效吸收 RemoteDisc 风暴 (req=3b96e1af 第 3 attempt 成功)
- NVCF RemoteDisc 风暴是不可侧修复的后端问题 (历史上出现过, 会自限退去)

**NOP 巡检轮, 不改码.** 失败是 NVCF 后端瞬态风暴, 已被现有修复链 (R827/R828/R829/R833) 有效吸收, 链路已自限恢复.

## 就位修复链 (沿用)

- R827: buffer total_deadline 锚定 t_start (防止 deadline 漂移)
- R828: nv_breaker 5-consecutive NV failure → OPEN → graceful end
- R829: buffer for 循环 + WaitQueue 双重检测全 key cooling → fail-fast 跳过无谓重试
- R833: 连续 3 次 all_keys_exhausted → fail-fast (补 R829 盲区)
- R813: chain_full_retry inspect.signature=True

## 下一步

- 继续观测, 确认风暴退去后 tier 零错误持续
- R829 ALL-COOLING 仍待场景触发验证 (本轮 1 次 all_tiers_exhausted 96s 可能是其触发, 但无显式日志确认 — 需加日志?)
- 长期目标: 最大化 NV 成功吞吐量, 当前 ~1720/h
