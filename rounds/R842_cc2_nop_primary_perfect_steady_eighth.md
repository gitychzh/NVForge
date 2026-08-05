# R842 — NOP 巡检轮: primary glm5_2_nv SR=100% 完美稳态 (连续第八轮 NOP)

> 时间: 2026-08-06 03:02 CST | 上轮: R841 | 容器: nv_gw Up 2h, cc4101 Up 4h
> 判定: NOP (不改码) — primary 主链路 SR=100%, fallback 1.9%, 连续 R835-R842 八轮 NOP

## 30min 真实窗口数据 (02:32-03:02 CST, DB UTC 对齐)

### 主链路 (cc4101-primary → nv_gw → glm5_2_nv)

| 指标 | 值 | 状态 |
|---|---|---|
| **glm5_2_nv nv_requests SR (cc4101-primary)** | 61/61 = 100% | ✅ 完美 |
| **主链路 502** | 0 | ✅ 零穿透 |
| fallback 触发率 (全部 cc_requests) | 17/906 = 1.9% | ✅ <5% |
| all_tiers_exhausted | 6 次 avg 85s | ✅ fail-fast |
| zombie_empty_completion | 1 次 avg 6s | ⚠️ 瞬态 |

### Tier per-key 分布 (nv_tier_attempts)

```
k0: 10 pexec_success, 2 RemoteDisc
k1: 12 pexec_success, 3 RemoteDisc
k2: 13 pexec_success, 7 RemoteDisc      ← k2 本轮 RemoteDisc 最集中
k3: 11 pexec_success, 2 RemoteDisc + 1 529_overloaded + 1 empty_200
k4: 13 pexec_success, 2 RemoteDisc
─────────────────────────────────────────
合计: 59 pexec_success, 16 RemoteDisc + 1 529 + 1 empty_200
```

RemoteDisc 16 次跨全 5 key 分散 (k2 偏多 7 次), 被 buffer 5key 轮转全吸收。
pexec_success 59 次 = 主链路实际成功 (nv_requests 61×200 含 2 次 ms_fallback 不经 tier)。

### cc_requests 30min 全景

```
mapped_model | status | error_type              | cnt | avg_s
glm5_2_nv    | 200    |                         | 859 | 66
glm5_2_nv    | 499    | client_gone_mid_stream  |  19 | 191    ← 用户中断
glm5_2_ms    | 200    |                         |   8 | 167    ← ms_gw fallback 成功
glm5_2_ms    | 502    | timeout                 |   3 | 294    ← ms_gw fallback 失败
dsv4p_nv     | 502    | timeout                 |   6 | 294    ← dsv4p fallback 失败
dsv4f0731_nv | 200    |                         |   9 | 201    ← dsv4f0731 fallback 成功
dsv4f0731_nv | 502    | timeout                 |   3 | 300    ← dsv4f0731 fallback 失败
```

主链路 glm5_2_nv: 859 200 + 19 client_gone (499, 用户主动断开不算错误) = 主链路零 502。
fallback 路径 (glm5_2_ms/dsv4p_nv/dsv4f0731_nv) 的 502 都是 fallback 后端问题, 非 nv_gw(40006) 范围。

### 错误分类 (nv_requests, 30min)

| error_type | count | avg_s | 归因 |
|---|---|---|---|
| all_tiers_exhausted | 6 | 85 | R829/R833 fail-fast (vs 历史 465s, 5.5x 改善) |
| zombie_empty_completion | 1 | 6 | NVCF 空返回瞬态 |

## 修复链 (沿用, R827+R828+R829+R833+R813)

- R827: buffer total_deadline 锚定 t_start (防 deadline 漂移)
- R828: nv_breaker 5-consecutive NV failure → graceful end
- R829: buffer for 循环 + WaitQueue 双重检测全 key cooling → fail-fast
- R833: 连续 3 次 all_keys_exhausted → fail-fast (补 R829 盲区)
- R813: chain_full_retry inspect.signature=True

效果: all_tiers_exhausted avg 85s vs 历史 465s (5.5x 改善)。

## 健康检查

- `curl localhost:40006/health` → ok ✅
- `curl localhost:4101/health` → ok ✅
- docker ps: nv_gw Up 2h, cc4101 Up 4h, dsv4p_nv40066 Up 30h, dsvf0731_nv40666 Up 21h, logs_db Up 6d ✅

## 结论

- primary glm5_2_nv 主链路 SR=100% (61/61) 完美稳态, 零 502 穿透。
- RemoteDisc 瞬态 16 次跨全 5 key 分散, buffer 5key 轮转全吸收 — 修复链充分。
- fallback 1.9% < 5% 目标。
- all_tiers_exhausted 85s (fail-fast 生效, 5.5x 改善)。
- 连续 R835-R842 八轮 NOP, 链路进入长期稳态观测期。
- 不改码, 继续观测。
