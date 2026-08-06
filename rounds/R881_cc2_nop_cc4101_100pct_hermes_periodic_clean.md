# R881 — NOP 巡检轮 (cc2)

> 近窗 cc4101-primary SR=100% (99×200) 零错误, 残留 all_tiers_exhausted×5 经 DB 独立核验
> 全为 caller=hermes 外部 cron (502×5, avg ~179.5s), fallback 0%, buffer 全 attempt1 一次成交,
> 不改码。2026-08-07 ~07:05 CST (DB UTC)。

## 本轮数据 (轮前链路分析注入 + DB 独立复核)

**最近 30min cc4101-primary (cc2 路径) SR = 100% (99×200, 零错误).**

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 30min cc4101-primary SR** | **100% (99×200)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有, /health 确认) | ✅ |
| **30min caller×status (独立 DB)** | cc4101-primary 99×200; hermes 1×200 + 5×502 | cc2 路径全净 |
| **error 归属** | all_tiers_exhausted×5 全为 caller=hermes (外部 cron, 非 cc4101), avg 179457ms ≈ buffer deadline 全额耗尽 | ✅ 与 cc2 无关 |
| **非 200 归属** | 仅 `hermes/502/all_tiers_exhausted×5` (DB 独立复核), cc4101-primary 0 错误 | ✅ |
| **fallback 触发率** | 0 (104 请求 0 fallback) | ✅ |
| **buffer/wait** | 无 buffer/wait 日志, cc4101-primary 全 attempt 一次成交, 无 multi-attempt 退化 | ✅ |
| **per-key nv_tier_attempts** | dsv4f0731_nv 5key pexec_success 18~21/key, NVCFPexecRemoteDisconnected 瞬态 + Timeout + 529_nv_overloaded + empty_200 跨 key 吸收 | ✅ |
| **三容器 health** | nv_gw / cc4101 / dsv4p 均 ok, primary=dsv4f0731_nv | ✅ |

## 关键判断: cc2 路径全净, hermes 周期 all_tiers_exhausted 非本链路问题

30min 窗口独立 DB caller 核验: cc4101-primary **99×200 零错误**; 非 200 (502×5) **全部
caller=hermes** (外部客户端, 非 cc4101): all_tiers_exhausted×5, avg 179457ms ≈ buffer
deadline 全额耗尽签名 — 属 hermes 外部 cron 周期性全键耗尽/超时, 沿用 R853-R880 判定, 而非本链路退化。

Per-key tier 尝试确认 5 key pexec_success 均衡 (18~21/key), 底层 NVCFPexecRemoteDisconnected/
Timeout + 529_nv_overloaded + empty_200 等瞬态被跨 key round-robin 吸收, KeyManager 无持续冷却键堆积。
cc2 自身 99×200 零错误, fallback 0%, 无 buffer/wait 退化, 链路/KeyManager 健康。不改码。

## 参数快照 (无变化, R881, 与注入配置一致)

```
nv_gw(40006): pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s, WAIT max 120s,
              TIER_COOLDOWN_S=180, TIER_TIMEOUT_BUDGET_S=180, KEY_COOLDOWN_S=30,
              NV_INTEGRATE_KEY_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90, MIN_OUTBOUND_INTERVAL_S=10,
              NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
              NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
cc4101(4101): PRIMARY 动态轮转 (primary=dsv4f0731_nv), FALLBACK=ms_gw:40007 (glm5_2_ms, chat/completions),
              STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
              UPSTREAM_IDLE_TIMEOUT=150, PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步
- 长期观测。glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。
- hermes 周期 all_tiers_exhausted 属外部客户端 cron (非 cc2 使命); 持续观察是否影响 NV 成功指标 (当前无影响)。
- 不改码。cc2 近窗全净 (dsv4f0731_nv primary 维持 100% 则持续 NOP; 待 cc2 路径 SR 掉 <99% 或 buffer 退化 (>1 attempt) 再动手)。