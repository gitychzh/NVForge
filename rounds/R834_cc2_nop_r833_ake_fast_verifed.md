# R834 — NOP 巡检轮 (R833 AKE fail-fast 已验证触发, 链路全稳)

> 时间: 2026-08-06 00:03 CST
> 上轮: R833 (buffer 连续 AKE fail-fast)
> 容器: nv_gw Up 47m, cc4101 Up 47m, dsv4p_nv40066 Up 27h, dsvf0731_nv40666 Up 19h

## 改动: 无 (NOP 巡检轮)

R833 (连续 3 次 all_keys_exhausted → fail-fast) **本轮已验证触发**, 不再示 nopd (不再 NOP)。
R829 (全 key cooling fail-fast) 仍为待触发状态。

## 本轮数据 (00:03 CST 注入窗口, cc4101-primary 30min)

### nv_gw (cc4101-primary 视角)

| 指标 | 值 | 状态 |
|---|---|---|
| per-call SR | 94.4% (85/90) | ✅ >85% |
| per-key tier 成功 | 81 次 pexec_success (k0:15 k1:16 k2:19 k3:17 k4:14) | ✅ |
| per-key tier 瞬态 | k0 empty_200×1, k1 429×1 | 透明吸收 |
| per-key tier 0 失败 (transport error) | ✅ 本轮 zero RemoteDisc | ✅ 显著改善 |
| 用户可见 SR (cc4101) | 96.0% (958/998), fb=1.9% (19) | ✅ >95% |
| R833 AKE-FASTM 触发 | 3 次触发 (ce91236f/8028e4bd/62f3fbed) | ✅ 已验证 |
| R829 ALL-COOLING 触发 | 0 次 (无全 key cooling 场景) | 待场景 |

### 失败分类 (7 次, cc4101-primary)

| 错误类型 | 次数 | 耗时 | 分析 |
|---|---|---|---|
| buffer_exhausted (ms_fallback) | 4 | 445-463s | R833 AKE-FASTM 后走 ms_fallback→dsvf0731_nv40666, 回退总时长仍高 (~260s 回退时间)。这是回退路径自身的速度限制, 非主链路问题 |
| client_gone_during_flush | 2 | 156-195s | 瞬态流中断, 非 nv_gw bug |
| NVAnthCollect_IncompleteRead | 1 | 197s | 瞬态收集中断 |

### per-key tier 详情

```
k0: pexec_success×15, empty_200×1  |  k1: pexec_success×16, 429×1
k2: pexec_success×19              |  k3: pexec_success×17
k4: pexec_success×14
```

**本轮 RemoteDisconnected = 0** (对比 R832 RemoteDisc×16, 显著改善)。
429 ×1 + empty_200 ×1 为单 key 瞬态, 被 buffer 5key 轮转吸收。

### AKE-FASTM 触发详情

| req | 耗时 | 最终路径 | 结果 |
|---|---|---|---|
| ce91236f | 333s | nvcf_pexec | ✅ 成功 (AKE-FASTM 后回退到 NVCF 重试成功) |
| 8028e4bd | 452s | ms_fallback | ❌ buffer_exhausted |
| 62f3fbed | 457s | ms_fallback | ❌ buffer_exhausted |

R833 在第 3 次 AKE 时 break (约 190s), 之后回退路径覆盖剩余时间。

### 非 cc2 范围 (注入数据, 不处理)

- hermes|dsv4f0731_nv SR=64.3% (9/14) — hermes caller 另一条链路
- cc4101-fallback|glm5_2_nv SR=100% (4/4) — fallback 调用者, cc4101 层级

## 就位修复链 (沿用, R827+R828+R829+R833)

- R827: buffer total_deadline 锚定 t_start (防止 deadline 漂移)
- R828: nv_breaker 5-consecutive NV failure → next req 直送 ms_gw + buffer_stream ms_gw 兜底
- R829: buffer for 循环 + WaitQueue 双重检测全 key cooling → fail-fast 跳过无谓重试
- R833: 连续 3 次 all_keys_exhausted → fail-fast (补 R829 盲区, 覆盖短惩罚持续全挂场景)
- R813: chain_full_retry inspect.signature=True

## 健康检查

- `curl localhost:40006/health` → ok, 5 keys, pexec models 含 glm5_2_nv
- `curl localhost:4101/health` → ok, primary=glm5_2_nv
- docker ps: nv_gw Up 47m, cc4101 Up 47m, dsv4p_nv40066 Up 27h, dsvf0731_nv40666 Up 19h, logs_db Up 6d

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, KeyManager 429→120-600s 指数退避, RemoteDisc→5s 短惩罚,
       TIER_COOLDOWN_S=180, MS_FALLBACK_ENABLED=1→dsvf0731_nv40666:40666,
       PEER_FALLBACK_ENABLED=0, NVU_BUFFER_AKE_FAST_N=3 (R833 新增)
cc4101: PRIMARY=glm5_2_nv@nv_gw:40006, FALLBACK=dsv4f0731_nv@dsvf0731_nv40666:40666,
        STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400
```

## 下一步

- 继续观测, 等待 RemoteDisc 零化趋势确认 (本轮回零)
- R829 (全 key cooling fail-fast) 仍待场景触发验证
- R833 (AKE-FASTM) 已验证触发, 继续观测在 NVCF 不稳定期的节省效果
- 关注回退路径 (dsv4f0731_nv) 的响应速度 — 当前 260s 偏长, 但不属于主链路问题
- 长期目标: 最大化 NV 成功吞吐量, 当前 ~170/h (85req/30min) 已达目标区间