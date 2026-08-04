# R1016: 529 风暴第 7 轮 — NOP (integrate lane 观察期, 样本不足不扩量)

> 时间: 2026-08-05 04:35 BJT (20:35 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 via NVCF)
> 状态: **NOP (不改参数)** — R1015 k5 integrate lane 观察期, 样本不足
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/超时触发)

## 1. 背景 (改前必有数据)

R1015 (25min 前) 启用了 `NV_KEY_INTEGRATE_KEYS=dsv4f0731_nv:5` (R838B per-key lane), 为
dsv4f0731_nv 增加第二条 NVCF 通路 (integrate.api)。本轮是 R1015 部署后的首个完整观察轮。

### DB 30min 窗口 (mapped_model=dsv4f0731_nv)
- 总量 25, 200=20, **SR=80.0%** (R1014=71.9%, 风暴期波动回升)
- 502=5 (all_tiers_exhausted=5)
- 429: 0, key_cycle_429s: k0=13, k2=4, k4=4, k3=2, k1=1 (请求级 cycle 计数)
- Avg/P50/P95: 22495ms / 31387ms / 74094ms
- upstream: nvcf_pexec 23 (200=18), nv_integrate 2 (200=**2**)

### per-key 200 延迟 (30min)
| key | n | avg_ms | max(近似p) |
|-----|---|--------|-----------|
| 0 | 4 | 28318 | 62703 |
| 1 | 2 | 19506 | 23345 |
| 2 | 7 | 25208 | 37690 |
| 3 | 4 | 45956 | 91729 |
| 4 | 3 | 24941 | 36218 |

- k3 avg 最高 (45956ms), 但仅 4 样本, 方差大, 不构成劣化铁证
- 5 个 all_tiers_exhausted 全落在 k0 — 这是 key 循环最后失败 key 的归属, 非 k0 特有问题

### 2h 趋势 (nv_tier_attempts, tier=dsv4f0731_nv) — 风暴未收敛
| error_type | cnt | avg_ms |
|------------|-----|--------|
| **529_nv_overloaded** | **377** | - |
| NVCFPexecRemoteDisconnected | 30 | 37063 |
| 529_integrate_overloaded | 3 | - |
| empty_200 | 2 | - |
| NVCFPexecTimeout | 1 | 90534 |

- **529_nv_overloaded 仍绝对主导 (377/2h)** → 账户级过载风暴持续第 7 轮, 未收敛
- 2h 请求级 SR: 78% (117/150), avg 32216ms

### 3h upstream 对比
| upstream | total | ok | SR | avg_ms | p50 |
|----------|-------|----|----|--------|-----|
| nv_integrate | 2 | 2 | **100%** | 18368 | 18368 |
| nvcf_pexec | 160 | 118 | 73.8% | 30303 | 23439 |

- integrate 2/2 成功, avg 18.4s 优于 pexec avg — **但仅 2 样本, 不可作为扩量依据**
- R1015 记录 integrate 30min 内 5 次 lane 触发 (2 成功 / 2 529 / 1 SSL)

## 2. 决策: NOP (不改参数)

**理由:**
1. **R1015 变更仅 25min, integrate 样本不足 (2/2)** — 扩量风险 > 收益。需一整窗观察
   integrate vs pexec SR 对比后再决定是否扩 `NV_KEY_INTEGRATE_KEYS` 到 `:5,4` 等。
2. **529 风暴未收敛 (377/2h)** — 账户级过载, R1010-R1014 已 5 轮数据反证本容器可调参数无效。
3. **无新劣化信号** — per-key 延迟方差 / k3 偏高均属正常风暴波动, 429=0, 无 NVStream_IncompleteRead。
4. **一次只改一个参数** — R1015 刚改 integrate lane, 本轮应让该改动充分沉淀。

## 3. 当前状态 (30min 主指标)

- 30min SR: **80.0%** (20/25)
- Avg/P50/P95: 22495ms / 31387ms / 74094ms
- 错误: all_tiers_exhausted=5 (30min 请求级)
- 429: 0, key_cycle_429s=0
- upstream: pexec 23/200=78.3%, integrate 2/200=100%
- fallback: hm4104 持续 fallback 到 ms_gw (primary 502/超时触发)

## 4. 上次修改效果 (R1015 integrate lane)

- R1015 后 30min SR=80.0% vs R1014 基线 71.9% — 略升 (风暴波动范围)
- integrate lane 已激活: 30min 内 2 次请求全部成功 (avg 18.4s), 且 3h 窗口 2/2=100%
- **但样本过小 (2 请求), 尚不能判定 integrate 持续优于 pexec**
- 529_integrate_overloaded 出现 (3/2h) → integrate 端同样受账户级过载影响, 非银弹

## 5. 验证

- [x] /health: status OK, 5 keys, tiers 含 dsv4f0731_nv
- [x] 容器 Up (未重启)
- [x] env 生效: NV_KEY_INTEGRATE_KEYS=dsv4f0731_nv:5
- [x] integrate lane 真实工作 (2/2 成功)
- [x] 写入仓库 (本 round 文件 + commit)

## 6. 下一步建议

1. **下一轮收集整窗 integrate vs pexec 对比** — 若 integrate SR 持续 ≥ pexec 且样本 ≥10,
   可扩 `NV_KEY_INTEGRATE_KEYS=dsv4f0731_nv:5,4` (k4 加入 integrate 通路)。
2. **529 风暴持续第 7 轮** — 账户级过载, 精确优先级:
   额外 NVCF key / 不同 egress IP 池 / 换 NVCF function_id (dsv4f0731_nv 与 dsv4f_nv 共享 FID
   52e1ddb6)。本容器可调参数已达优化极限。
3. **监控 per-key** — k3 延迟偏高 (45956ms avg) 若持续且样本充足, 考虑将其移出 pexec 高负载路径。