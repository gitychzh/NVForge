# R841 — NOP 巡检轮: primary glm5_2_nv SR=100%, RemoteDisc 17 次 buffer 全吸收

> 时间: 2026-08-06 02:58 CST (DB UTC 对齐, 30min 真实窗口)
> 上轮: R840 (NOP, RemoteDisc 19 次 buffer 全吸收)
> 容器: nv_gw Up 2h, cc4101 Up 4h, dsv4p_nv40066 Up 30h, dsvf0731_nv40666 Up 21h, logs_db Up 6d

## 改动: 无 (NOP 巡检轮, 连续 R835-R841 七轮 NOP)

## 依据

glm5_2_nv primary 主链路 SR=100% (50/50), tier per-key pexec_success 全 5 key 均匀,
RemoteDisc 瞬态 17 次跨全 key 分散被 buffer 5key 轮转全吸收, R829/R833 fail-fast 持续生效.
无新错误类型, 修复链 R827+R828+R829+R833+R813 充分. 无需改码.

## 本轮数据 (02:28-02:58 CST, 30min 窗口)

### 总览

| 指标 | 值 | 状态 |
|---|---|---|
| **glm5_2_nv nv_requests 最终 SR** | 50/50 = 100% (primary 主链路) | ✅ 完美 |
| **glm5_2_nv tier pexec_success** | 50 跨全 5 key | ✅ |
| **cc4101 总 SR** | 51/52 = 98.1% | ✅ |
| **fallback 触发率** | 1/52 = 1.9% | ✅ <5% |
| **all_tiers_exhausted** | 6 次 avg 81s | ✅ fail-fast (vs 历史 465s, 5.7x) |
| **buffer_exhausted** | 1 次 452s | ⚠️ 极端尾部 |
| **zombie_empty_completion** | 1 次 6s | 瞬态 |

### per-key pexec_success + RemoteDisc 分布

```
k0: 10 success, 3 RemoteDisc  → SR 77% (10/13)
k1: 10 success, 3 RemoteDisc  → SR 77% (10/13)
k2: 10 success, 5 RemoteDisc  → SR 67% (10/15)
k3:  9 success, 3 RemoteDisc + 1 529_overloaded → SR 69% (9/13)
k4: 11 success, 3 RemoteDisc  → SR 79% (11/14)
```

跨全 5 key 均匀分散, 无集中点. buffer 5key 轮转充分吸收.

### 错误分类 (30min)

| error_type | count | avg_ms | 归因 |
|---|---|---|---|
| all_tiers_exhausted | 6 | 80961 | R829/R833 fail-fast 跨全 key cooling |
| buffer_exhausted | 1 | 451999 | 全 5 key 瞬态挂穿 buffer 极端尾部 |
| zombie_empty_completion | 1 | 5864 | NVCF 空返回瞬态 |

### 非 cc2 主链路 (不在本轮范围)

- dsv4f0731_nv SR=62% (13/21) — cc4101 fallback 目标 `dsvf0731_nv40666:40666` 后端问题
- hermes caller dsv4f0731_nv: 12×200 + 7×502 — 另一条链路 (非 cc2)

## 修复链 (沿用, R827+R828+R829+R833+R813)

- R827: buffer total_deadline 锚定 t_start (防 deadline 漂移)
- R828: nv_breaker 5-consecutive NV failure → graceful end
- R829: buffer for 循环 + WaitQueue 双重检测全 key cooling → fail-fast
- R833: 连续 3 次 all_keys_exhausted → fail-fast (补 R829 盲区)
- R813: chain_full_retry inspect.signature=True

修复链效果: all_tiers_exhausted avg 81s vs 历史 465s (5.7x 改善).

## 健康检查

- nv_gw (40006): ok, pexec models 含 glm5_2_nv, 5key ✅
- cc4101 (4101): ok, primary=glm5_2_nv ✅
- dsv4p_nv40066 (40066): ok ✅
- docker ps: 全 Up ✅

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, KeyManager 429→120-600s 指数退避, RemoteDisc→5s 短惩罚,
       TIER_COOLDOWN_S=180, MS_FALLBACK_ENABLED=0 (NVU_DISABLE_MS_FALLBACK=0),
       PEER_FALLBACK_ENABLED=0, NVU_BUFFER_AKE_FAST_N=3 (R833)
cc4101: PRIMARY=glm5_2_nv@nv_gw:40006, FALLBACK=dsv4f0731_nv@dsvf0731_nv40666:40666,
        STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步

- 连续 R835-R841 七轮 NOP, glm5_2_nv primary SR=100% 完美稳态.
- NVCF RemoteDisc 瞬态风暴 (本轮 17 次) 是后端不可侧修复, buffer 5key 轮转全吸收 — 修复链 R827+R828+R829+R833+R813 充分.
- dsv4f0731_nv fallback 后端 SR=62% (13/21) 偏低 (8 502 avg ~295s), 这是 cc4101 fallback 目标后端问题, 非 nv_gw (40006) 范围.
- 不改码, 继续长期观测.
