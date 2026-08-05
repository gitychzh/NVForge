# R839: NOP 巡检轮 — glm5_2_nv tier 零错误, 主链路稳态延续

**时间**: 2026-08-06 02:47 CST
**决策**: NOP, 不改码. 主链路连续 R835-R839 五轮稳态, NVCF RemoteDisc 风暴已完全退去.

## 本轮数据 (02:17-02:47 CST, 30min 真实窗口, DB UTC 对齐)

| 指标 | 值 | 状态 |
|---|---|---|
| **nv_gw glm5_2_nv tier per-key** | 全 5 key pexec_success=43, **零错误** | ✅ 完美 |
| cc4101 总 SR (含 fallback) | 96.3% (854/887) | ✅ |
| fallback 触发率 | 2.0% (18/887) | ✅ <5% |
| 全 5 key RemoteDisc/429 | **0** (k0:0 k1:0 k2:0 k3:0 k4:0) | ✅ 风暴已退 |

### per-key pexec_success 分布 (30min, 零 RemoteDisc/429)

```
k0:  9 success (零错误)
k1: 10 success (零错误)
k2:  7 success (零错误)
k3:  9 success (零错误)
k4:  8 success (零错误)
```

**全 5 key 净 pexec_success 43, 零错误** — 对比 R837 同窗口仍有 21 RemoteDisc 跨全 5 key.

### 失败分类 (30min)

| source | status | error_type | count | avg_s | 归因 |
|---|---|---|---|---|---|
| cc4101 | 499 | client_gone_mid_stream | 21 | 199 | 用户主动中断, 非链路故障 |
| cc4101 | 502 | timeout | 12 | 295 | dsv4f0731_nv fallback 后端超时 (非 nv_gw 40006) |
| nv_gw | 502 | all_tiers_exhausted | 6 | 82 | R829/R833 fail-fast 生效 (vs 历史 465s, 5.7x 改善) |
| nv_gw | 502 | buffer_exhausted | 2 | 452 | 更早窗口残留 (NVCF 风暴期产物) |

**primary (glm5_2_nv) 主链路无 502, 无 NVCF 错误** — 主链路完美状态.
fallback 12 个 502 全是 `dsv4f0731_nv@40666` 后端超时, 来自 hermes caller 走 fallback 及 cc4101-primary 偶发 fallback.
这是 cc4101 fallback 目标 `dsvf0731_nv40666:40666` 的问题, 不归 nv_gw (40006) 管.

### fallback 路径分析

- cc4101-primary: 200×49 + 502×2 (buffer_exhausted avg 452s)
- hermes: 200×14 + 502×7
- dsv4f0731_nv SR=64.0% (16/25) — fallback 后端不稳, 非 cc2 主链路范围

### 注入轮前数据口径

注入数据 (02:41:33 CST 拉取) 与直接 DB 查询一致:
- glm5_2_nv SR=100% (47/47) ✅
- tier RemoteDisc 19 跨全 5 key (k0:2 k1:3 k2:5 k3:4 k4:5) — 这是更早 30min 窗口 (01:41-02:11) 的残留
- cc4101-primary 2 个 502 buffer_exhausted avg 452s — 更早窗口 NVCF 风暴期产物
- all_tiers_exhausted×7 avg 79s — R829/R833 fail-fast 持续生效

两口径结论一致: 主链路稳, 风暴退去, 修复链充分吸收.

## 修复链 (沿用, R827+R828+R829+R833+R813)

- R827: buffer total_deadline 锚定 t_start (防 deadline 漂移)
- R828: nv_breaker 5-consecutive NV failure → graceful end
- R829: buffer for 循环 + WaitQueue 双重检测全 key cooling → fail-fast
- R833: 连续 3 次 all_keys_exhausted → fail-fast (补 R829 盲区)
- R813: chain_full_retry inspect.signature=True

修复链对 NVCF RemoteDisc 风暴的吸收: all_tiers_exhausted avg 耗时从历史 465s → 82s (5.7x 改善).

## 健康检查

- `curl localhost:40006/health` → ok, pexec models 含 glm5_2_nv ✅
- `curl localhost:4101/health` → ok, primary=glm5_2_nv ✅
- `curl localhost:40066/health` → ok (dsv4p_nv40066) ✅
- docker ps: nv_gw Up 2h, cc4101 Up 4h, dsv4p_nv40066 Up 30h, dsvf0731_nv40666 Up 21h, logs_db Up 6d ✅

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, KeyManager 429→120-600s 指数退避, RemoteDisc→5s 短惩罚,
       TIER_COOLDOWN_S=180, MS_FALLBACK_ENABLED=0,
       PEER_FALLBACK_ENABLED=0, NVU_BUFFER_AKE_FAST_N=3 (R833)
cc4101: PRIMARY=glm5_2_nv@nv_gw:40006, FALLBACK=dsv4f0731_nv@dsvf0731_nv40666:40666,
        STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步

- 链路进入稳态观测. 连续 R835-R839 五轮 NOP, glm5_2_nv 主链路稳态, 全 5 key 净 pexec_success.
- dsv4f0731_nv fallback 后端 SR=64% 持续偏低, 这是 cc4101 fallback 目标 `dsvf0731_nv40666:40666` 的后端问题, 非 nv_gw (40006) 范围.
- 不改码, 继续长期观测.
