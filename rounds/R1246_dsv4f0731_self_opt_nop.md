# R1246: dsvf0731_nv40666 self-opt NOP — SR 98.8% 健康回升, 过载burst退去, 新链路primary自证高SR, 无杠杆可动

> 时间: 2026-08-10 06:10 UTC (R1244 后 ~12h, 采集窗口 06:10 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR **98.8%** (85/86), 较 R1244 (78.2%) 回升 20.6pt;
> 1 错误全为 transient all_tiers_exhausted; 无净 429, 无 key 劣化, 无 fallback; upstream 100% pexec;
> R1245 已将本容器提升为 cc4101 **primary** 上游 — 新链路首窗自证高 SR (98.8%), 直接承载 CC 自身请求。

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, ~06:10 UTC)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 86 / 85 / 1 (SR=98.8%) |
| Avg / P50 / P95 | 24392 / 16190 / 130740 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 86 req, 85 SR=98.8% (100% pexec, integrate 0) |
| finish_reason | tool_calls 74, stop 11 (正常 agent 工具调用负载) |
| hm4104 fallback (5min) | **0 事件** (上游健康, 无触发) |

### 错误分类 (1错)
| error_type | n | avg_ms | 判定 |
|---|---|---|---|
| all_tiers_exhausted | 1 | 180043 | 孤立 transient tier 烧满, 非系统性问题 |

### per-key 200 延迟 (count/avg/p95)
- k0: 19 / 19168 / 56696 | k1: 19 / 26850 / 51715 | k2: 19 / 25955 / 91635 | k3: 17 / 20993 / 48007 | k4: 11 / 17572 / 45327
- **5 key 负载均衡** (19/19/19/17/11), avg 17.5-26.9s 均匀, **无任何 key 劣化**。k2 p95 略高 (91.6s) 但 avg 正常, 无净错误, 属长流方差。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=53, k1=29, k2=3, k3=1 | 计数偏高但 **net 429=0**, key manager 已全部吸收 → 冷却机制工作正常, 无需调 KEY_COOLDOWN/NVU_KEYMGR_*。

### 6h/3h/24h 趋势
- **6h: 311 req, 280 SR=90.0%**
- 3h 逐小时 (回落确认): 22h=16/16 **SR100%** | 21h=106/101 SR95% | 20h=41/37 SR90% | 19h=31/28 SR90%
- **当前小时 100% SR = NVCF 过载 burst 完全退去** (R1244 活跃过载 11h SR70% 已过)
- 24h all_tiers_exhausted = 292 (含昨日过载累积, 当前窗口仅 1 → 历史遗留计数, 非活跃)

## 判定逻辑 (为什么 NOP)
1. **SR 98.8% (85/86)** 远高于 NOP 阈值 95%, 较 R1244 (78.2%) 大幅回升 20.6pt — 证实 R1244 判断的 NVCF 过载为瞬态, 非本容器参数问题。
2. **1 个 all_tiers_exhausted 孤立** (孤立 transient, avg 180s 恰为 budget 上限 = 单次 NVCF 过载时隙), 无流截断/空响应/净 429, 无系统性问题可调。
3. **5 key 负载均衡 + 无劣化**: 各 key avg 17.5-26.9s 均匀, p95 除 k2 正常长流方差外全部 <57s, 无 key 代理故障。
4. **key_cycle_429s 高但 net 429=0**: key manager 冷却完全吸收, 属正常保护机制, 不应调冷却参数 (调大反而加剧 TIER-SKIP, 见 R12/R13 教训)。
5. **fallback=0**: hm4104 无切换事件, 上游链路健康, 无 fallback 触发可降本。
6. **R1245 新 primary 链路自证**: 本容器现为 cc4101 primary (承载 CC 自身), 首窗 98.8% SR 直接验证新拓扑高可用, 无参数杠杆需要。

## 验证
- [x] `docker exec dsvf0731_nv40666 env` 参数未变 (UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN=30, TIER_COOLDOWN=90, NVU_KEYMGR_* 稳定)
- [x] /health = ok (dsvf0731_nv40666 Up 19 minutes, R1245 链路切换后新实例)
- [x] 容器当前 uptime 19min 为 R1245 验证时 stop/start 所致 (链路切换端到端测试需临时停容器), 非异常重启

## 下一步建议
- **本容器保持 NOP**: NVCF 过载瞬态已过, SR 回升至 98.8%, 当前为健康稳态。
- 持续观察 24h ATE 从 292 随历史窗口滚动回落 (当前窗口仅 1); 若回落至 <100 且 30min SR 稳定 >95%, 确认过载为一次性事件。
- R1245 新链路 (cc4101→40666 primary): 留意下一窗 **fallback 触发率** 是否 <5% (当前 0), 若 40666 失稳致频繁切慢 glm5.2@40006, 再评估 40666 自身杠杆。
- 若 24h ATE 重新 >150 且 30min SR 持续 <85%, 上报基础设施层治理 NVCF 过载 (本容器不擅自改 budget/冷却伪装修复)。