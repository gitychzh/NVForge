# R1077: dsv4f0731_nv self-opt NOP — NVCF 模型特异性劣化风暴第 52 轮 (全 5 key, 无容器 lever)

> 时间: 2026-08-06 23:0x BJT (15:0x UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Flash 0731 via NVCF)
> 状态: **NOP (无参数修改)** — 延续 R1076/R1075/R1074/.../R1021 的模型特异性劣化风暴,
>   R1067 (CONN_ERR_FAST_BREAK=5) 已落地为最佳可及收益, 无新增单参数 lever。

## 1. 背景 (改前必有数据)

### 30min 窗口 (pre-run 注入) — tier_model=dsv4f0731_nv
- 总量 38, 200=8, 失败=30, **SR=21.1%** (pre-run 注入口径)
- Avg 180038ms, p50 206667ms, max 641610ms
- 429: 0 实际计数; key_cycle_429s 分布 k0:25, k1:6, k2:4, k3:2, k4:1, k7:1 — 轮转伪影 (k0 首试)
- per-key 200: k0=2, k1=2, k2=2, k3=1, k4=1 (成功分散于各 key)

### 错误分类 (30min, nv_tier_attempts)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 18 | 219273 |
| client_gone_during_flush | 4 | 384188 |
| zombie_empty_completion | 4 | 60122 |
| buffer_exhausted (ms_fallback) | 2 | 391251 |
| stream_absolute_cap | 2 | 163644 |

### 1h nv_tier_attempts 详查 (本轮直接查询)
- 总量 171, ok=0, fail=171 — 全 5 key 同时 0 成功。
- 上游错误: NVCFPexecRemoteDisconnected=59, 504_nv_gateway_timeout=41,
  529_nv_overloaded=33, NVCFPexecTimeout=27, empty_200=9, budget_exhausted_after_connect=2。
- per-key 错误 (跨 key 均匀分散, 非单 key 网络类劣化):
  - k0: RD=9, 504=8, empty=5, Tm=4, 529=4 (30)
  - k1: RD=13, 504=12, 529=11, Tm=4, empty=1 (41)
  - k2: 504=12, RD=8, 529=8, Tm=4, empty=2 (34)
  - k3: RD=11, Tm=9, 504=7, 529=5, budget=2, empty=1 (35)
  - k4: RD=18, Tm=6, 529=5, 504=2 (31)

### upstream_type (30min)
- nvcf_pexec 35 (200=8, **SR=22.9%**, avg=182776ms)
- nv_integrate 2 (200=0, avg=391251ms)
- ms_fallback 1 (200=0, avg=364079ms) — fallback 路径持续 0%
- (blank/其他 1, 200=0)

### 同链路对照 (本轮直接查询, 30min)
- glm5_2_nv (同容器同 key 同出口) **SR=86.7% (13/15)** vs dsv4f0731_nv 21.1%
  → 网络/mihomo/key/出口路径健康, 故障仅在 deepseek-v4-flash-0731 function 执行层。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1076 的 **NVCF 模型特异性劣化风暴**:
1. **错误跨全 5 key 均匀分散** (k0:30, k1:41, k2:34, k3:35, k4:31), 全 upstream 错误
   (RD+504+529+timeout+empty_200 混合风暴), 无单 key 劣化 → 无 key 冷却/轮转 lever 可解。
2. **同链路健康对照**: glm5_2_nv 同容器同 key 同出口 SR=86.7%, 证明链路/代理/出口健康,
   故障仅在 NVCF deepseek-v4-flash 0731 function 执行层 → 非本容器可路由之物。
3. **429 实际计数为 0**, fast-break=5 先耗尽 key, 无 429 冷却杠杆空间。
4. R1069 (budget 放宽) 已证明无收益并回滚 (R1070); R1067 (CONN_ERR_FAST_BREAK=5) 已落地
   为最佳可及收益。

## 3. 决策: NOP (无参数修改)

无单参数 lever 可修复全 5 key 模型特定上游风暴。维持 R1067 最佳配置,
等待 NVCF 侧 deepseek-v4-flash-0731 function 恢复。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough (pre-run 注入)
- [x] 容器 dsvf0731_nv40666 Up 5 hours, 无重启

## 5. 下一步建议

- 若风暴持续 >24h, 考虑与 HM1 协同 (R-chain) 将 dsv4f0731_nv 流量整体迁移至
  nv_integrate 通道或 ms_gw 备用模型, 而非继续调超时/冷却。
- 持续监控 glm5_2_nv 对照: 若对照也开始劣化, 则转为链路级 (mihomo/出口) 排查。