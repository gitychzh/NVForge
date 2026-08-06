# R853 — cc2 NOP 巡检轮 (2026-08-07 04:25 CST)

近窗 cc4101-primary SR=100% (逐分钟桶全 200, 全窗口零错误), 不改码。

## 结论: NOP 巡检轮

cc2 自身路径 (cc4101-primary) 全 30min 窗口 (19:55-20:25 UTC) 逐分钟桶 100% 200,
零错误。buffer 全走 dsv4f0731_nv attempt=1/5 一次成功 (7-13s, success_tool_call),
零 buffer_exhausted, 零 WAIT。修复链充分。不改码。

## 本轮数据 (04:25 CST, 实时拉取, DB UTC)

**cc4101-primary 逐分钟时间线**: 30 个分钟桶 (19:55-20:25 UTC) 每一桶全 200
(2-7 req/桶)。仅 1 条非 200 = 499 client_gone_pre_attempt @ 19:55:20 (窗口最早期, ~30min 前)。

**buffer 日志 (近 20min)**: 全部 attempt=1/5 → success_tool_call, 7-13s, 零 buffer_exhausted。

**容器健康**:
- `nv_gw:40006/health` → ok (passthrough, 5 keys, 含 dsv4f0731_nv)
- `cc4101:4101/health` → ok (primary=dsv4f0731_nv)

## 关键发现: all_tiers_exhausted×5 是 hermes 周期客户端, 非链路退化

30min 窗口的 5 条 `all_tiers_exhausted` (502, avg 177.5s) 全部 **caller=hermes (外部客户端, 非 cc4101)**,
且呈**严格周期分发型** (约每 5-6 分钟一次, 每次 ~177s ≈ 5×90s buffer deadline 全额耗尽):

```
caller=hermes 时间线:
  19:50:59 / 19:57:00 / 20:01:59 / 20:07:00 / 20:13:00 / 20:19:00
```

这是 **cron/定时 hermes 客户端**周期性发大请求、恰在 90s×5=450s buffer 耗尽时的特征,
与 cc2 路径无关。cc2 自身请求 100% 成功, 证明不是链路/KeyManager 问题 — 修复链
自适应吸收正常。

## 修复链 (沿用) — 无变更
- dsv4f0731_nv 1 attempt 一次成功 7-13s, 用户无感知
- all_tiers_exhausted 仅影响外部 hermes 周期请求, 与 cc2 无关

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, TIER_COOLDOWN_S=180, NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 恢复)
cc4101: PRIMARY 动态轮转 (primary=dsv4f0731_nv), FALLBACK=ms_gw:40007,
        STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步
- 长期观测。glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv。
- hermes 周期 all_tiers_exhausted 属外部客户端, 若非 cc2 使命范畴可不处理; 持续关注是否影响 NV 成功指标。
- 不改码。