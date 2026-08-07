# R1205 cc2 nv_gw NOP 巡检轮 (瞬时多-key SSL egress blip 后自愈)

**日期**: 2026-08-08 07:00 CST
**结论**: NOP 不改码。30min 窗口含 ~5min 瞬时多-key SSL egress blip (06:43-06:47 CST),
触发 2× buffer_exhausted (SR 97.1%), 偶发 blip 已自愈, 恢复后窗口 (22:47→22:53 UTC) 100% SR。
无配置回归, 不改码。

## 数据 (30min 窗口, 活查复核)

### 活查 cc4101-primary (nv_requests, status)
| status | count |
|---|---|
| 200 | 66 |
| 502 | 2 |

SR = **97.1%** (66/68)。0 fallback (`fallback_occurred=0`)。

### 错误分类 (nv_requests status!=200, caller=cc4101-primary)
| error_type | count | avg_dur(ms) |
|---|---|---|
| buffer_exhausted | 2 | 68950 |

### 2× buffer_exhausted 请求明细
| req | error | nv_key_idx | dur(ms) | ts (UTC) |
|---|---|---|---|---|
| 76fb2449 | buffer_exhausted | — | 58039 | 22:44:20 |
| 7562e67f | buffer_exhausted | k4 | 79860 | 22:47:03 |

### nv_gw 日志时序 (根因铁证) — 瞬时多-key SSL egress blip
```
06:44:20 req=76fb2449 buffer + ms_fb 双败 → (第1个 buffer_exhausted)
06:44:30 k5 SSL error (9948ms) — egress 线开始抖
06:45:07 req=0789f624 all 5 keys + modes exhausted (execute_failed, 单次 blip 中)
06:45:43 req=7562e67f buffer attempt1 zombie_partial → attempt2-4 全 execute_failed
06:47:03 req=7562e67f AKE fail-fast (3 consecutive all_keys_exhausted) → 跳过 WaitQueue
         → ms_gw fallback 也失败 → 第2个 buffer_exhausted
06:47:13-38 k4→k5→k1→k2→k3→k4 连环 SSL error (5005-9949ms each, 全 5 key)
06:48:01 buffer 恢复 (ea32d78b)   ← blip 结束
06:49:49 req=d172056e 带 2 次 SSLEOFError (k3/k4) 靠 buffer 4-attempt 成功 flush 3902b
06:49:59 之后所有 buffer attempt=1 success, elapsed 5-23s ← 完全恢复
```

**根因**: ~5min (06:43-06:47 CST / 22:43-22:47 UTC) 全 5 key egress SSL 抖动脉冲
(`SSLEOFError: UNEXPECTED_EOF_WHILE_READING`, mihomo 5 US IP 同时瞬��异常), 撞上 2 个请求。
**无配置漂移** — 同 [[ssleof-error-transient-egress-blip]] 记忆的瞬时 egress 抖动模式
(R1077 确认主链 bad 根因=transient SSLEOFError 多 key egress 抖, NOP 自愈即可)。

### 防御链按设计工作 (未加码, 已生效)
1. buffer 5-attempt 跨 key 轮转 ✓
2. AKE (all_keys_exhausted) fail-fast 连续 3 次后跳过 WaitQueue (省 ~120s) ✓
3. ms_gw fallback 尝试 (同一 blip 下也败, 属防御目的非走 ms 成功链) ✓

### 恢复后窗口 (blip 结束后, 100% 全绿)
| 分钟 (UTC) | total | ok |
|---|---|---|
| 22:47-22:53 | 19 | **19** |

自 06:47 之后无 SSL cycle (最后一笔 06:47:38), 06:49:59 起全 attempt-1 命中。
30min 窗口尾部完全净稳。

### 容器健康
- nv_gw /health ok (nv_num_keys=5, 主链 fid 281478d0-f307, dsv4f0731_nv 单模式)
- cc4101 ok, dsv4p_nv40066 ok。

## 判断
2× buffer_exhausted 系 **~5min 瞬时全-key SSL egress blip** 撞上 2 个请求所致, 非配置回归。
防御链 (buffer 5-attempt + AKE fail-fast + ms 兜底) 全部按设计工作。blip 后窗口 100% SR,
无复发。**NOP 不改码** — transient egress 抖动期改码反而引入风险, 且当前静稳。

## 改动
无 (NOP 巡检轮)。仅记录瞬时 blip 事件, 提交 round 文件 + STATE.md。

## 下一步
维持静稳观察。持续监控 `ssleof-error-transient-egress-blip` 复发间隔:
- 本轮是近 50 轮内首次同窗同时出现 2× buffer_exhausted (均系 5min 全-key egress blip)。
- 若此类**全 5 key 同时 SSL 抖动**复发间隔明显缩短 / 单个 blip 内失败请求>2,
  才查 mihomo 5 US 线路质量 (egress_ip 分布); 孤立瞬时则 NOP 自愈即可。
- 主键: 仍优先最大化单位时间 NV 成功数, 当前链路整体 SR 高 (恢复后 100%)。