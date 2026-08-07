# R1078: dsv4f0731_nv self-opt — NOP (NVCF RemoteDisconnected 模型风暴持续, 30min窗口健康)

日期: 2026-08-07 ~08:13 (UTC)

## 1. 数据 (30min 窗口 @08:02 采集 + 实时日志)

### 主指标
- **SR = 96.6% (141/146)**, avg=18205ms, p50=10089ms, p95=72226ms
- 30min 错误: all_tiers_exhausted=3, client_gone_during_flush=1, stream_absolute_cap=1
- **429 计数 = 0** (fast-break 先耗尽 key, 无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec (146), integrate 0 请求

### per-key 200 延迟 (全部健康)
| key | 200数 | avg | p50 |
|---|---|---|---|
| k0 | 26 | 10208 | 14769 |
| k1 | 31 | 15816 | 56703 |
| k2 | 28 | 12220 | 12775 |
| k3 | 27 | 10719 | 17143 |
| k4 | 29 | 12943 | 31363 |

5 key 全部正常出 200, 延迟接近 — 无单 key 劣化。

### NVCFPexecRemoteDisconnected (2h 主错误)
- **61 次, avg 40961ms** — 均匀跨全 5 key (k0:11, k1:13, k2:12, k3:15, k4:10)
- 6h 逐小时趋势: 10, 23, 29, 37, 19, 36, 16 — 持续高位
- 529_nv_overloaded = 15 (跨全 5 key)

### 实时容器日志 (08:00-08:13)
```
[NV-CONN] tier=dsv4f0731_nv k4 connection error: Remote end closed connection without response
[NV-TIER-FAIL] all 5 keys failed: 429=0, empty200=0, timeout=1, other=4, elapsed=180046ms
[NV-PEER-FB] returning local 502 for agent ms_gw fallback
```
all_tiers_exhausted 事件: 07:41, 07:53, 07:59, 08:05, 08:08 — **当前时刻正在持续风暴**。

### 对照
- glm5_2_nv (同容器同 key 同出口) 此前 R1077 对照 SR=86.7% → 链路/代理/出口健康
- 故障仅在 NVCF deepseek-v4-flash-0731 function 执行层

## 2. 根因判定 (改前必有数据)

延续 R1021-R1077 的 **NVCF 模型特异性劣化风暴**:
1. **错误跨全 5 key 均匀分散** (RD: 10-15/key), 无单 key 劣化 → 无 key 冷却/轮转 lever 可解。
2. **NVCFPexecRemoteDisconnected avg=41s** — 上游保持连接~36s 后主动断开, 非本容器超时可控
   (UPSTREAM_TIMEOUT=90 未触发)。5 key 每请求各烧 ~36s = 恰耗满 180s TIER_TIMEOUT_BUDGET。
3. **同链路健康对照**: glm5_2_nv SR=86.7% 证明链路健康, 故障仅在 NVCF function 执行层。
4. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
5. 30min 窗口 SR=96.6% 健康（大部分请求成功），但 6h 趋势 91.2% 且当前正风暴。

## 3. 决策: NOP (无参数修改)

无单参数 lever 可修复全 5 key 模型特定上游 RemoteDisconnected 风暴。
维持 R1067 最佳配置 (CONN fast-break + 冷却), 等待 NVCF 侧 deepseek-v4-flash-0731 function 恢复。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough
- [x] 容器 dsvf0731_nv40666 Up 15 hours, 无重启
- [x] hm4104 fallback 日志确认: 502 由 peer-fb 返回 (NVCF DEGRADING), ms_gw 503 亦失败

## 5. 下一步建议

- 若风暴持续 >24h, 与 HM1 协同 (R-chain) 将 dsv4f0731_nv 流量迁移至 nv_integrate 或 ms_gw 备用模型。
- 持续监控 glm5_2_nv 对照: 若对照也开始劣化, 则转链路级 (mihomo/出口) 排查。
- 关注 NVCFPexecRemoteDisconnected 6h 趋势: 若回落 <10/h 则说明上游恢复, 可停止 NOP 轮。