# R830 — cc2 NOP 巡检轮: R829 fail-fast 待触发, NVCF RemoteDisc 瞬态全被 buffer 吸收

> 时间: 2026-08-05 20:08 CST | 上轮: R829 (全 key cooling fail-fast, 已就位)
> 容器: nv_gw (Up 27min) | 改动: 无 (NOP 巡检轮)

## 本轮改动: 无 (NOP 巡检轮)

R829 (buffer 全 key cooling fail-fast) 已就位。本轮数据未触发 R829 fail-fast (无全 key cooling 场景)。
链路全稳, 瞬态 RemoteDisconnected 被 buffer 5key 轮转完全吸收, 用户零感知。无源码 / 无 env 改动。

## 30min 真实窗口 (20:08 CST 窗口)

### cc2 主链路 (cc4101-primary → glm5_2_nv)

| 指标 | 值 | 状态 |
|---|---|---|
| per-call SR | 100% (28/28) | ✅ |
| 用户可见 SR | 100% (零 502 穿透) | ✅ |
| avg 耗时 | 73.7s | 正常 |
| fallback 触发 | 0 (主链路) | ✅ |

### tier 层错误 (per-key, 30min)

```
k0  NVCFPexecRemoteDisconnected ×3, pexec_conn_RemoteDisconnected ×1, pexec_success ×6
k1  NVCFPexecRemoteDisconnected ×1, pexec_conn_RemoteDisconnected ×1, pexec_success ×5
k2  NVCFPexecRemoteDisconnected ×4,                  pexec_success ×3
k3  NVCFPexecRemoteDisconnected ×2,                  pexec_success ×8
k4  NVCFPexecRemoteDisconnected ×4,                  pexec_success ×6
─────────────────────────────────────────────────────────────────
    RemoteDisconnected ×14 (瞬态), pexec_success ×28
```

**per-key tier 最终成功 SR = 100% (28/28)** — 14 次 NVCF 瞬态 RemoteDisconnected
全部被 buffer 5key 轮转吸收, 每个请求最终都有至少一个 key pexec_success。
buffer 设计目的充分体现: NVCF 后端抖动透明吸收, 用户零感知。

### 非 cc2 范围 (注入数据, 不影响 cc2)

- `hermes|dsv4f0731_nv SR=72.2% (13/18)` — hermes caller 走 dsv4f0731_nv, 不在 cc2 (glm5_2_nv) 范围
- `openclaw|dsv4p_nv SR=0% (0/2)` — openclaw caller 走 dsv4p_nv, 不在 cc2 范围
- `all_tiers_exhausted ×6` — 来自 dsv4f0731_nv 链路, 不是 cc2 的 glm5_2_nv
- `zombie_empty_completion ×1` — 同上

这些是另一条链路 (dsv4f0731_nv / dsv4p_nv) 的问题, cc2 不负责, 不改码。

## R829 fail-fast 触发情况

本轮 30min 窗口 **无全 key cooling 场景**, R829 fail-fast 未触发。
14 次 RemoteDisconnected 都是单 key 瞬态, 另有 4 key 可用, buffer 轮转即吸收。
fail-fast 设计针对的是"5 key 全在长冷却"的极端场景, 本轮未发生。

## R829 + R828 + R827 就位铁证 (无变化, 沿用 R829 验证)

- R827 (buffer total_deadline 锚定 t_start): 就位
- R828 (nv_breaker 5-consecutive → ms_gw + buffer_stream ms_gw 兜底): 就位
- R829 (全 key cooling fail-fast: for 循环 + WaitQueue 双重跳过): 就位
- R813 (chain_full_retry inspect.signature=True): 就位

## 健康检查

```
curl localhost:40006/health → ok, 5 keys, pexec models 含 glm5_2_nv
curl localhost:4101/health  → ok, primary=glm5_2_nv
docker ps: nv_gw Up 27min, cc4101 Up 18h, dsv4p_nv40066 Up 23h
```

## 指标对比

| 指标 | R829 目标 | 本轮 (R830) | 状态 |
|---|---|---|---|
| per-call SR | 90%+ (参考) | 100% (28/28) | ✅ |
| per-attempt SR | 90%+ (参考) | 28/(28+14+2)=63.6% | 瞬态抖动吸收中 |
| ms_fallback 触发率 | < 5% | 0% (主链路) | ✅ |
| 失败请求 avg 耗时 | < 30s | 无失败请求 | ✅ (R829 待场景验证) |

## 下一步

- 继续观察, 等待下次 NVCF 风暴验证 R829 fail-fast
- 关注 RemoteDisconnected 是否升级为持续性 (当前是单 key 瞬态, 可接受)
- 若出现全 key cooling 场景, 确认 NV-BUFFER-ALL-COOLING / NV-BUFFER-SKIP-WAIT 日志
- 优化方向仍是最大化 NV 成功吞吐量, 当前 28req/30min ≈ 56/h, 健康
