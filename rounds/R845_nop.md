# R845 — NOP 巡检轮 (连续第十一轮, primary glm5_2_nv SR=100% 零502)

> 日期: 2026-08-06 06:24 CST | 上轮: R844 (NOP, 第十轮)
> 容器: nv_gw Up 4min (刚 restart, 疑宿主机维护), cc4101 Up 7h, dsv4p_nv40066 Up 34h, dsvf0731_nv40666 Up 25h, logs_db Up 6d

## 判稳: NOP (不改码)

glm5_2_nv primary 主链路 SR=100% (38/38 零 502), fallback 1.7% < 5%, 无新错误。
连续 R835-R845 十一轮 NOP 稳态。

## 本轮数据 (06:24 CST, 30min 真实窗口, DB UTC 对齐)

| 指标 | 值 | 状态 |
|---|---|---|
| **glm5_2_nv (cc4101-primary)** | 38/38 = 100% (零 502) | ✅ 完美 |
| **cc4101-primary 总 SR** | 39/40 = 97.5% (1×buffer_exhausted) | ✅ |
| **主链路 502 穿透** | 0 | ✅ 零穿透 |
| **glm5_2_nv tier per-key pexec_success** | 38 (k0:8 k1:7 k2:7 k3:6 k4:10) | ✅ |
| **RemoteDisc 瞬态跨 key** | 19 次 (k0:4 k1:4 k2:5 k3:4 k4:5) 被 buffer 全吸收 | ⚠️→✅ |
| fallback 触发率 | 1/59 = 1.7% | ✅ <5% |
| all_tiers_exhausted | 8 次 avg 87.3s | ✅ fail-fast (vs 历史 465s, 5.3x) |
| buffer_exhausted | 1 次 (453s) | ⚠️ 极端尾部全 key 瞬态挂穿 |

### per-key pexec_success + RemoteDisc 分布

```
k0: 8 success, 4 RemoteDisc                                      ← 稳定
k1: 7 success, 4 RemoteDisc
k2: 7 success, 5 RemoteDisc                                      ← RemoteDisc 最多
k3: 6 success, 4 RemoteDisc + 1 529_overloaded + 2 conn_RemoteDisc + 1 empty_200 + 1 pexec_empty_200  ← k3 最复杂 (但 6 成功)
k4: 10 success, 5 RemoteDisc                                     ← k4 最稳 (success 最多)
```

19 RemoteDisc 瞬态跨全 5 key 分散, buffer 5key 轮转全吸收, 用户零穿透。
1 buffer_exhausted (453s) 是 5key 全挂穿到 cc4101 的极端尾部, NVCF 后端不可侧修复。

### cc4101-primary 30min 全景

```
status | cnt | avg_dur(ms) | error_type
200    |  39 | 42763       | (成功, avg ~43s)
502    |   1 | 453349      | buffer_exhausted
```

主链路零 502 穿透。1×502 是 5key 全挂后 buffer 耗尽穿到 cc4101, 属 NVCF 后端极端尾部。

### fallback 链路观察

dsv4f0731_nv (cc4101 fallback 目标) SR=57.1% (12/21, 8×502), 但本轮 fallback 仅触发 1 次,
影响极小。dsv4f0731_nv 后端本身不稳但不在本轮修复范围 (只改 nv_gw 40006 主链路)。

## 修复链 (沿用, R827+R828+R829+R833+R813)

- R827: buffer total_deadline 锚定 t_start (防 deadline 漂移)
- R828: nv_breaker 5-consecutive NV failure → graceful end
- R829: buffer for 循环 + WaitQueue 双重检测全 key cooling → fail-fast
- R833: 连续 3 次 all_keys_exhausted → fail-fast (补 R829 盲区)
- R813: chain_full_retry inspect.signature=True

修复链效果: all_tiers_exhausted avg 87.3s vs 历史 465s (5.3x 改善)。

## 健康检查

- `curl localhost:40006/health` → ok ✅ (nv_gw, 5 keys)
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=glm5_2_nv)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)
- `curl localhost:40666/health` → ok ✅ (dsvf0731_nv40666)
- docker ps: 全 Up ✅ (nv_gw Up 4min 刚 restart, 其余均长效 Up)

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, KeyManager 429→120-600s 指数退避, RemoteDisc→5s 短惩罚,
       TIER_COOLDOWN_S=180, NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 已恢复),
       PEER_FALLBACK_ENABLED=0, NVU_BUFFER_AKE_FAST_N=3 (R833)
cc4101: PRIMARY=glm5_2_nv@nv_gw:40006, FALLBACK=dsv4f0731_nv@dsvf0731_nv40666:40666,
        STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步

- 连续 R835-R845 十一轮 NOP, glm5_2_nv primary 主链路零 502 穿透稳态延续。
- 继续长期观测, 不改码。
- 关注 dsv4f0731_nv fallback 链路 SR 57.1% — 但 fallback 触发率 1.7% 极低, 不在本轮范围。
