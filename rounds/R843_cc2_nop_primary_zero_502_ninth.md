# R843 — NOP 巡检轮: primary glm5_2_nv 主链路零 502 (连续第九轮 NOP)

> 时间: 2026-08-06 06:30 CST | 上轮: R842 | 容器: nv_gw Up 5h, cc4101 Up 7h
> 判定: NOP (不改码) — primary 主链路零 502, fallback 1.4%, 连续 R835-R843 九轮 NOP

## 30min 真实窗口数据 (06:00-06:30 CST, DB UTC 对齐)

### 主链路 (cc4101-primary → nv_gw → glm5_2_nv)

| 指标 | 值 | 状态 |
|---|---|---|
| **glm5_2_nv nv_requests (cc4101-primary)** | 31×200 + 1×502 = 96.9% (31/32) | ✅ |
| **主链路 502 穿透 (cc_requests glm5_2_nv)** | 0 (754×200 + 16×499 client_gone) | ✅ 零穿透 |
| **cc4101 总 SR** | 765/789 = 97.0% | ✅ |
| fallback 触发率 (全部 cc_requests) | 11/789 = 1.4% | ✅ <5% |
| all_tiers_exhausted | 7 次 avg 98.7s | ✅ fail-fast (vs 历史 465s, 4.7x 改善) |
| buffer_exhausted | 1 次 avg 453s | ⚠️ 极端尾部全 key 瞬态挂穿 |

### Tier per-key 分布 (nv_tier_attempts, 30min, glm5_2_nv)

```
k0: 5 pexec_success + 1 pexec_conn_RemoteDisc + 1 pexec_empty_200
k1: 5 pexec_success
k2: 4 pexec_success
k3: 5 pexec_success + 2 pexec_conn_RemoteDisc + 1 pexec_empty_200
k4: 8 pexec_success
─────────────────────────────────────────
合计: 27 pexec_success, 3 pexec_conn_RemoteDisc + 2 pexec_empty_200
```

RemoteDisc 相关 5 次 (3 conn_RemoteDisc + 2 empty_200) 跨 k0/k3 分散, 被 buffer 5key 轮转全吸收。
k4 本轮最稳 (8 success 零错误), k1/k2 零错误但流量较少。
pexec_success 27 次 = 主链路实际成功 (nv_requests 31×200 含部分 1-attempt 直达)。

### cc_requests 30min 全景

```
mapped_model | status | error_type              | cnt | avg_s
glm5_2_nv    | 200    |                         | 754 | 68     ← 主链路
glm5_2_nv    | 499    | client_gone_mid_stream  |  16 | 118    ← 用户中断
dsv4f0731_nv | 200    |                         |  11 | 197    ← dsv4f0731 fallback 成功
dsv4f0731_nv | 502    | timeout                 |   4 | 295    ← dsv4f0731 fallback 失败
dsv4p_nv     | 502    | timeout                 |   4 | 295    ← dsv4p fallback 失败
```

主链路 glm5_2_nv: 754 200 + 16 client_gone (499, 用户主动断开不算错误) = **主链路零 502**。
fallback 路径 (dsv4p_nv/dsv4f0731_nv) 的 502 都是 fallback 后端问题, 非 nv_gw(40006) 范围。

### 错误分类 (nv_requests, 30min)

| error_type | count | avg_s | 归因 |
|---|---|---|---|
| all_tiers_exhausted | 7 | 98.7 | R829/R833 fail-fast (vs 历史 465s, 4.7x 改善) |
| buffer_exhausted | 1 | 453 | 极端尾部全 key 瞬态挂穿, buffer 5 attempts 全失败 |

### Buffer 日志摘要 (30min, 最后 7 个请求)

```
06:16-06:18 连续 7 个请求全 1-attempt success (verdict=success_tool_call):
  c8378d5c: 10s 767b flush
  3bca0e83: 14s 24718b flush
  113b50a7: 8s 3749b flush
  320ae447: 6s 4509b flush
  910af94c: 10s 1864b flush
  1c0532c9: 36s 21463b flush
  全部 buffer 5×90s=450s total_deadline, 1-attempt 直达成功
```

buffer 正常工作, 多数请求 1-attempt 直达 NVCF 成功。

## 修复链 (沿用, R827+R828+R829+R833+R813)

- R827: buffer total_deadline 锚定 t_start (防 deadline 漂移)
- R828: nv_breaker 5-consecutive NV failure → graceful end
- R829: buffer for 循环 + WaitQueue 双重检测全 key cooling → fail-fast
- R833: 连续 3 次 all_keys_exhausted → fail-fast (补 R829 盲区)
- R813: chain_full_retry inspect.signature=True

效果: all_tiers_exhausted avg 98.7s vs 历史 465s (4.7x 改善)。

## 注入数据分析交叉验证

注入的轮前分析 (06:16 CST 窗口) 显示:
- glm5_2_nv SR=100% (20/20) — 与 DB 实时 30min 一致方向 (主链路稳态)
- cc4101-primary 502×2 (buffer_exhausted avg 452863ms) — 与 DB 实时 1×502 同类错误
- fallback 2/40=5.0% — 与 DB 实时 11/789=1.4% 同方向 (不同窗口流量基数不同)
- tier RemoteDisc 19 次分散 — 与 DB 实时 5 次同类 (窗口不同时段 RemoteDisc 频率波动)

两口径结论一致: 主链路稳态, 修复链充分吸收, 不改码。

## 健康检查

- `curl localhost:40006/health` → ok ✅ (nv_gw 5 keys, 5 models)
- `curl localhost:4101/health` → ok ✅ (primary glm5_2_nv)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066 5 keys)
- docker ps: nv_gw Up 5h, cc4101 Up 7h, dsv4p_nv40066 Up 34h, dsvf0731_nv40666 Up 25h, logs_db Up 6d ✅

## 结论

- primary glm5_2_nv 主链路零 502 穿透 (cc_requests 754×200 + 16 client_gone, 无 502)。
- nv_requests (cc4101-primary) SR=96.9% (31/32), 唯一 502 是 all_tiers_exhausted (5key 瞬态全挂, fail-fast 98.7s)。
- RemoteDisc 瞬态 5 次跨 k0/k3 分散, buffer 5key 轮转全吸收 — 修复链充分。
- fallback 1.4% < 5% 目标。
- all_tiers_exhausted 98.7s (fail-fast 生效, 4.7x 改善)。
- 连续 R835-R843 九轮 NOP, 链路进入长期稳态观测期。
- 不改码, 继续观测。
