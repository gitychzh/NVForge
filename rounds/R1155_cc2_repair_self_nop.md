# R1155 — cc2 nv_gw 自优化 (HM2) — NOP 巡检轮

> 时间: 2026-08-08 02:48 CST (18:48 UTC)
> 上轮: R1154 | 容器: nv_gw Up 23h, cc4101 Up 23h, 全未重启 (health 全 ok)

## 结论
**NOP, 不改码。** 30min 窗口内 2× 502 buffer_exhausted = **R1154 已闭合的 Burst 2 (18:34/18:36 UTC) 的窗口边界 re-sample**, 非新一轮复发。18:37 起当前整窗干净, 实测最新 10min 35/35=100% SR, 含 130K+ char 超大请求全 200。

## 依据 (注入 + 实查 2026-08-08 02:48 CST)

- **注入 30min cc4101-primary**: `200|92`, `502|2` (buffer_exhausted, avg_dur ~34.8s) → 97.9% SR。
- **实查 90min 8× NV-BUFFER-EXHAUSTED 全部时序 (关键)**, 全部 ms_gw fallback 亦失败 → 全返 502:
  - **Burst A**: 17:47–18:02 UTC 6× (acdcf33a, 82ee78ae, ab59c732, c262f96c, abe467e0, 9731043f)
    = R1148/49 风暴带 (已闭环)。输入恒 63714 chars。
  - **Burst 2**: 18:34/18:36 UTC 2× (3a582e6c, 25c3a92b) = **R1154 已分析并确认自愈的那次**。
    输入 71105/80973 chars (超大请求, 同 R1154 观察目标)。
  - **18:37 → now 全 200, 无第 3 次复发。**
- **30min 窗口归属**: 本轮 30min 窗口 (18:16–18:46 UTC) 内仅 Burs2 2× (18:34/18:36) 在内,
  Burst A 在上一 30min, 不在本轮窗口。故本轮 2× = **同一次已闭合 burst 的 re-sample, 非新事件**。
- **Tier (实查 30min)**: 96 pexec_success, 仅 1× NVCFPexecTimeout; **429=0, empty=0, 无新类型**。
- **fallback (实查 30min)**: 0/99 = 0%, ms_gw 未实际成功 (8× 尝试全失败返 502, 不计入 NV 成功)。
- **Live (实查)**: 最新 10min cc4101-primary 35/35 = 100% SR; 最近 10 请求全 200
  (含 131908/129656/125839 chars 超大请求全通过)。
- **容器**: nv_gw/cc4101/dsv4p/kimi 全 health ok, 全未重启 → 无配置漂移。

## 本轮改动
无 (NOP)。判据: 错误类型全 accounted for (既有已闭合 storm 带 re-sample), 无新错误,
当前整窗干净, SR 100%, 不符改码条件 (铁律 1: 改前有数据, 无持续劣化不动手)。

## 验证
最新 10min 35/35=100%; 最近 10 请求全 200 含超大请求; tier 无 429/empty; 容器全健康。

## 下一步 (持续监控目标)
维持静稳, **重点盯是否重现"第 3 次独立瞬时 burst" 及复发间隔**。R1148/49 storm (17:47-18:02)
→ Burst2 (18:34/18:36, 间隔 ~32min) 已确认自愈。若下一窗口再现 ≥2× buffer_exhausted 且
为**独立新事件** (不在 18:37 前时区), 则按记忆 `ssleof-error-transient-egress-blip` 逻辑
深挖 mihomo dsv4f0731_nv egress 线路 (7900-7904), 并评估超 5 key 超大请求 (>70K chars)
buffer 首跳韧性。当前仍判定为瞬时 egress 抖动非配置漂移, NOP 自愈。

## 参数快照 (本轮注入, 无变更)
nv_gw: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, BUFFER_MAX_RETRIES=5 (stairs 90×5=450s),
NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
NVU_BUFFER_CALLERS=cc4101-primary,openclaw2. (full 参见上轮 R1154 STATE)
cc4101: PRIMARY=dsv4f0731_nv, FALLBACK=glm5_2_ms@ms_gw:40007, STREAM_TOTAL_DEADLINE_S=470,
PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3.
主链 fid: 281478d0-f307 稳定 (全 5 key pexec bind index 0)。