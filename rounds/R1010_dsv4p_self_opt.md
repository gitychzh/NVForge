# R1010: 529 NVCF overload storm — NOP (account-level, backoff harmful)

> 时间: 2026-08-05 02:43 BJT (18:43 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: NOP (不改参数)
> Fallback: hm4104 primary 故障/超时, 已 fallback 到 dsv4f0731_ms; 本轮观察窗口内恢复

## 1. 背景 (改前必有数据)

本容器在 R-dsv4f0731-fix (02:32) 修复了 100% 404 model 名缺陷后回归工作。
随后在 02:37-02:41 遭遇 **NVCF 529_nv_overloaded 账户级过载风暴**。

### 容器日志铁证 (02:37-02:42)
```
[NV-CYCLE] tier=dsv4f0731_nv k4 → 529 (529_nv_overloaded), cycling to next key
[NV-CYCLE] tier=dsv4f0731_nv k5 → 529 (529_nv_overloaded), cycling to next key
[NV-TIER-FAIL] tier=dsv4f0731_nv all 5 keys failed: 429=0, empty200=0, timeout=0, other=7, elapsed=19043ms
[NV-ALL-TIERS-FAIL] All 1 tiers failed ... ABORT-NO-FALLBACK
[NV-CONN] tier=dsv4f0731_nv k2 connection error: Remote end closed connection without response
[NV-CONN-BREAK] tier=dsv4f0731_nv 2 consecutive connection errors → fast-break
```
- 5 key 全部 529/连接错误, 无 429 (429=0), key_cycle_429s=0
- 每次 ATE 在 13-70s 内耗尽 (远低于 180s budget = 快速 cycle 路径)
- 同时伴随 SSLEOFError (mihomo SOCKS5 层) 与 connection errors

### DB (12min 窗口, status 计数)
| 期段 | 200 | 502 |
|------|-----|-----|
| 02:30-02:41 (风暴中) | 15 | 8 |
| 02:42 (恢复) | 2 | 1 |

### 恢复证据
```
[02:42:01] [NV-SUCCESS] tier=dsv4f0731_nv k5 succeeded after 6 cycle attempts
[02:42:37] [NV-SUCCESS] tier=dsv4f0731_nv k5 succeeded after 3 cycle attempts
```
风暴发散中, 522→200 收敛, 请求在 6/3 次 cycle 后命中成功 key。

## 2. 根因定性

**529_nv_overloaded 是 NVCF 账户级持续过载, 非本容器可调参数可解决。**

既有 round 已两次数据证实:
- `R-dsv4f-backoff-revert` (08-04): Adaptive+2s backoff → SR 80%→60%, 延迟+40%。
  **backoff 有害无益** — NVCF 529 在 budget 内不恢复, 快速换 key (0ms) 反而能多试增加命中概率。
- `R-dsv4f-529-backoff-nop` (08-05): 15s tier-DEGRADED backoff 方案同样被既有数据否决, 采纳 NOP。

## 3. 决策: NOP (不改参数)

- 当前 529 是 NVCF 侧过载, 非容器参数缺陷。
- 参数已是最优 (R-dsv4f-adaptive: pexec-first + 快速 cycle + keymgr 429 cooldown 120s)。
- 任何 backoff/退避改动都有 SR 下降风险 (既有数据反证)。
- 风暴已开始收敛 (02:42 success 恢复), 无需干预。

## 4. 当前状态 (改前 30min 主指标, 含风暴期)

- 30min SR: 26 请求, 14 成功 = **53.8%** (风暴期拖低)
- 错误: all_tiers_exhausted=11, NVStream_IncompleteRead=1
- 429: 0 (请求级), key_cycle_429s: k0=19, k1=2, k3=2, k4=3 (cycle 计数, 非 429)
- upstream: 全 nvcf_pexec (integrate 已清空, R1006)
- fallback: hm4104 在风暴期触发 (502 → ms_gw), 恢复期已停止

## 5. 验证
- [x] /health: status OK, 5 keys, tiers 含 dsv4f0731_nv
- [x] 容器 Up (未重启)
- [x] 02:42 后 200 恢复 (风暴收敛)
- [ ] 30min 后: 若 SR 回升 >80% 确认风暴已过

## 6. 上次修改效果 (R-dsv4f0731-fix)
- 修复 dsv4f0731_nv model 名 404 (deepseek-v4-flash-0731 → deepseek-v4-flash)
- 效果: 100% 404 → 可成功 (02:36 首竿成功), 后遭 529 风暴
- 修复正确, 404 缺陷已消除

## 7. 下一步建议
- 若 529 风暴持续影响 SR, 优先级在**上游侧**: 额外 NVCF key / 不同 egress IP / 换 FID,
  而非本容器退避逻辑。
- 下一轮: 常规 30min 窗口回归, 确认 SR 恢复到 ~82% (与 dsv4f_nv 对齐)。
- 观察 hm4104 fallback 是否随风暴收敛而停止。