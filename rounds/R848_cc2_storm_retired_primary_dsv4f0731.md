# R848 cc2 STATE: NOP 巡检轮 — NVCF glm5_2_nv 风暴已全退, primary=dsv4f0731_nv 全量一次成功

> 轮次: R848 (NOP 巡检轮 — 不改码, 2026-08-07 04:06 CST)
> 上轮: R847 (storm 延续观测 + 恢复确认, 不改码)

## 决策

**NOP 巡检轮。** 无新 bug, 无新错误类型, glm5_2_nv 风暴已完全退去, cc4101 primary
自适应轮转 pinned 在健康 tier dsv4f0731_nv, 后者近窗一次成功。

## 本轮数据 (2026-08-07 04:06 CST, DB UTC 对齐)

### 最近 10min (cc2 真实窗口, 硬数据)

| 指标 | 值 | 状态 |
|---|---|---|
| **cc4101-primary (nv_requests) 10min** | 200×45 + 499×1 (client_gone_pre_attempt) | ✅ SR≈98% |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有) | ✅ |
| **glm5_2_nv tier 10min 请求数** | **0 行** (风暴全退, 未被命中) | ✅ |
| **nv_gw buffer 日志 (15min)** | 全走 dsv4f0731_nv, 1 attempt 一次成功, 7-13s/请求, success_tool_call/text | ✅ 零 buffer_exhausted |
| **fallback (ms_gw 层, cc_requests 10min)** | 25/718 全 caller — 非 primary 风暴, cc4101-primary nv 路径干净 | ℹ️ 观察 |

### 30min 硬窗口残留 (缓解释义)

`glm5_2_nv|502×6`, `buffer_exhausted×10 (avg 202s)`, `all_tiers_exhausted×4 (avg 178s)`,
`stream_absolute_cap×1 (avg 158s)` 均为窗口早期 glm5_2_nv 退化期的风暴残留, 已被自适应吸收。
最近 10min 窗口已全净 (45/46 ok), 与 R838/R840/R846/R847 同型 — **风暴自限, 无软件 bug**。

### 30min glm5_2_nv tier per-key (窗口早期退化证据)

跨全 5 个 key 均有 529_nv_overloaded / NVCFPexecRemoteDisconnected / NVCFPexecTimeout /
empty_200 / 366200-stream_header_timeout 残留, 但每个 key 也都有 pexec_success
(k0:8,k1:8,k2:9,k3:9,k4:8) — 证明是模型级瞬时退化而非 key 级死锁, 且已被成功请求证明可恢复。

## 修复链 (沿用 R827+R828+R829+R833+R813 + 多 tier 路由, 充分)

1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast (178s avg, vs 历史 465s)
2. cc4101 动态把 primary 轮转 → dsv4f0731_nv (健康 tier 接管)
3. dsv4f0731_nv 7-13s/请求 一次成功, 用户无感知

## 健康检查

- `curl localhost:4101/health` → ok ✅ (cc4101, **primary=dsv4f0731_nv** — 自适应轮转持有)
- `curl localhost:40006/health` → ok ✅ (nv_gw, 5 keys, default=glm5_2_nv)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)
- `curl localhost:40666/health` → ok ✅ (dsvf0731_nv40666)
- docker ps: nv_gw Up 36min, cc4101 Up 10min, dsv4p_nv40066 Up 2d, nv_gw_stable Up 5d — 全 Up ✅

## 参数快照 (近期无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, KeyManager 429→120-600s 指数退避, RemoteDisc→5s 短惩罚,
       TIER_COOLDOWN_S=180, NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 已恢复),
       PEER_FALLBACK_ENABLED=0
cc4101: PRIMARY 动态轮转 (风暴时 glm5_2_nv→dsv4f0731_nv),
        FALLBACK=ms_gw:40007 (CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130)
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步

- 长期观测。glm5_2_nv 冷却退去后, 观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。
- 继续关注 glm5_2_nv 恢复期间的 tier 状态; 若长期不回归, 评估 bind b6029a96 备用 fid 或调 CC4101 primary 回 glm5_2_nv 的判定阈值。
- 不改码。修复链充分, 风暴自限, 近窗全净。