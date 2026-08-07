# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1206 (NOP 巡检 — SSLEOFError 瞬时 egress blip 跨全 key 复发泛化:
> 30/40min 窗 3× buffer_exhausted (SR 96.6%), 其中 2 个是 R1205 blip 重复计入
> (76fb2449/7562e67f, 22:43-22:47 UTC), 仅 1 个新失败 (7f34c956, 23:04-23:06 UTC) 系跨 k1-k3
> 连续 3 次 Remote end closed 触发; 防御链工作, 基线健康 (19-21 UTC 连续 3h 100% SR) → NOP 不改码)**
> 主链 fid: **281478d0-f307** 稳定, dsv4f0731_nv 单模式
> 错误分类 (活查, 40min): cc2-primary buffer_exhausted ×3 (avg ~100s; 2 上轮残留 + 1 新)
> 根因: `SSLEOFError` / `Remote end closed connection without response` 瞬时 egress resets
> 跨全 5 key 均匀分布 (非单隧道), mihomo 进程/端口稳定, 防御链按设计工作 → 上游瞬时, 非配置回归
> 最新窗口: 19-21 UTC 连续 3h 100% SR; 22h 98.8%, 23h 96.0% (含 1 新失败 7f34c956)
> fallback: **~0%** (仅有 ms_gw 兜底尝试, 同瞬时下也败, 非成功走 ms)

## 本轮 (R1206) 改动 + 依据 + 验证

### 改动: 无 (NOP 巡检轮。3× buffer_exhausted 中 2 个为上轮 blip 重复计入, 1 个新失败系
上游瞬时 egress 跨 key 抖动的低概率连续 3 次命中, 无改码条件)

### 依据 (活查 40min + nv_gw 日志时序, 2026-08-08 08:00 CST)

- **活查 40min cc4101-primary (nv_requests)**: `200|86`, `502|3` (buffer_exhausted),
  SR=96.6% (86/89), 200 avg_dur=18407ms。fallback 触发率 ~0%。
- **3× buffer_exhausted 归属**: `76fb2449`(ts 22:43-22:44, dur 58039)、`7562e67f`(22:46-47, 79860)
  = **R1205 blip 重复计入**; `7f34c956`(23:04-23:06 UTC, dur 167010) = **本轮新失败**。
- **新失败 7f34c956 时序**: attempt1 k1(07:04:37) → attempt2 k2(07:05:43) → attempt3 k3(07:06:49),
  各隔 ~60s 全 `Remote end closed connection without response` → 3-consecutive all_keys_exhausted
  → AKE fail-fast (跳过 WaitQueue 省 ~120s) → ms_gw 兜底也败 → 502。167s = 3× ~60s attempt timeout。
  防御链按设计工作, 只是运气差连续 3 发同一瞬时坏。
- **同信号多数自愈**: 180b7acd(07:10 k1 err → attempt2 → 200)、69b33a57/63930dd2/d172056e 等
  均 attempt-2/3 自愈; 仅 7f34c956 连败 3 次。
- **跨 key 均匀分布 (3h nv_gw 日志)**: k1(2+4) k2(3+2) k3(5+2) k4(7+1) k5(3+1),
  SSLEOFError + Remote end closed 全 5 key 均有 → 广义 egress 瞬时, 非单隧道故障。
- **基线健康铁证**: 19-21 UTC 三小时 SR 100.0% (665/665), 22h 98.8%, 23h 96.0%。
  mihomo pid 1056 自 Jul30 稳定, 5 proxy 端口 (7894/7896/7897/7899/7901) 全绑定; 容器 nv_gw 32h、
  cc4101 27h 无重���漂移, 参数与上轮一致 → 非配置回归。
- **容器健康**: nv_gw /health `{"status":"ok", nv_num_keys=5}` (+ 主链 dsv4f0731_nv, fid
  281478d0-f307) ok, dsv4p_nv40066 ok。

### 验证
新失败 7f34c956 系连续 3 次同一瞬时 egress 重置的低概率事件 (防御链 buffer/AKE fail-fast/ms 兜底
全按设计工作); 同信号其他请求均自愈; 且存在 19-21 UTC 连续 3h 100% SR 基线 → 上游瞬时抖动,
无改码条件。fallback 0% (ms 兜底尝试未成功走 ms)。容器 health ok。

## 参数快照 (nv_gw + cc4101, 本轮注入无变更)

- **nv_gw**: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5
  (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90,
  TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0
  (全 key bind fid index 0=281478d0-f307, dsv4f0731_nv 单模式)。
- **cc4101**: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1205 (NOP — 30min 含 ~5min 瞬时全-key SSL egress blip (06:43-06:47 CST), 2× buffer_exhausted
SR 97.1%, blip 自愈后窗口 100%) → R1206 (共享仓库): 本轮 3× buffer_exhausted 中 2 个为上一轮
blip 重复计入, 仅 1 个新失败 (7f34c956)。SSLEOFError 瞬时 egress 抖动从 R1205 的「集中 ~5min 全
key blip」演变为 R1206 的「跨 k1-k5 分散 ~10min」, 属同一瞬时模式复发/泛化, 非配置回归。

## 下一步
维持静稳观察。**核心监控升级** (按 `ssleof-error-transient-egress-blip` 记忆的「持续分布才查
mihomo 线路」触发门槛): SSLEOFError / `Remote end closed` 在 R1205 + R1206 已连续两轮出现且
跨全 key 均匀分布。若 **R1207 仍见此类分散错误 + SR <99%**, 已满足「持续分布」条件 → 拉 mihomo
隧道线路质量 (各 egress_ip 失败率、隧道状态、`mihomo get proxies`), 评估是否调整 key→proxy 绑定。
- 单个意外 buffer_exhausted / 瞬时自愈错误仍 NOP 自愈。
- 主键: 最大化单位时间 NV 成功数; 当前存在 3h 100% SR 基线, 防御链工作正常。