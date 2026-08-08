# RN1062: NOP — 链路持续健康 (SR 99.1%)，k3 孤立 zombie 复现，首key 429 被轮转全吸收，不改参数

日期: 2026-08-08 11:04 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DSV4F0731 NVCF 链路)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

RN1048~RN1061 健康稳态延续。本窗口 **SR 99.1% (109/110)**，唯一事件为 **k3 `zombie_empty_completion` (5084ms)**。

与 RN1060/1061 (k3 同 5084ms zombie) 同刻/相邻采集，跨 6h 窗口完全一致：**仅 1 个孤立 zombie，无聚集、无 429 净失败、无 fallback、无 IncompleteRead、无 integrate 流量**。错误位仍落在 k3，属 RN1059 已确立的全部 5 key 分布式 NVCF-side 随机空响应模式，与 key/代理/参数无关。

守"改前必有数据"+"一次只改一个参数"铁律。对分布式稀疏残留调超时/预算/冷却/快断无原理性收益（RN1048~1061 已反复论证），且会扰动当前稳定健康区间 → **不动作**。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **99.1%** (109/110, 1 error, 0 timeout) |
| 错误 / Fallback | **zombie_empty_completion 1 @ k3 (5084ms) / 0** |
| Avg / P50 / P95 | 19178 / 12989 / 56781 ms |
| 429 / timeout | 0 / 0 |
| upstream_type | nvcf_pexec 110/110 (100%) — 无 integrate |
| finish_reason | tool_calls 83, stop 26 |
| 24h all_tiers_exhausted | 32（持平，近 6h 为 0 → 陈旧累积口径在滚动甩走）|

**Per-key 200 延迟**（30min 直查，5 key 负载/延迟均匀）:
```
key0|21req|avg21349|P50 56917
key1|26req|avg19909|P50 72619
key2|16req|avg14996|P50 35468
key3|24req|avg20195|P50 53915   ← 1 error zombie 5084ms (k3 孤立复现)
key4|22req|avg18813|P50 60669
```
Key 间负载均匀 (16-26 req)、延迟基本同量级。单点错误 (1/110) 对全局无统计影响。

**key_cycle_429s（30min，重要健康信号）**: key0=40 req 循环 0 次, key1=69 req 循环 1 次, key2=1 req 循环 2 次。**0 个净 429 失败** —— 首 key 偶发 429 全部被轮转吸收到下一个 key 成功，rotation 机制完全工作正常。tier_attempts 空（无 key 循环进入失败态）。

## 趋势

- **6h**: 1695/1690 → **SR=99.70%**（5 失败为稀疏残留）
- **3h 逐小时**: 03:00 18/18 (100%), 02:00 225/224 (99.6%), 01:00 236/235 (99.6%), 00:00 284/284 (100%)
- **24h all_tiers_exhausted**: 32（持平 RN1061，最新事件为 ~13h 前，近 6h 窗口为 0 → 陈旧累积口径在滚动甩走）

## 容器状态

`dsvf0731_nv40666` Up 9 hours；`nv_gw` Up 32h；`hm4104` Up 3 days；`nv_gw_stable` Up 6d。`/health` ok，proxy_role=passthrough，nv_num_keys=5，dsv4f0731_nv 在 nvcf_pexec_models，port=40666。

## hm4104 fallback 日志（非本容器问题）

最近 5min fallback 日志为空，本窗口无 fallback 信号。备案同前。

## 修改记录

无（NOP）。维持当前参数（env 实测）：UPSTREAM_TIMEOUT=50, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30, NVU_TIER_BUDGET_DSV4F_NV=180, NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3, NVU_KEYMGR_429_{BASE,MAX}_COOLDOWN=120, NVU_KEYMGR_CONN_{BASE,MAX,LONG}_COOLDOWN=30/60/120, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3, NVU_BUFFER_TIMEOUT_STAIRS=90x5。

## 下一步建议

- **key_cycle_429s=1 占多数** 是 RN1060 以来的稳定背景信号：单 key 偶发 429、被轮转无净失败。当前 429 Base/Max=120s 冷却是健康工作点，无净失败即不需要调大 KEY_COOLDOWN（调大会延长首 key 偶发 429 的等待缺口）。
- **zombie_empty_completion** 延续为 24h 分布式噪声（跨全部 5 key、单速率 ~0.1/时）。跨 key 无聚集 → NVCF 端随机空响应，非本容器可控参数可改善；持续交叉核验但无需调参。
- 继续观察 24h all_tiers_exhausted（32 持平/走低即健康）。
- 链路稳定则持续 NOP。