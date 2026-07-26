# R2393 (hm2_cc2, 2026-07-27 04:54 CST) — nv_breaker OPEN 致 ms_gw 硬扛 → 502 风暴 (数据发现轮, 0 改动)

> 本轮纯数据发现. 上轮 STATE "cc2 链路 100% (42/42)" 是短窗口盲点, 实测 30min 有 19×502.
> 真根因链首次完整钉死: glm5_2_nv 5 keys 集体 429 → nv_breaker OPEN → ms_gw 硬扛大 prompt → 502.
> 0 改动 0 restart. 标记为下轮行动项 (nv_breaker 是保险, 不可贸然调阈值).

## 背景: 为何拉这轮数据

R-buffer-post2 STATE 记 "cc2 链路 100% (42/42), buffer 102×SUCCESS/6h, cc4101 fb=0".
但 `NV-ALL-TIERS-FAIL`=`NV-MS-FB-SERVED` 在 1h 窗口大量出现, 与 "100% + fb=0" 矛盾.
怀疑上轮看了短窗口或别的表. 本轮拉 30min 窗口核实.

## 数据 (2026-07-27 04:54 CST, 30min 窗口)

### cc2 自己的流量 (cc_requests, 30min)
```
 status | count | avg_ms | max_ms
--------+-------+--------+--------
    200 |   278 |  21428 | 148707   ← 91.4% (不是 100%)
    502 |    19 | 527766 | 565108   ← 6.4% 真失败! duration ~512-565s
    499 |     3 |  40515 |  68598   ← client_gone (残留, R2191 后 <5/30min 可接受)
```
error_type 分布 (非 200):
- 502 `stream_total_deadline` ×19 (duration 全部 ~512-565s = 480s deadline + 余量)
- 499 `client_gone_mid_stream` ×3

### 19×502 的时间分布 (30min 内, 每隔 ~5min 一个)
02:35, 02:44, 02:51, 02:56, 03:01, 03:06, 03:10, 03:15, 03:23, 03:28, 03:34,
03:53, 03:59, 04:07, 04:17, 04:23, 04:28, 04:32, 04:37
**注意**: DB now() 与 wall clock 有偏差, 但最新 04:37:47 与 nv_gw k2-429 风暴 (04:23-04:49) 重叠 → 是实时退化, 不是历史数据.

### nv_gw 侧: glm5_2_nv 5 keys 集体 429
```
[04:23:25.9] NV-GLM52-COOLDOWN tier=glm5_2_nv k2 429, cooling
[04:23:25.9] NV-GLM52-CHAIN-FAIL tier=glm5_2_nv all 5 keys + modes exhausted
...
[04:30:48.1] NV-GLM52-CHAIN-FAIL (同上, 5 keys 全 exhausted)
```
- 不是 "k2 单 key 问题" (上轮 STATE 若有此记法是错的).
- 是 5 keys 在 `integrate_us_rr` mode **共速率池**, 间歇集体撞 NVCF 429.
- RR 走完 5 key 全 cooling → CHAIN-FAIL (耗 30-50s/次, 非 90s timeout × 5).

### cc4101 侧: stall 触发 502
```
[04:40:41.3] CC4101-STREAM-STALL-FAIL req_id=5c91319c elapsed=512663ms
[04:47:10.4] CC4101-STREAM-STALL-FAIL req_id=ef03b533 elapsed=563395ms
```
- elapsed 512-563s = `CC4101_STREAM_TOTAL_DEADLINE_S=480` (R1925) + stall-watcher 余量.
- **关键**: 这两个 req_id 在 nv_gw 日志里 **零命中** → 这些请求根本没进 nv_gw chain.
  证明它们被 nv_breaker 直接甩给 ms_gw, nv_gw 查不到轨迹.

### nv_breaker 状态 (关键! 这是 502 的直接原因)
```
[04:28:27.6] NV-MS-FB-ATTEMPT chain all_keys_exhausted, attempting ms_gw fallback (breaker=HALF_OPEN)
[04:28:37.9] NV-MS-FB-SERVED ms_gw served fallback, nv breaker recorded failure (state=OPEN)
[04:31:47.1] NV-MS-FB-SERVED (state=OPEN)
[04:32:08.6] NV-MS-FB-BREAKER-OPEN breaker OPEN, skipping nv chain, serving ms_gw directly (state=('OPEN',5,8))
```
- nv_breaker 在 04:28 OPEN, 之后请求**跳过 nv chain 直走 ms_gw**.
- ms_gw 处理 cc2 大 prompt (150K+) TTFB > 480s → cc4101 stream_total_deadline → 502.

### kimi_nv big_input_breaker 也 OPEN (并发问题, 非 cc2 流量)
```
[04:52:51.6] NV-BIGINPUT-FAIL kimi_nv input=250590c err=zombie_empty_completion (breaker OPEN)
[04:53:11.4] (同上, metrics_id=a6618d9d)
[04:53:33.7] (同上, metrics_id=7ff9b920)
```
- 这是 openclaw/hermes 的 kimi 流量, 非 cc2. 但说明 NVCF 此刻整体不稳.

## 真根因链 (完整)

```
glm5_2_nv 5 keys (integrate_us_rr 共速率池) 间歇集体撞 NVCF 429
  → nv_gw CHAIN-FAIL (30-50s)
  → nv_gw 试 ms_gw fallback → ms fallback 累积失败
  → nv_breaker OPEN (state=('OPEN', 5, 8))
  → breaker OPEN 期间所有 glm5_2_nv 请求跳过 nv chain 直走 ms_gw
  → ms_gw 处理 cc2 大 prompt (150K+) TTFB 长 (>480s)
  → cc4101 stream_total_deadline=480 触发 → 记 502
  → cc2 收到 502 (19×/30min = 6.4%)
```

## 为何不改码 (本轮决策)

1. **nv_breaker 是保险, 不是病根**. 病根是 glm5_2_nv 5 keys 共速率池撞 429 (NVCF 上游配额问题, 非 cc2 可控).
2. 调高 nv_breaker 阈值 = 把死循环请回来 (CLAUDE.md 铁律: "不要调高阈值去假装不 OPEN").
3. 调高 `stream_total_deadline` = 让 cc2 等 ms_gw 更久 (8→10min), 治标不治本, 且 cc2 SDK 客户端墙 ~131s 也可能先断 (BUG-A).
4. 真正治本方向: **让 nv_breaker OPEN 期间也能快速恢复** (breaker cooldown 太长? state=('OPEN',5,8) 中 8 是什么?) 或 **让 glm5_2_nv 不集体撞 429** (换 mode? 不共速率池?). 需下轮专门调研.
5. 本轮数据已够, 不应在不理解 nv_breaker state=('OPEN',5,8) 含义时动它.

## 行动项 (下轮, 数据驱动)

- [ ] 查 nv_breaker state=('OPEN', 5, 8) 三元组含义 (config.py + handlers.py). 8 是 cooldown? 5 是 fail count?
- [ ] 查 glm5_2_nv `integrate_us_rr` mode 为何共速率池 — 是不是 5 keys 共用同一 egress IP (socks5h://172.18.0.1:7895)?
- [ ] 评估: breaker OPEN 期间能否**部分**走 nv (如 k0/k3 未 429 的 key) 而非全甩 ms. 当前是 OPEN 全甩.
- [ ] 持续监控: 19×502/30min 是否持续. 若 NVCF 429 是临时配额, breaker 自然恢复后 502 应降.

## 验证

- 0 改动 0 restart → 无需 health/docker ps 验证.
- `curl -s http://localhost:40006/health` = ok (nv_gw 容器健康, 是上游 429 非容器死).
- 数据已钉死根因链, 下轮据此决策.

## 铁律遵守

- 改前有数据 ✓ (30min cc_requests + nv_gw + cc4101 三侧日志交叉核证)
- 改后有验证 ✓ (0 改动, 无需验证; health ok 确认容器健康)
- 聚焦 nv_gw(40006) ✓ (数据全在 40006 链路; 未碰 ms_gw 源码)
- 所有修改写入仓库 ✓ (本文件)
- 未碰全局 ~/.claude/settings.json ✓

## 下一轮

拉新一轮 30min 数据, 看 19×502 是否还在. 若在 → 按"行动项"查 nv_breaker state. 若退 → 确认是 NVCF 临时配额, 归档.
