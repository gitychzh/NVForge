# R1030: RemoteDisconnected 风暴延续 (第9轮) — 模型特异性劣化持续, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 11:05 BJT (03:05 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断持续绝对主导,
>   且第 9 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 100% 成功) → NVCF
>   deepseek-v4-flash function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/RemoteDisconnected 触发)

## 1. 背景 (改前必有数据)

R1021-R1029 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~13min)
为**同一风暴第 9 轮延续**, 数据完全复现 R1029 结论。

### 30min 窗口 — nv_requests (采集脚本, tier_model=dsv4f0731_nv)
- 总量 13, 200=7, 502=6, **SR=53.8%** (窗口内业务流量少, 波动大)
- Avg: 65524ms
- 429: 0 (key_cycle_429s 0=11/1=2, 非 429 主导)
- upstream_type: nvcf_pexec 13/200=7 (全 pexec, integrate 0)
- 错误分类: all_tiers_exhausted=5, NVStream_IncompleteRead=1
- finish_reason: stop=3, tool_calls=4
- 30min 内 8 个 status=200 请求 duration_ms>60000 (慢成功, 非失败)

### 1h tier_attempts 失败细分 (per-attempt 层, dsv4f0731_nv)
- **NVCFPexecRemoteDisconnected: 14 (绝对主导, avg ~40s, 烧近 90s 预算)**
- empty_200: 3, 529_nv_overloaded: 1

### ⭐ 关键证据 — 模型特异性第 9 次复现 (同容器同窗 1h, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    | 163 | 163 | **100%** |
| dsv4f0731_nv |  28 |  13 | **46.4%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- glm5_2_nv 同链路 100% 成功 → 故障隔离到 deepseek-v4-flash 的具体 NVCF function
- 6h 逐小时: glm5_2_nv 每小时全 100% (155/157/189/150/155/20), dsv4f0731_nv 46-52%
- 证据第 9 次成立, 变量隔离彻底干净

### per-key 均匀劣化 (非单 key 问题)
- 30min per-key 200 延迟: 0:4@73465, 3:1@28853, 4:2@21094 — 各 key 均偶有成功
- 每 key 失败均烧尽 5 key → all_tiers_exhausted (请求层 30min=5, 24h=121)
- key_cycle_429s 低, 非 429 主导

### 6h 趋势 (请求层)
- 6h 累积: 208 请求 130 成功 (62.5%)
- dsv4f0731_nv 逐小时 SR: 21:00=57.6%, 22:00=84.2%, 23:00=54.3%, 00:00=65.6%, 01:00=36.4%, 02:00=50.0%
  — 风暴全程低位波动, 未缓解

## 2. 决策: NOP (无参数修改)

RemoteDisconnected 是 NVCF deepseek-v4-flash **远程 function 级**瞬断, 与容器 env 无关:
- 同出口同 key 下 glm5_2_nv 163/163=100% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- 调 FASTBREAK / cooldown / budget 均无 lever (键已因远端断连而烧尽, 非本地策略问题)

本轮继续 NOP, 等待 NVCF 侧恢复 (第 9 轮)。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, FASTBREAK_PEXEC=3, FASTBREAK_EMPTY_200=3.

## 4. 验证

- /health: status ok, 5 keys, dsv4f0731_nv 在列
- 容器 dsvf0731_nv40666 Up 5h
- 无参数变更, 无重启

## 5. 下一步建议

- 持续观察 NVCF 侧是否恢复 (RemoteDisconnected 计数下降)
- 若连续更多轮维持 0 成功, 考虑与 HM1 侧协商是否临时将 hermes 主链切到 glm5_2_nv
  或允许 hm4104 长期 fallback dsv4f0731_ms (已自动生效, fallback 日志证实)
- 恢复后下一轮再评估是否有真实可调的参数优化空间