# R1010: NOP 轮 — 链路健康, 无参数修改

> 时间: 2026-08-07 09:42 UTC (17:42 BJT)
> 容器: dsvf0731_nv40666 (端口 40666, HM2 本机)
> 模型: dsv4f0731_nv (DeepSeek V4 Pro via NVCF pexec)

## 1. 数据 (改前必有数据)

### 30min 窗口主指标 (ts > NOW()-30min)
- **总量**: 127, **成功**: 123, **失败**: 4, **429**: 0
- **成功率**: 123/127 = **96.8%**
- **延迟**: avg=14551ms, ttfb=9180ms, p50=18088ms, p95=180041ms
  - p95=180s 由 3 次 all_tiers_exhausted (每 180045ms) 拉高; 正常请求 p50≈18s 属 pexec 正常范围
- **错误分布**: all_tiers_exhausted=3, stream_absolute_cap=1
- **finish_reason**: tool_calls=106, stop=17 (正常, 以工具调用为主)

### Per-key 200 延迟 (30min) — 均匀无劣化
| key | s200 | avg_ms | p95_ms |
|-----|------|--------|--------|
| 0 | 25 | 9623 | 14064 |
| 1 | 24 | 8345 | 11973 |
| 2 | 25 | 9629 | 13780 |
| 3 | 25 | 8962 | 13427 |
| 4 | 24 | 10158 | 12723 |

5 key 延迟高度一致 (8.3-10.2s), 无单 key 劣化.

### Per-key 错误 (30min)
- k0: all_tiers_exhausted=3 (180045ms)
- k3: stream_absolute_cap=1 (158341ms)
- 其余 key 无错误

### key_cycle_429s (30min)
- k1=121 (高!), k0=5, k3=1
- 注意: k1 虽 429 循环次数高 (121), 但仍取得 24 次成功且延迟最低 (avg 8345ms). 说明 k1 常被限流但成功时很快, 由其他 key 分担负载, 不影响 SR.

### 3h 逐小时趋势
| hour | total | s200 | ate | sr_pct |
|------|-------|------|-----|--------|
| 01:00 | 180 | 175 | 5 | 97.2% |
| 00:00 | 291 | 282 | 9 | 96.9% |
| 23:00 | 208 | 191 | 17 | 91.8% |
| 22:00 | 83 | 78 | 5 | 94.0% |

趋势改善: 91.8% → 96.9% → 97.2%. 最近窗口已稳定 >96%.

### 6h 趋势
- 1370 total, 1288 s200, 82 ate, 0 429 → **SR=94.0%**

### 24h all_tiers_exhausted
- 453 (峰值在前半段, 近 3h 仅 29 次, 已显著回落)

### upstream_type
- 3h: nvcf_pexec 765 (734 ok, 95.9%), 空 4
- 24h: nvcf_pexec 2306, ms_fallback 154, nv_integrate 24, 空 42
- integrate 已基本闲置 (24/24h), pexec 承担全部负载且工作正常

### hm4104 fallback 日志 (最近 5min)
- 09:35-09:38 出现 `FALLBACK-STREAM` + `PRIMARY-BREAKER-SKIP-STREAM` (circuit OPEN)
- 这是 hm4104 适配器 → nv_gw(40006) 主链路短暂打不开, 切到 ms_gw
- 属瞬时事件, 与容器当前 96.8% SR 不冲突; 30min 窗口无持续故障

## 2. 结论: NOP

按 NOP 规则 (SR>95%, 无异常错误, 延迟稳定), 本轮判定为**健康轮**, 不修改任何参数.

- 30min SR = 96.8% > 95% ✓
- Per-key 延迟均匀 (8-10s), 无单 key 劣化 ✓
- 30min 错误仅 4 (3 ATE + 1 stream_cap), 无异常 ✓
- R1009 (429_MAX_COOLDOWN 300→120) 生效, 黑屏已消除, 3h 趋势持续改善 ✓
- integrate 已空转, pexec 稳定承载 ✓

## 3. 观察项 (下一轮关注, 不立即改)

1. **NVU_KEYMGR_429_BASE_COOLDOWN=120 == MAX=120** — 429 冷却无退避递增 (base=max). R1009 已提示此点. 当前 SR 正常暂不动; 若未来 ATE 再抬升, 可考虑 BASE 降到 60-90 恢复退避阶梯.
2. **k1 key_cycle_429s=121 (30min)** — k1 频繁被 NVCF 限流但成功时快. 若未来 k1 错误/延迟恶化, 考虑调高 k1 对应 SOCKS5 出口或降低其优先级.
3. **hm4104 fallback 瞬时触发** — 主链路 circuit OPEN 是瞬时事件, 与容器健康不直接冲突, 持续观察.

## 4. 验证清单
- [x] /health = ok, 5 keys, 6 models (含 dsv4f0731_nv)
- [x] 容器 Up 16h, 无重启
- [x] R1009 参数 (NVU_KEYMGR_429_MAX_COOLDOWN=120, TIER_COOLDOWN=90) 在 env 确认生效

## 5. 参数演化历史
| Round | 参数 | 旧→新 | 效果 |
|-------|------|-------|------|
| R1006 | NV_KEY_INTEGRATE_KEYS | dsv4p_nv:3→空 | 消除 integrate 0% SR 浪费 |
| R1007 | TIER_COOLDOWN_S | 180→90 | 缩短 tier 级冻结 |
| R1008 | MIN_OUTBOUND_INTERVAL_S | 1.5→5 | 延缓 429 到达 |
| R1009 | NVU_KEYMGR_429_MAX_COOLDOWN | 300→120 | 消除全 key 429 后 300s 黑屏 |
| **R1010** | **NOP** | — | 链路健康, 无修改 |

## 6. 下一步建议
- 持续观察 24h ATE 是否维持在低水平 (<50/24h)
- 若 ATE 抬升: 调整 NVU_KEYMGR_429_BASE_COOLDOWN (120→60-90) 恢复退避阶梯, 减少全 key 同步进入长冷却
- 若 k1 持续高 429 循环且延迟恶化: 评估 k1 出口降权