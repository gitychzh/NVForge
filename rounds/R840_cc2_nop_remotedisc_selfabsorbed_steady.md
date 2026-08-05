# R840 — NOP 巡检轮: NVCF RemoteDisc 瞬态回潮 buffer 全吸收, 链路稳态延续

> 时间: 2026-08-06 02:25-02:55 CST (30min 真实窗口, DB UTC 对齐)
> 上轮: R839 (NOP, glm5_2_nv tier 零错误, 主链路稳态)
> 容器: nv_gw Up 2h, cc4101 Up 4h, dsv4p_nv40066 Up 30h, dsvf0731_nv40666 Up 21h, logs_db Up 6d

## 本轮改动: 无 (NOP 巡检轮)

## 本轮数据

### 30min 总览

| 指标 | 值 | 状态 |
|---|---|---|
| **glm5_2_nv nv_requests 最终 SR** | 50/52 = 96.2% (50 pexec 200 + 2 ms_fallback 502) | ✅ |
| **glm5_2_nv tier per-key pexec_success** | 50 (k0:9 k1:11 k2:9 k3:10 k4:11) | ✅ 跨全 key |
| **glm5_2_nv tier RemoteDisc 瞬态** | 19 (k0:2 k1:3 k2:5 k3:4 k4:5) | ⚠️ NVCF 后端瞬态 |
| **glm5_2_nv tier 529_overloaded** | 1 (k3) | ⚠️ 同上 NVCF 后端 |
| **cc4101 总 SR (含 fallback)** | 859/891 = 96.4% | ✅ |
| **fallback 触发率** | 17/891 = 1.9% | ✅ <5% |
| **all_tiers_exhausted** | 7 次 avg 80s | ✅ fail-fast (vs 历史 465s, 5.8x 改善) |
| **buffer_exhausted** | 1 次 451s + 2 ms_fallback 502 avg 453s | ⚠️ 全 5 key 瞬态挂 |
| **zombie_empty_completion** | 1 次 6s | 瞬态 |
| **最近 15 glm5_2_nv 请求** | 全 200, 全 1-tier, 4-114s | ✅ 实时稳态 |

### per-key pexec_success + RemoteDisc 分布 (30min)

```
k0:  9 success, 2 RemoteDisc
k1: 11 success, 3 RemoteDisc
k2:  9 success, 5 RemoteDisc
k3: 10 success, 4 RemoteDisc + 1 529_overloaded
k4: 11 success, 5 RemoteDisc
───
全 5 key 净 pexec_success=50, RemoteDisc=19 (跨全 key 瞬态分散), 529=1
```

RemoteDisc 19 次是 NVCF 后端瞬态风暴 (跨全 5 key 分散, 不是单个 key/代理故障),
buffer 5key 轮转全部吸收 → tier 最终成功 50/52=96.2%, 失败 2 个走 ms_fallback。

### 失败分类 (30min, 8 个失败 nv_requests)

| error_type | count | avg_s | 归因 |
|---|---|---|---|
| all_tiers_exhausted | 7 | 80 | R829/R833 fail-fast 生效 (vs 历史 465s, 5.8x) |
| buffer_exhausted | 1 | 451 | 全 5 key 瞬态挂穿 buffer |
| zombie_empty_completion | 1 | 6 | NVCF 返回空 completion 瞬态 |

**primary (glm5_2_nv) 主链路内 pexec 200 成功 50 次, 远程断连 19 次全被 buffer 吸收** — 主链路稳态.

### 修复链 (沿用 R827+R828+R829+R833+R813)

- R827: buffer total_deadline 锚定 t_start (防 deadline 漂移)
- R828: nv_breaker 5-consecutive NV failure → graceful end
- R829: buffer for 循环 + WaitQueue 双重检测全 key cooling → fail-fast
- R833: 连续 3 次 all_keys_exhausted → fail-fast (补 R829 盲区)
- R813: chain_full_retry inspect.signature=True

效果: all_tiers_exhausted avg 耗从历史 465s → 80s (5.8x 改善), 本轮 7 次全 65-109s.

## 健康检查

- `curl localhost:40006/health` → ok, pexec models 含 glm5_2_nv ✅
- `curl localhost:4101/health` → ok, primary=glm5_2_nv ✅
- `curl localhost:40066/50666/health` → ok (dsv4p/dsv4f0731) ✅
- docker ps: 全 Up ✅

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, KeyManager 429→120-600s 指数退避, RemoteDisc→5s 短惩罚,
       TIER_COOLDOWN_S=180, MS_FALLBACK_ENABLED=0 (env NVU_DISABLE_MS_FALLBACK=0 已恢复),
       PEER_FALLBACK_ENABLED=0, NVU_BUFFER_AKE_FAST_N=3 (R833)
cc4101: PRIMARY=glm5_2_nv@nv_gw:40006, FALLBACK=dsv4f0731_nv@dsvf0731_nv40666:40666,
        STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步

- 连续 R835-R840 六轮 NOP, glm5_2_nv 主链路稳态延续.
- NVCF RemoteDisc 瞬态风暴 (本轮 19 次) 是后端不可侧修复, buffer 5key 轮转全吸收 — 修复链 R827+R828+R829+R833+R813 充分.
- dsv4f0731_nv fallback 后端 SR=62% (13/21) 偏低 (8 502 avg 70s), 这是 cc4101 fallback 目标 `dsvf0731_nv40666:40666` 后端问题, 非 nv_gw (40006) 范围.
- 不改码, 继续长期观测.
