# R1011: NOP 轮 — 链路健康, 无参数修改

> 时间: 2026-08-07 17:12 UTC (01:12 BJT+1)
> 容器: dsvf0731_nv40666 (端口 40666, HM2 本机)
> 模型: dsv4f0731_nv (DeepSeek V4 Pro via NVCF pexec)

## 1. 数据 (改前必有数据)

### 30min 窗口主指标 (ts > NOW()-30min)
- **总量**: 159, **成功**: 157, **失败**: 2, **429**: 0
- **成功率**: 157/159 = **98.7%**
- **延迟**: avg=11326ms, ttfb=8454ms (注意: 脚本输出的 p50/p95 格式不同, avg=11326, p50=8454, p95=21670, 最后一个值 82565 是 max)
- **错误分布**: all_tiers_exhausted=1 (180074ms), zombie_empty_completion=1 (7050ms)
- **finish_reason**: tool_calls=137, stop=20 (正常, 以工具调用为主, 87.4% tool_calls)

### Per-key 200 延迟 (30min) — k0 略高但正常

| key | s200 | avg_ms | p95_ms |
|-----|------|--------|--------|
| 0 | 33 | 13618 | 38665 |
| 1 | 32 | 10201 | 18687 |
| 2 | 31 | 8856 | 13054 |
| 3 | 30 | 10141 | 19894 |
| 4 | 31 | 8361 | 13340 |

k0 的 p95=38665 (38.6s) 明显高于其他 key 的 13-20s, 且 k0 上产生了 1 ATE + 1 zombie。但 k0 仍有 33 次成功, 不是完全瘫痪。可能是 k0 对应的 SOCKS5 出口偶尔劣化。

### Per-key 错误 (30min)
- k0: all_tiers_exhausted=1 (180074ms), zombie_empty_completion=1 (7050ms)
- 其余 key 无错误

### key_cycle_429s (30min)
- k1=112 (高! 已在 R1010 标注观察)
- k2=46
- k3=1
- k0/k4=0
- k1 和上次一样 cycle 计数高但成功 32 次, 说明 k1 常被限流但不影响 SR

### 6h 趋势
- 1652 total, 1610 s200, 42 ate, 0 429 → **SR=97.5%**

### 3h 逐小时趋势
| hour (UTC) | total | s200 | ate | 429 | avg_ms |
|-----------|-------|------|-----|-----|--------|
| 09:00 | 89 | 89 | 0 | 0 | 9,503 |
| 08:00 | 260 | 251 | 9 | 0 | 12,495 |
| 07:00 | 262 | 253 | 9 | 0 | 12,557 |
| 06:00 | 216 | 211 | 5 | 0 | 15,033 |

趋势: **91.8% (R1010 23:00) → 97.2% (R1010 01:00) → 97.5% (R1011 6h) → 98.7% (R1011 30min)**. 成功率持续走高。

### 24h all_tiers_exhausted
- **321** (显著低于 R1010 的 453, 下降 29%)

### upstream_type (30min)
- nvcf_pexec: 159 (全部 pexec, ok=157, 成功 98.7%)
- 无 integrate, 无 ms_fallback

### hm4104 fallback 日志 (最近 5min)
- **(无 fallback 日志)** — 比 R1010 更好, hm4104 主链路完全稳定

### /health
- status=ok, 5 keys, 6 models, proxy_role=passthrough, 端口 40666
- 容器 Up 24h (比 R1010 的 16h 多 8h, 连续运行无重启)

## 2. 结论: NOP

按 NOP 规则 (SR>95%, 无异常错误, 延迟稳定), 本轮判定为**健康轮**, 不修改任何参数.

- 30min SR = **98.7%** > 95% ✓ (比 R1010 的 96.8% 提升 +1.9pp)
- 零 429 ✓
- 零 pexec timeout ✓
- Per-key 延迟: k0 略高但仍有 33 成功, 整体正常 ✓
- 24h ATE 从 453 (R1010) → 321 (R1011), 下降 29% ✓
- hm4104 无 fallback 日志 ✓
- 3h 逐小时趋势持续改善 ✓

## 3. 观察项 (下一轮关注, 不立即改)

1. **k0 p95=38665ms (38.6s)** — 其他 key 均 <20s, k0 响应偏慢. 若 k0 持续劣化 (ATE 集中在 k0 或 200 数下降), 考虑调高 k0 对应 SOCKS5 出口的冷却权重. 当前仅 1 ATE + 1 zombie, 不足以触发修改.
2. **k1 key_cycle_429s=112** (与 R1010 的 121 基本持平) — k1 频繁被限流. 再次确认对 SR 无实质影响, 持续观察.
3. **NVU_KEYMGR_429_BASE_COOLDOWN=120 == MAX=120** — 无退避阶梯. R1009 已调过, 当前 SR 优异, 不动.

## 4. 验证清单
- [x] /health = ok, 5 keys, 6 models, port 40666
- [x] 容器 Up 24h, 无重启 (`dsvf0731_nv40666 Up 24 hours`)
- [x] 所有 R1009 参数 (NVU_KEYMGR_429_MAX_COOLDOWN=120, TIER_COOLDOWN=90 等) 在 env 确认生效

## 5. 参数演化历史

| Round | 参数 | 旧→新 | 效果 |
|-------|------|-------|------|
| R1006 | NV_KEY_INTEGRATE_KEYS | dsv4p_nv:3→空 | 消除 integrate 0% SR 浪费 |
| R1007 | TIER_COOLDOWN_S | 180→90 | 缩短 tier 级冻结 |
| R1008 | MIN_OUTBOUND_INTERVAL_S | 1.5→5 | 延缓 429 到达 |
| R1009 | NVU_KEYMGR_429_MAX_COOLDOWN | 300→120 | 消除全 key 429 后 300s 黑屏 |
| R1010 | **NOP** | — | 链路健康 (96.8%), 无修改 |
| **R1011** | **NOP** | — | 链路更健康 (98.7%), 无修改 |

## 6. 下一步建议

- 链路持续改善中: R1008(R1007) 降低 TIER_COOLDOWN 至 90 和 R1009 降低 429_MAX_COOLDOWN 至 120 的效果仍在显现. 继续观察 24h ATE 趋势 (453→321, -29%).
- 若未来 24h ATE < 200 → 可以考虑进一步降低 NVU_KEYMGR_429_BASE_COOLDOWN (120→90) 以恢复退避阶梯, 让轻度 429 使用短冷却.
- 若 k0 持续劣化 → 后续关注 k0 对应 SOCKS5 proxy (port 7897) 的健康状态.