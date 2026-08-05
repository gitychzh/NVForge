# R1031: RemoteDisconnected 风暴延续 (第10轮) — 模型特异性劣化持续, 无参数修改 (恢复观察轮)

> 时间: 2026-08-05 11:22 BJT (03:22 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 flash via NVCF)
> 状态: **恢复观察轮 (无参数修改)** — NVCFPexecRemoteDisconnected 远程瞬断持续绝对主导,
>   且第 10 次复现**模型特异性** (同容器同 key 同出口 glm5_2_nv 100% 成功) → NVCF
>   deepseek-v4-flash function 级劣化, 无本容器可解参数
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502/RemoteDisconnected 触发)

## 1. 背景 (改前必有数据)

R1021-R1030 已连续记录同一 RemoteDisconnected 风暴并判定模型特异性 NOP。本轮 (间隔 ~17min)
为**同一风暴第 10 轮延续**, 数据完全复现 R1030 结论。

### 30min 窗口 — nv_requests (采集脚本, tier_model=dsv4f0731_nv)
- 总量 11, 200=4, 502=7, **SR=36.4%** (窗口内业务流量少, 波动大)
- Avg: 95617ms (慢失败烧满预算后 502)
- 429: 0 (key_cycle_429s 0=9/1=2, 非 429 主导)
- upstream_type: nvcf_pexec 11/200=4 (全 pexec, integrate 0)
- 错误分类: all_tiers_exhausted=7
- finish_reason: stop=2, tool_calls=2

### 1h tier_attempts 失败细分 (per-attempt 层, dsv4f0731_nv)
- **NVCFPexecRemoteDisconnected: 27 (绝对主导, avg ~40s, 烧 90s 预算)**
- empty_200: 7, 529_nv_overloaded: 2, NVCFPexecTimeout: 2

### ⭐ 关键证据 — 模型特异性第 10 次复现 (同容器同窗 1h, 请求层)
| tier_model | total | ok | SR |
|---|---|---|---|
| glm5_2_nv    | 171 | 171 | **100%** |
| dsv4f0731_nv |  25 |  11 | **44.0%** |

- 同一容器、同一 5 组 NVU_KEY、同一 5 个 mihomo 出口 (7894/7895/7896/7897/7904)
- glm5_2_nv 同链路 171/171=100% 成功 → 故障隔离到 deepseek-v4-flash 的具体 NVCF function
- 证据第 10 次成立, 变量隔离彻底干净

### per-key 均匀劣化 (非单 key 问题)
- 5 key 各有 RemoteDisconnected (14/20/21/19/17), 均匀分布 → 非单 key/proxy 问题
- 每 key 失败均烧尽 5 key → all_tiers_exhausted (请求层 30min=7, 24h=126)
- key_cycle_429s 低, 非 429 主导

### 6h 趋势 (请求层)
- 6h 累积: 207 请求 129 成功 (62.3%)
- 3h 逐小时 SR: 00:00=63.6%, 01:00=38.1%, 02:00=50.0%, 03:00=28.6%
- SR 持续低位波动, 风暴未缓解

## 2. 决策: NOP (无参数修改)

RemoteDisconnected 是 NVCF deepseek-v4-flash **远程 function 级**瞬断, 与容器 env 无关:
- 同出口同 key 下 glm5_2_nv 171/171=100% 成功 → 网络/mihomo/key/出口路径全部健康
- 故障仅存在于 dsv4f0731_nv 具体 function 的远端执行层
- 调 FASTBREAK / cooldown / budget 均无 lever (键已因远端断连而烧尽, 非本地策略问题)

本轮继续 NOP, 等待 NVCF 侧恢复 (第 10 轮)。

## 3. 修改

无。参数保持: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, FASTBREAK_PEXEC=3, FASTBREAK_EMPTY_200=3.

## 4. 验证

- /health: status ok, 5 keys, dsv4f0731_nv 在列
- 容器 dsvf0731_nv40666 Up 6h
- 无参数变更, 无重启

## 5. 下一步建议

- 持续观察 NVCF 侧是否恢复 (RemoteDisconnected 计数下降)
- 若连续更多轮维持 0 成功, 考虑与 HM1 侧协商是否临时将 hermes 主链切到 glm5_2_nv
  或允许 hm4104 长期 fallback dsv4f0731_ms (已自动生效, fallback 日志证实)
- 恢复后下一轮再评估是否有真实可调的参数优化空间