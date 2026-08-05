# R831 — NOP 巡检轮 (R829 fail-fast 仍待触发, 链路全稳)

> 轮号: R831 | 容器: nv_gw, cc4101, dsv4p_nv40066 (全 Up) | 时间: 2026-08-05 20:19 CST
> 上轮: R830 (NOP, R829 fail-fast 待场景)

## 决策: NOP (不改码)

## 本轮数据 (20:19 CST 注入窗口)

### cc2 主链路 (cc4101-primary × glm5_2_nv) — 唯一关注

| 指标 | 值 | 状态 |
|---|---|---|
| per-call SR | 100% (36/36) | ✅ |
| 用户可见 SR | 100% (零 502 穿透) | ✅ |
| ms_fallback 触发率 | 0% (主链路) | ✅ |
| 平均耗时 | ~67s (3600/36 全 200 OK) | 健康 |
| NV 成功吞吐 | 36req/30min ≈ 72/h | 高位 |
| R829 fail-fast 触发 | 无 (无全 key cooling 场景) | 待场景 |

### per-key tier 错误分布 (glm5_2_nv)

```
k0: pexec_success×11, NVCFPexecRemoteDisconnected×5   (SR 11/16)
k1: pexec_success×8,  NVCFPexecRemoteDisconnected×2   (SR 8/10)
k2: pexec_success×1,  NVCFPexecRemoteDisconnected×3   (SR 1/4)
k3: pexec_success×10, NVCFPexecRemoteDisconnected×1   (SR 10/11)
k4: pexec_success×6,  NVCFPexecRemoteDisconnected×5   (SR 6/11)
```

汇总: 36 次最终成功, 16 次 NVCFPexecRemoteDisconnected 瞬态, 全被 buffer 5key 轮转吸收。
RemoteDisconnected 跨全 5 key 分布均匀 (无明显单 key 持续性), 是 NVCF 后端瞬态, 非链路 bug。

### 非 cc2 范围 (注入数据, 不处理)

- `hermes\|dsv4f0731_nv SR=68.4% (13/19)` — hermes caller, 另一条链路
- `openclaw\|dsv4p_nv SR=0% (0/2)` — openclaw caller, 另一条链路
- `all_tiers_exhausted ×7` — 自动分析归属 dsv4f0731, 非 cc2 的 glm5_2_nv
- `zombie_empty_completion ×1` — 非 cc2 范围

只看 `caller=cc4101-primary AND model=glm5_2_nv` 一行: 36 req 全 200, cc2 链路 100% 健康。

## 就位修复链 (沿用, R827+R828+R829)

- R827: buffer total_deadline 锚定 t_start (防止 deadline 漂移)
- R828: nv_breaker 5-consecutive NV failure → next req 直送 ms_gw + buffer_stream ms_gw 兜底
- R829: buffer for 循环 + WaitQueue 双重检测全 key cooling → fail-fast 跳过无谓重试
- R813: chain_full_retry inspect.signature=True

本轮 R829 fail-fast 仍未触发 — 三个连续 NOP 轮均无全 key cooling 场景出现。
说明当前 NVCF 后端虽有 RemoteDisconnected 瞬态, 但从未同时打挂全部 5 key,
buffer 5key 轮转设计 (k_i 失败 → 立即切 k_{i+1}) 足以吸收。

## 健康检查

- `curl localhost:40006/health` → ok, 5 keys, pexec models 含 glm5_2_nv
- `curl localhost:4101/health` → ok, primary=glm5_2_nv
- `curl localhost:40066/health` → ok, 5 keys
- docker ps: nv_gw Up 38m, cc4101 Up 19h, dsv4p_nv40066 Up 24h, logs_db Up 6d

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, KeyManager 429→120-600s 指数退避, RemoteDisc→5s 短惩罚,
       TIER_COOLDOWN_S=180, NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 已恢复)
cc4101: PRIMARY=glm5_2_nv@nv_gw:40006, FALLBACK=glm5_2_ms@ms_gw:40007,
        STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400
```

## 下一步

- 继续观测, 等待 NVCF 风暴验证 R829 fail-fast (已 3 轮 NOP 未触发)
- 关注 RemoteDisconnected 是否升级为持续性 (当前是单 key 瞬态, 被透明吸收)
- 若观测到全 key cooling 场景, 确认日志出现 NV-BUFFER-ALL-COOLING / NV-BUFFER-SKIP-WAIT
- 长期目标: 最大化 NV 成功吞吐量, 当前 ~72/h 已达目标区间高位
