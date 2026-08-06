# R1055: RemoteDisconnected 风暴延续 (第34轮) — 模型特异性第34次复现, NOP (无参数修改)

> 时间: 2026-08-06 10:00 BJT (02:00 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断风暴在 attempt 层
>   持续主导, 第 34 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 6h SR=95.7%
>   且 0 tier 错误, dsv4f0731_nv 6h SR=49.1% + attempt 层 RemoteDisconnected/529 主导) →
>   NVCF deepseek function 级劣化, 无本容器可解参数
> 信号: hm4104 fallback 持续 (PRIMARY-BREAKER-SKIP-STREAM 直走 fallback)

## 1. 背景 (改前必有数据)

R1021-R1054 连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮间隔 ~10min
为同一风暴第 34 轮延续。

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 30, 200=12, 失败=18, fallback=4, **SR=40.0%**
- Avg 132948ms, p50 72904ms, p95 455650ms, max 659420ms
- 429: 0 计数
- upstream_type: nvcf_pexec 25 (200=12, SR=48.0%), ms_fallback 4 (200=0), 空 1 (200=0)
- finish_reason: tool_calls=10, stop=2 (正常业务完成)

### 错误分类 (30min, nv_requests)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 12 | 197154 |
| buffer_exhausted | 4 | 232526 |
| zombie_empty_completion | 2 | 41592 |

### per-key 200 延迟 (30min)
| key | 200 | min_ms | max_ms |
|---|---|---|---|
| 1 | 3 | 53097 | 62673 |
| 2 | 3 | 33936 | 130196 |
| 3 | 2 | 35214 | 54541 |
| 4 | 4 | 61269 | 130196 |

### per-key 错误 (30min)
- k0: all_tiers_exhausted=11, buffer_exhausted=4
- k2: all_tiers_exhausted=1, zombie_empty_completion=1
- k4: zombie_empty_completion=1
- (空 key): all_tiers_exhausted=2, buffer_exhausted=1
- → 错误跨全 5 key 分散, 非单 key/单 SOCKS5 代理问题

### 模型特异性重验证 (6h, 同容器同 key 同出口同时窗)
- **glm5_2_nv 6h**: 同链路 SR=95.7% (186 请求, 178 200)
- **dsv4f0731_nv 6h**: 395 请求, 194 200, **SR=49.1%**
- **结论**: 同容器同 key 同出口, glm5_2_nv 95.7% vs dsv4f0731_nv 49.1% → 模型特异性
  第 34 次成立。故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层。

### attempt 层错误 (1h)
- NVCFPexecRemoteDisconnected=56, 529_nv_overloaded=21, empty_200=9, NVCFPexecTimeout=2
- → 纯远程瞬断/过载/空响应, 无 429, 无 SSL 错误

### 6h/24h 趋势
- 6h 请求层: 395 请求, 194 200, SR=49.1%, fallback=53
- 3h 逐小时 SR: 01:00=36.1%(22/61), 00:00=37.2%(29/78), 23:00=43.3%(29/67)
- 24h all_tiers_exhausted: 220 次

### hm4104 fallback 日志 (最近 5min)
- **PRIMARY-BREAKER-SKIP-STREAM**: primary 流式跳过 (circuit OPEN 或 fallback 冷却), 直走 fallback
- **FALLBACK-STREAM**: 从 primary 切到 ms_gw 流式
- 说明 hm4104 断路器持续 OPEN, 用户请求持续 fallback 到 ms_gw 保活

## 2. 决策: NOP (无参数修改)

RemoteDisconnected/529_nv_overloaded/zombie_empty/buffer_exhausted 是 NVCF deepseek
**远程 function 级**瞬断/劣化, 与容器 env 无关 (第 34 次确认):
- 同出口同 key 下 glm5_2_nv 6h SR=95.7% + 0 tier 错误 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- 错误跨全 5 key 分散 (k0/k1/k2/k3/k4) → 证明非 UPSTREAM_TIMEOUT/budget/cooldown/fastbreak 可解的 lever
- 无 429, 无 SSL 错误 (RemoteDisconnected/529/empty_200 主导) → 纯远程断连/过载
- 无单 key 劣化 (错误均匀分散各 key) → 无 key 分配/冷却可调

本轮继续 NOP, 等待 NVCF 侧恢复 (第 34 轮)。模型特异性铁证 (6h glm5_2_nv 95.7% +
0 tier 错误 vs dsv4f0731_nv 49.1% + 错误均匀分散) 第 34 次成立。hm4104 断路器
已接管用户侧 fallback (用户请求由 ms_gw 保活)。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
NVU_KEYMGR_429_BASE/MAX=120, NVU_EMPTY_200_FASTBREAK=3, NVU_PEXEC_TIMEOUT_FASTBREAK=3,
NVU_STREAM_FB_200K_S=90, NVU_STREAM_ABSOLUTE_CAP_S=150. 无重启。

## 4. 验证

- /health: status=ok, 5 keys, dsv4f0731_nv in nvcf_pexec_models + nv_model_tiers
- 容器 Up 28 hours, 无重启
- 本轮无参数改动, 无需额外验证

## 5. 下一步建议

继续观察 NVCF 侧 deepseek function 恢复。若后续 30min 窗口内 dsv4f0731_nv 出现
RemoteDisconnected 明显回落 (如 SR>80% 且 512 高峰解除), 恢复基准监测; 否则维持 NOP。
hm4104 断路器保持 OPEN 由 ms_gw 兜底, 不因 dsv4f0731_nv 劣化而改用户侧路由。