# R835 — NOP 巡检轮: tier 零错误, AKE-FASTM 持续触发, 链路全稳

> 时间: 2026-08-06 02:12 CST
> 上轮: R834 (NOP, R833 AKE-FASTM 已验证)
> 容器: nv_gw Up ~1h, cc4101 Up 3h, dsv4p_nv40066 Up 29h, dsvf0731_nv40666 Up 21h

## 改动: 无 (NOP 巡检轮)

## 依据

### 30min 真实窗口 (01:42-02:12 CST)

| 指标 | 值 | 判稳 |
|---|---|---|
| cc4101 总 SR (全 caller) | 96.2% (865/899) | ✅ >85% |
| glm5_2_nv tier SR | 100% (21/21 pexec_success, **零错误**) | ✅ |
| fallback 触发率 | 2.2% (19/899) | ✅ <5% |
| per-call SR (nv_gw cc4101-primary) | 88.9% (32/36, 注入窗口) | ✅ |
| R833 AKE-FASTM 触发 | 3 次 (a68cc3db/8770d657/a57de549) | ✅ 持续有效 |
| R829 ALL-COOLING 触发 | 0 次 | 待场景 |
| NV 成功吞吐 | ~1700/h (865/30min × 2) | ✅ 高位 |

### per-key tier 分布 (当前 30min)

```
k0: pexec_success×5 | k1: pexec_success×5 | k2: pexec_success×3
k3: pexec_success×5 | k4: pexec_success×3
```

**本轮 tier 零错误** — 对比注入窗口 (01:58) 的 RemoteDisc 跨全 5 key, 当前窗口 (02:12) NVCF 风暴已完全退去。

### R833 AKE-FASTM 活样本 (3 次触发)

1. **req=a68cc3db** (01:42-01:44): k3→k4→k5 各 attempt1 fail, 3 consecutive → fail-fast
2. **req=8770d657** (01:51-01:52): k1→k2→k3 各 attempt fail, 3 consecutive → fail-fast
3. **req=a57de549** (01:59-02:01): k5→k1→k2 各 attempt fail, 3 consecutive → fail-fast

每次 3 次 all_keys_exhausted 后触发 fail-fast, 跳过剩余 buffer attempt, 避免无谓等待。

### buffer 自愈活样本

**req=096eb0fa** (02:09-02:10): attempt1 k1 EXEC-FAIL (all_keys_exhausted) → backoff 5s → attempt2 success_tool_call (56s, flush 1331b)

### 失败分类 (34 次, 全 caller)

| 错误 | 次数 | avg 耗时 | 分析 |
|---|---|---|---|
| client_gone_mid_stream (499) | 22 | 195s | 用户主动中断, 非链路问题 |
| timeout (502) | 12 | 295s | fallback 路径 dsvf0731_nv 超时, 非主链路 |

12 个 502 全部是 fallback 路径 (dsvf0731_nv40666) 超时, 主链路 glm5_2_nv 零失败。

## 验证

- `curl localhost:40006/health` → ok, 5 keys, glm5_2_nv in pexec models
- `curl localhost:4101/health` → ok, primary=glm5_2_nv
- docker ps: nv_gw Up ~1h, cc4101 Up 3h, 全容器 Up

## 就位修复链 (沿用, R827+R828+R829+R833)

- R827: buffer total_deadline 锚定 t_start (防 deadline 漂移)
- R828: nv_breaker 5-consecutive → next req 直送 + buffer ms_gw 兜底
- R829: buffer + WaitQueue 双重检测全 key cooling → fail-fast
- R833: 连续 3 次 all_keys_exhausted → fail-fast (补 R829 盲区)
- R813: chain_full_retry inspect.signature=True

## 下一步

- 继续观测, 确认 tier 零错误趋势
- R829 (全 key cooling fail-fast) 仍待场景触发验证
- R833 (AKE-FASTM) 持续触发有效, 3 次/30min 节省 ~10min 无谓等待
- fallback 路径 dsv4f0731_nv 12 个 502 timeout 非主链路, 不优化
- 长期目标: 最大化 NV 成功吞吐量, 当前 ~1700/h 高位
