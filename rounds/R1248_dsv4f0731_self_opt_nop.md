# R1248: dsvf0731_nv40666 self-opt NOP — SR 98.7% 健康稳态延续, 1 孤立 ATE transient, 无杠杆可动

> 时间: 2026-08-10 06:30 UTC (R1247 后 ~1 窗, 采集窗口 06:22 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR **98.7%** (75/76), 与 R1247 (97.5%) 基本持平;
> 1 错误全为 isolated all_tiers_exhausted; 无净 429, 无 key 劣化, 无 fallback; upstream 100% pexec;
> 参数自 R1246 未变, /health ok。

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, ~06:22 UTC)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 76 / 75 / 1 (SR=98.7%) |
| Avg / P50 / P95 | 28625 / 17491 / 100702 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 75 req, 75 SR=100% (100% pexec, integrate 0) |
| finish_reason | tool_calls 65, stop 10 (正常 agent 工具调用负载) |
| hm4104 fallback (5min) | **0 事件** (上游健康, 无触发) |

### 错误分类 (1错)
| error_type | n | avg_ms | 判定 |
|---|---|---|---|
| all_tiers_exhausted | 1 | 180066 | 孤立 transient tier 烧满 (avg 恰为 budget 上限 180s = 单次 NVCF 过载时隙), 非系统性问题 |

### per-key 200 延迟 (count/avg/p95)
- k0: 16 / 18177 / 44288 | k1: 17 / 32457 / 90429 | k2: 15 / 28726 / 98392 | k3: 15 / 20503 / 50549 | k4: 12 / 34532 / 113886
- **5 key 负载均衡** (16/17/15/15/12), avg 18-34s 均匀, **无任何 key 劣化**。k2/k4 p95 略高 (98s/113s) 但 avg 正常, 无净错误, 属长流方差。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=66, k1=3, k2=6, k3=1 | 计数偏高但 **net 429=0**, key manager 已全部吸收 (k0 计数高因负载最重 16 req) → 冷却机制工作正常, 无需调 KEY_COOLDOWN/NVU_KEYMGR_*。

### 6h/3h/24h 趋势
- **6h: 339 req, 307 SR=90.6%**
- 3h 逐小时 (回落确认): 22h=46/45 **SR97.8%** | 21h=106/101 SR95.3% | 20h=41/37 SR90.2% | 19h=28/26 SR92.9%
- **当前小时 97.8-98.7% SR = NVCF 过载 burst 完全退去**, 逐小时历史窗口微降 (19-20h 90-93%) 属昨日过载长尾, 非活跃。
- 24h all_tiers_exhausted = 293 (含昨日过载累积, 当前窗口仅 1 → 历史遗留计数, 非活跃)

## 判定逻辑 (为什么 NOP)
1. **SR 98.7% (75/76)** 高于 NOP 阈值 95%, 与 R1247 (97.5%) 基本持平 (+1.2pt 噪声内) — 健康稳态延续。
2. **1 个 all_tiers_exhausted 孤立** (isolated transient, avg 180s 恰为 budget 上限 = 单次 NVCF 过载时隙), 无流截断/空响应/净 429, 无系统性问题可调。
3. **5 key 负载均衡 + 无劣化**: 各 key avg 18-34s 均匀, 无 key 代理故障。
4. **key_cycle_429s 高但 net 429=0**: key manager 冷却完全吸收, 属正常保护机制, 不应调冷却参数 (调大反而加剧 TIER-SKIP, 见 R12/R13 教训)。
5. **fallback=0**: hm4104 无切换事件, 上游链路健康, 无 fallback 触发可降本。
6. **R1245 primary 链路持续自证**: 本容器为 cc4101 primary (承载 CC 自身), 连续三窗 98.8%/97.5%/98.7% SR, 新拓扑稳定。

## 验证
- [x] `docker exec dsvf0731_nv40666 env` 参数未变 (UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN=30, TIER_COOLDOWN=90, NVU_KEYMGR_* 稳定)
- [x] /health = ok (dsvf0731_nv40666 Up 31 minutes, 5 keys)

## 下一步建议
- **本容器保持 NOP**: NVCF 过载瞬态已完全退去, 连续三窗 SR >97%, 健康稳态确立。
- 持续观察 24h ATE 从 293 随历史窗口滚动回落 (当前窗口仅 1); 若回落至 <100 且 30min SR 稳定 >95%, 确认过载为一次性事件。
- R1245 新链路 (cc4101→40666 primary): 留意下一窗 **fallback 触发率** 是否 <5% (当前 0), 若 40666 失稳致频繁切慢 glm5.2@40006, 再评估 40666 自身杠杆。
- 若 24h ATE 重新 >150 且 30min SR 持续 <85%, 上报基础设施层治理 NVCF 过载 (本容器不擅自改 budget/冷却伪装修复)。