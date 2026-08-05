# R837 — NOP 巡检轮: NVCF RemoteDisc 瞬态风暴持续自限, buffer 5key 轮转全吸收

> 时间: 2026-08-06 02:27 CST (30min 真实窗口 01:57-02:27 CST)
> 上轮: R836 (NOP, 同样 RemoteDisc 风暴自限恢复)
> 容器: nv_gw Up 2h, cc4101 Up 3h, dsv4p_nv40066 Up 30h, dsvf0731_nv40666 Up 21h, logs_db Up 6d

## 本轮改动: 无 (NOP 巡检轮)

## 本轮数据 (02:27 CST, 30min 真实窗口 01:57-02:27 CST)

| 指标 | 值 | 评估 |
|---|---|---|
| glm5_2_nv 主链路 SR | 97.1% (34/35) | ✅ ≥85% |
| cc4101-primary per-call SR | 92.3% (36/39) | ✅ ≥90% |
| cc4101-primary 502 avg | 355s (3 次) | ⚠️ 但 R829/R833 fail-fast 生效 |
| fallback 触发率 | 3.3% (2/60) | ✅ <5% |
| glm5_2_nv tier pexec_success | 34 (全 5 key) | ✅ buffer 5key 轮转正常 |
| tier RemoteDisc (in-flight 失败) | 21 (k0:4 k1:2 k2:6 k3:6 k4:4) | ⚠️ NVCF 风暴波及全 5key |
| dsv4f0731_nv fallback 路径 SR | 64% (16/25) | 非主链路, hermes caller |
| all_tiers_exhausted avg | 88s (×7) | ✅ R829/R833 fail-fast (vs 历史 465s) |

## 错误分类 (30min cc4101-primary)

| error_type | count | avg_ms | 分析 |
|---|---|---|---|
| all_tiers_exhausted | 7 | 88179 | R829/R833 fail-fast 生效, 88s << 465s |
| buffer_exhausted | 2 | 457035 | buffer 450s 耗尽 (NVCF 持续故障期) |
| NVAnthCollect_IncompleteRead | 1 | 151818 | 瞬态 mid-stream 断流 |

cc4101-primary 3 个 502: buffer_exhausted×2 + IncompleteRead×1. 主链路偶发被 NVCF 持续故障耗尽 buffer.

## per-key fid 健康 (30min tier)

```
k0: b1b22d03  4 pexec_success + 4 RemoteDisc (50%)
k1: b1b22d03  8 pexec_success + 1 RemoteDisc + 1 empty_200 (80%)
k2: b1b22d03  5 pexec_success + 6 RemoteDisc (45%)  ← 风暴中心
k3: b1b22d03 11 pexec_success + 6 RemoteDisc (65%)
k4: b1b22d03  6 pexec_success + 4 RemoteDisc (60%)
```

全 5 key 都有 pexec_success (无全挂), RemoteDisc 瞬态分散全 5 key — NVCF 后端不可侧修复, buffer 5key 轮转设计目的充分体现.

## buffer 自愈活样本 (02:26-02:28)

最近 5 个 cc4101-primary 请求全 1-attempt success:
- req=f922f9e6: 1 attempt, 21.8s, flush 18997b, verdict=success_text
- req=6d20f9ad: 1 attempt, 1.9s, flush 1192b, verdict=success_text (k3 轮转)
- req=93b79bd1: 1 attempt, 24.7s, flush 2584b, verdict=success_tool_call (k4 轮转)
- req=19dfe58a: 1 attempt, 11.2s, flush 33079b, verdict=success_tool_call (k5 轮转)
- req=6f1c4011: 1 attempt, 3.5s, flush 4946b, verdict=success_tool_call (k1 轮转)

每个请求 `_KEY_ROTATION` 轮转 key, 零故障, NVCF 风暴已自限恢复.

## 就位修复链 (沿用, R827+R828+R829+R833+R813)

- R827: buffer total_deadline 锚定 t_start (防止 deadline 漂移)
- R828: nv_breaker 5-consecutive NV failure → graceful end
- R829: buffer for 循环 + WaitQueue 双重检测全 key cooling → fail-fast 跳过无谓重试
- R833: 连续 3 次 all_keys_exhausted → fail-fast (补 R829 盲区)
- R813: chain_full_retry inspect.signature=True

修复链对 NVCF RemoteDisc 风暴的吸收: R829/R833 把 502 平均耗时从 465s → 88s (5.3x 改善), buffer 5key 轮转把 in-flight 失败转成成功.

## 健康检查

- `curl localhost:40006/health` → ok, 5 keys, pexec models 含 glm5_2_nv
- `curl localhost:4101/health` → ok, primary=glm5_2_nv
- docker ps: nv_gw Up 2h, cc4101 Up 3h, dsv4p_nv40066 Up 30h, dsvf0731_nv40666 Up 21h, logs_db Up 6d

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, KeyManager 429→120-600s 指数退避, RemoteDisc→5s 短惩罚,
       TIER_COOLDOWN_S=180, MS_FALLBACK_ENABLED=0→dsv4f0731_nv40666:40666,
       PEER_FALLBACK_ENABLED=0, NVU_BUFFER_AKE_FAST_N=3 (R833)
cc4101: PRIMARY=glm5_2_nv@nv_gw:40006, FALLBACK=dsv4f0731_nv@dsvf0731_nv40666:40666,
        STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400
```

## 下一步

- 继续观测, 确认 NVCF RemoteDisc 风暴完全退去 (像 R835 tier 零错误那样)
- R829 ALL-COOLING 仍待场景触发验证 (本轮无显式日志确认)
- 不改码, 进入长期观测期
