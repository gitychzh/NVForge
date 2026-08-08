# RN1060: NOP — 链路健康 (SR 99.15%)，错误位回到 k3 分布式 zombie (追踪中的 k2 IncompleteRead 本轮未现)，不改参数

日期: 2026-08-08 10:48 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1048~RN1059 健康稳态延续。本窗口 **SR 99.15% (117/118)**，唯一事件为 **k3 `zombie_empty_completion` (5084ms)**。

这是 RN1059 已确立的**分布式 NVCF-side zombie 模式**的延续：上一轮 24h 全量审计显示 `zombie_empty_completion` 分布于全部 5 key (k0=7, k2=6, k4=6, k3=5, k1=4)，单 key 速率 ~0.1/时，非 key 聚集。本窗口落在 k3，与 RN1059 的 02:38 k3 zombie 呼应，仍属随机空响应的稀疏噪声。

**关键信号：RN1055~1059 连续追踪的 k2 定值 (38288ms) NVStream_IncompleteRead 本轮未再现。** 表明该"持久性稀疏"事件窗口内没有升级为聚集 (≥3/30min)，且本窗口唯一错误位返回了 k3 zombie，进一步支持"全部为 NVCF 端分布式随机残留、与 key/代理/参数无关"的判定。

守"改前必有数据"+"一次只改一个参数"铁律。对分布式稀疏残留调超时/预算/冷却/快断均无原理性收益（RN1048~1059 已反复论证），且会扰动当前稳定健康区间 → **不动作**。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **99.15%** (117/118, 1 error, 0 timeout) |
| 错误 / Fallback | **zombie_empty_completion 1 @ k3 (5084ms) / 0** |
| Avg / P50 / P95 / Max | 17111 / 12100 / 45744 / 74180 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 118/118 (100%) — 无 integrate |
| finish_reason | tool_calls 95, stop 22 |

**Per-key 200 延迟**（30min 直查，5 key 负载/延迟均匀）:
```
key0|22req|avg16546|P5038885
key1|23req|avg14648|P5031147   ← 负载/延迟最低
key2|24req|avg17945|P5048870   ← 本窗口无 IncompleteRead（追踪信号未现）
key3|24req|avg17805|P5050716   ← 1 error zombie 5084ms（RN1059 02:38 k3 zombie 延续）
key4|24req|avg18961|P5044664
```
Key 间负载均匀 (22-24 req)、延迟同量级 (14.6-19.0s avg)。单点错误对全局无统计影响。tier_attempts 空（0 key 循环失败），key_cycle_429s=0|34,1|83,2|1 属噪声，429=0 验明无压力。

## 趋势

- **6h**: 1742/1737 → **SR=99.71%**（5 失败为稀疏残留）
- **3h 逐小时**: 02:00 190/189 (99.5%), 01:00 236/235 (99.6%), 00:00 310/310 (100%), 23:00 63/63 (100%) — 整点小时基本全 100%
- **24h all_tiers_exhausted**: 32（较上轮 32 持平，已自 36→35→32 走低，陈旧累积口径在滚动甩走）

## 容器状态

`dsvf0731_nv40666` Up 8 hours；`nv_gw` Up 31h；`hm4104` Up 3 days；`nv_gw_stable` Up 6d。`/health` ok，proxy_role=passthrough，nv_num_keys=5，dsv4f0731_nv 在 nvcf_pexec_models。

## hm4104 fallback 日志（非本容器问题）

最近 5min fallback 日志为空，本窗口无 fallback 信号。备案同前。

## 修改记录

无（NOP）。维持当前参数（env 实测）：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3, NVU_KEYMGR_429_{BASE,MAX}_COOLDOWN=120, NVU_KEYMGR_CONN_{BASE,MAX,LONG}_COOLDOWN=30/60/120, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3。

## 下一步建议

- **追踪信号 k2 IncompleteRead 本轮未现**（RN1055~1059 连续 5 轮后中断）。按 RN1057 预设，其未升级为"≥5 轮连续"（本轮 0 次已重置连续计数），也未达窗口聚集阈值 → 该信号降级为观察项，暂不启动 k2 → 7904 SOCKS5 / 出口 IP 排查。若再度出现 ≥3/30min，再启动链路排查。
- **zombie_empty_completion 持续为 24h 分布式噪声新主角**（全部 5 key 皆有，随机散布）。跨全部 key 且无聚集，判定为 NVCF 端随机空响应，非本容器可控参数可改善；持续交叉核验但无需为此调参。
- 继续观察 24h all_tiers_exhausted（当前 32，持平/走低即健康）。
- 链路稳定则持续 NOP。