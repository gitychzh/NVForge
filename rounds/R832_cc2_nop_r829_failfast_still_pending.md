# R832 — NOP 巡检轮 (R829 fail-fast 第 4 轮未触发)

> 时间: 2026-08-05 20:25 CST
> 上轮: R831 (NOP, R829 fail-fast 待场景)
> 容器: nv_gw Up 44m, cc4101 Up 19h, dsv4p_nv40066 Up 24h

## 改动: 无 (NOP 巡检轮)

R829 (buffer 全 key cooling fail-fast) 已就位。连续 4 轮 NOP (R830/R831/R832) 均未触发
fail-fast (无全 key cooling 场景出现), 链路全稳, 不改码。

## 本轮数据 (20:25 CST 注入窗口)

| 指标 | 值 | 状态 |
|---|---|---|
| cc4101-primary per-call SR | 100% (42/42) | ✅ |
| per-key tier 最终成功 SR | 100% (42/42) | ✅ |
| 用户可见 SR | 100% (零 502 穿透) | ✅ |
| ms_fallback 触发率 | 0% (主链路) | ✅ |
| RemoteDisconnected 瞬态 | ×16 跨全 5 key (被 buffer 轮转吸收) | 透明 |
| R829 fail-fast 触发 | 无 (第 4 轮 NOP 未出现全 key cooling) | 待场景 |
| NV 成功吞吐 | 42req/30min ≈ 84/h | 高位 |

## per-key RemoteDisc 分布 (本轮)

```
k0: success×13, RemoteDisc×5   k1: success×8,  RemoteDisc×3
k2: success×3,  RemoteDisc×3   k3: success×12, RemoteDisc×1, empty_200×1
k4: success×6,  RemoteDisc×4, 529_overloaded×1
```

RemoteDisc 跨全 5 key 均匀分布, 是 NVCF 后端瞬态, 从未同时打挂全 5 key。
k3 出现 1 次 empty_200 (zombie), k4 出现 1 次 529 nv_overloaded — 均单 key 瞬态,
被 buffer 切其他 key 成功吸收。

## 非 cc2 范围 (注入数据, 不处理)

- hermes|dsv4f0731_nv SR=70% (14/20) — hermes caller 另一条链路
- openclaw|dsv4p_nv SR=0% (0/2) — openclaw caller 另一条链路
- all_tiers_exhausted×7 (avg 111s) + zombie_empty_completion×1 — 归属 dsv4f0731, 非 cc2 的 glm5_2_nv

## 就位修复链 (沿用, R827+R828+R829)

- R827: buffer total_deadline 锚定 t_start (防止 deadline 漂移)
- R828: nv_breaker 5-consecutive NV failure → next req 直送 ms_gw + buffer_stream ms_gw 兜底
- R829: buffer for 循环 + WaitQueue 双重检测全 key cooling → fail-fast 跳过无谓重试
- R813: chain_full_retry inspect.signature=True

## 健康检查

- `curl localhost:40006/health` → ok, 5 keys, pexec models 含 glm5_2_nv
- `curl localhost:4101/health` → ok, primary=glm5_2_nv
- docker ps: nv_gw Up 44m, cc4101 Up 19h, dsv4p_nv40066 Up 24h, logs_db Up 6d

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, KeyManager 429→120-600s 指数退避, RemoteDisc→5s 短惩罚,
       TIER_COOLDOWN_S=180, NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 已恢复)
cc4101: PRIMARY=glm5_2_nv@nv_gw:40006, FALLBACK=glm5_2_ms@ms_gw:40007,
        STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400
```

## 下一步

- 继续观测, 等待 NVCF 风暴验证 R829 fail-fast (已 4 轮 NOP 未触发)
- 关注 RemoteDisconnected 是否升级为持续性 (当前是单 key 瞬态, 被透明吸收)
- 若观测到全 key cooling 场景, 确认日志出现 NV-BUFFER-ALL-COOLING / NV-BUFFER-SKIP-WAIT
- 长期目标: 最大化 NV 成功吞吐量, 当前 ~84/h 已达目标区间高位
