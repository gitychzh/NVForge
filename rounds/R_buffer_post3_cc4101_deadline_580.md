# R-buffer-post3: cc4101 STREAM_TOTAL_DEADLINE 480→580 对齐 buffer 总预算

> HM2 cc2 自线巡检轮. 本轮**发现并修复一个真实失败**: cc4101 的 480s 总时长墙
> 在 R-buffer 后成了比 nv_gw buffer(580s) 更早的硬墙, 误杀 cc2 正常长请求.
> **不是 NOP 巡检轮** — 有实质改动 + 验证.

## 数据 (改前, 2026-07-27 06:06 CST 拉取, 6h 窗口)

### cc2 链路 (cc_requests, glm5_2_nv) 6h 状态分布
- 200 成功: 378
- 502 stream_total_deadline: **29** ← 真实失败, 本轮目标
- 499 client_gone_mid_stream: 3 (历史低位)

### 30min 窗口 (近实时) cc2 链路
- 38×200 / 0 失败 (SR 100%) — 但这只是短窗口, 6h 累积 29 deadline 是真问题
- buffer: 全 SUCCESS 0 RETRY (短窗口正常)
- cc4101 真 fallback = 0

### 29 个 stream_total_deadline 的铁证模式
```
duration_s | ttfb_s | content_s | count
   512-522 | 32-42  |   480     |  全部 29
```
- **content_s 全部精确 = 480s** = ttfb 后恰好 480s 被 cc4101 杀.
- **成功 200 请求里 duration>400s 的 = 0 个** → 凡跑到 480s 的全被杀, 没一个撑过去成功.
  = 误杀铁证: 这些是 NVCF 正常长输出 (大 input 132-190K + 长 thinking + 长文), 被 cc4101 480s 墙截断.
- 最新一条 05:55:26 CST (拉数据时 11min 前), 持续活跃中, 非历史.

## 根因分析

### R1925 设 480s 的历史背景 (compose 注释原文)
- 480s = nv_gw 指数退避 420s (单 key 60/120/240) + 30s 余量 + ttfb 容差.
- 设值时 (R1925, 2026-07-22) nv_gw 还没有 buffer, 单请求 chain budget ~120s,
  480s "对当前链路几乎无副作用" (注释原话).
- 目的是为 R1926 nv_gw 指数退避扫清 cc4101 抢断坑.

### R-buffer 后情况变了 (R-buffer, 2026-07-27 落地)
- buffer TOTAL_DEADLINE_S=580s: cc2 请求走 buffer 可重试到 580s.
- 但 cc4101 STREAM_TOTAL_DEADLINE_S=480s **比 buffer 早 100s 杀请求**.
- → buffer 的 580s 预算被 cc4101 480s 架空: 请求总时长一到 480s (ttfb+内容流),
  cc4101 先于 buffer 完成杀连接 → 记 stream_total_deadline 502.
- cc4101 日志铁证 (req=8dc75549): `[DBG] passthrough recv-fallback got 22b` 紧接
  `[STREAM-DEADLINE] 480s after ttfb exceeded` → 杀的瞬间 NVCF 还在发内容 (22b 刚到).

### cc2 SDK 墙确认 (安全边界)
- `API_TIMEOUT_MS=600000` (600s) = cc2 claude CLI 总请求超时墙.
- 当前 cc4101 480s < SDK 600s. 提到 580s 仍 < 600s, 留 20s 给 buffer flush.
- resume.sh / cc2-long systemd 超时 28800s (8h), 不撞.

## 拟改 (一轮一点, env 单点)

**cc4101 `CC4101_STREAM_TOTAL_DEADLINE_S`: 480 → 580**

- compose env 单点改 (docker-compose.yml:211).
- 580s = 对齐 buffer TOTAL_DEADLINE_S=580s, 让 buffer 能完整跑完不被 cc4101 抢断.
- 留 SDK 600s 墙 20s 余量 (buffer flush + SSE 收尾).
- 不改 40007 ms_gw (铁律).
- 只改 HM2 (铁律).
- 回滚: 改回 480 (或删 env 行回 config 默认 360).

## 预期

- 29/6h 的 stream_total_deadline 应骤降 (这些请求能撑到 buffer 完成而非被 480s 砍).
- cc2 链路 6h SR 从 378/(378+29+3)=92.0% 提升.
- buffer 的重试预算 (580s) 真正可用, 不再被 cc4101 架空.
- 风险: 若 NVCF 真有"无限零星 chunk 永不结束"的挂死流, 480→580 多等 100s 才切.
  但 (a) buffer 的 TOTAL_DEADLINE 580s 本就打算等这么久, (b) idle_gap 100s 仍兜底真静默,
  (c) cc2 SDK 600s 墙是最终硬上限. 风险可控.

## 验证清单

1. compose 改 + `docker compose up -d cc4101` (env 改用 up -d, 非 restart — env 变更需重建容器).
   ⚠ 注意: cc4101 是 cc2 入口, 重启期间 cc2 请求会瞬断几秒, 但 nv_gw(ms_gw 兜底) 不变.
2. `docker exec cc4101 env | grep STREAM_TOTAL` 确认 580.
3. `curl -s http://localhost:40006/health` + `docker ps` (nv_gw 不受影响, 但确认栈稳).
4. 等下一窗口 (30-60min) 查 cc_requests stream_total_deadline 是否归零/骤降.
5. 确认 buffer 仍全 SUCCESS, cc4101 fallback=0, 无新错误类型.
6. commit + push, 更新 STATE.

## 验证结果 (落地后即时)

### 即时验证 (06:15 CST 重启后 2min)
- `docker exec cc4101 env | grep STREAM_TOTAL` → `CC4101_STREAM_TOTAL_DEADLINE_S=580` ✓
- `curl /health nv_gw` → ok, nv_default_model=glm5_2_nv ✓ (未受影响)
- docker ps: cc4101 Up 6s, nv_gw Up 5h, ms_gw Up 5d ✓
- cc4101 启动日志正常 (listening 4101, primary glm5_2_nv, fallback ms_gw)
- 真实 cc2 请求通过: req=d6ca3510 经 cc4101→nv_gw buffer, 200 SUCCESS 8.8s ✓
- 重启后 2min: cc2 链路 6×200 / 0 deadline / 0 499 / 0 fail ✓ (早期迹象)
- cc4101 重启后 5min 内 STREAM-DEADLINE/STALL-FAIL/PRIMARY-FAIL 计数 = 0 ✓

### 待下轮窗口验证 (30-60min 后)
- stream_total_deadline 应从 29/6h 骤降 (近零或归零).
- 改前铁证 content_s 全=480s 精确 → 改后这些长请求能撑到 NVCF 自然完成 (duration 应 >480s 但 <580s 且 status=200).
- buffer 仍全 SUCCESS, cc4101 fallback=0, 无新错误类型.
- 风险观察: 若出现 duration>580s 的 deadline (说明 NVCF 真有 >580s 的超长流), 再评估是否提到 595s (逼近 SDK 600s 墙, 但需留 flush 余量).

## 铁律自查
- 改前有数据 ✓ (6h 29 deadline 铁证)
- 聚焦 40006 链路 ✓ (cc4101 是 cc2→nv_gw 链路入口, 非独立 ms_gw)
- 不碰 40007 ms_gw 源码/配置 ✓ (只改 cc4101 env)
- 只改 HM2 ✓
- 写入仓库 ✓
- 改后验证 ✓ (清单见上)
