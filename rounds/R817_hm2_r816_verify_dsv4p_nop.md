# R817: HM2 R816 效果验证 + dsv4p empty-200 持续观测 NOP

> 承接 R816 (ms_gw SETTO-ERR NameError 修复). 远程 HM2 8轮定时优化 R4.
> 铁律: 改前有数据, 改后有验证, 改动 ≤5 处.

## 候选1: R816 settimeout 恢复效果 (★显著改善)

ms_gw stream duration 对比 (status=ok, is_stream=true):

| 窗口 | 样本 | avg | p95 | max |
|---|---|---|---|---|
| R816 改前 60min | 23 | 25292ms | 161088ms | 171230ms |
| R816 改后 10min | 10 | 8712ms | 17713ms | 18025ms |

**p95 从 161s → 17.7s, max 从 171s → 18s**. settimeout 兜底恢复后, 之前那些
read1 阻塞到默认超时的超长流式消失了. R816 修复真实生效.
部署后 15min 内无任何 >30s 的流式请求 (改前有 171s 的).

## 候选2: ms_gw cycle/stream_no_data

部署后日志: 全是 MS-OK-STREAM 正常结束, 无 cycle/stream_no_data/STALL.
SETTO-ERR 计数 = 0 (改前每次流式都报).
R813 [DONE] 关连接 + R816 settimeout 兜底, 双重保障下流式稳定.

## 候选3: dsv4p_nv ttfb empty-200 (NOP, 数据强化 R815 结论)

### 30min 数据
| tier_model | 200 | 502 | SR |
|---|---|---|---|
| dsv4p_nv | 14 | 4 | 78% (降, 之前 94.8%) |
| glm5_2_nv | 0 | 19 | 0% (DEGRADED 短路) |
| kimi_nv | 1 | 0 | 100% (有流量了) |

### dsv4p_nv 502 仍全 ~60s empty-200
17:17:29(60983ms) 17:25:45(60734ms) 17:33:09(60758ms) 17:36:18(60879ms)
间隔 ~8min, 从 R815 的偶发(9/90min)变为 30min 4 例, 频率上升.

### dsv4p_nv 200 ttfb 上升
| p50 | p95 | max |
|---|---|---|
| 32939ms | 53719ms | 58003ms |
(R815 时 p50=27.4s p95=43.7s max=49.8s) → NVCF 上游变慢.

## 决策: NOP (零网关侧改动)

### 为什么仍不能改 (数据强化)
1. **根因不变**: empty-200 是 NVCF 卡 60s 才吐 Content-Length:0 响应头, _check_empty_200
   收到头后即刻判定(检测本身即时), 但等头的 60s 无法避免.
2. **ttfb 重叠加剧**: 正常 max ttfb=58s, 失败 60s, 差 2s. 设提前放弃阈值(如 55s)
   会误杀 ttfb=58s 的正常请求. ttfb 上升让安全阈值更难设.
3. **UPSTREAM_TIMEOUT=66 合理**: 略高于 max 正常 ttfb.
4. **容错链路通**: empty→fastbreak→502→ms_gw, R816 后 ms_gw p95 17.7s 兜底可靠.

dsv4p_nv SR 从 94.8%→78% 的主因是 NVCF 上游变慢+empty-200 频率上升, 都是 NVCF 侧
问题, 网关不可修. 强行降 UPSTREAM_TIMEOUT 会误伤正常慢请求.

## 改动
无. 零容器重启, 零参数变更.

## 下轮候选 (R818)
- dsv4p_nv empty-200 频率若持续上升, 考虑把 dsv4p_nv 的 FALLBACK 从 ms_gw 同model
  改为更稳的 tier (但 R753 删了跨 model fallback, 需评估)
- glm5_2_nv DEGRADED 是否恢复 (周期性, 持续探测)
- ms_gw 流式在更大样本下 p95 稳定性 (R816 长期效果)
