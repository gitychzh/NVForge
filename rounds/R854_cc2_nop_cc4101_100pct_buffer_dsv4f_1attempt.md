# R854 — cc2 NOP 巡检轮 (2026-08-07 04:28 CST)

近窗 cc4101-primary SR=100%, buffer 全走 dsv4f0731_nv attempt=1/5 一次成功 (4-11s),
零 buffer_exhausted 零 WAIT, 不改码。

## 结论: NOP 巡检轮

cc2 自身路径 (cc4101-primary) 近窗全净: 15min 实时 58×200 零错误,
buffer 全走 dsv4f0731_nv attempt=1/5 一次成功 (4-11s, success_tool_call),
零 buffer_exhausted 零 WAIT。修复链充分。不改码。

## 本轮数据 (04:28 CST, 实时拉取, DB UTC)

**最近 15min cc4101-primary SR = 100%** (58×200, 零错误)。

**buffer 日志 (实时 tail)**: 全部 attempt=1/5 → success_tool_call, elapsed 4-11s,
`flushed Xb after 1 attempt(s)` → 零 reroute, 零 buffer_exhausted。

**容器健康**:
- `nv_gw:40006/health` → ok (passthrough, 5 keys, nvcf_pexec_models 含 dsv4p_nv/dsv4f_nv/dsv4f0731_nv/glm5_2_nv/kimi_nv)
- `cc4101:4101/health` → ok (primary=dsv4f0731_nv)

## 关键判定: all_tiers_exhausted×5 归属 hermes 周期客户端 (沿用 R853)

30min 窗口 5 条 `all_tiers_exhausted` (502, avg 177.5s ≈ 90s×5 buffer 全额耗尽) 全部
**caller=hermes (外部客户端, 非 cc4101)**, 呈严格周期分发 (约每 5-6min 一次) —
cron/定时 hermes 客户端大请求特征, 与 cc2 路径无关。cc2 自身 100% 成功 + attempt=1/5
一次成交, 证明链路/KeyManager 未退化, 修复链正常吸收。

## 修复链 (沿用) — 无变更
- dsv4f0731_nv 1 attempt 一次成功 4-11s, 用户无感知
- 多 tier round-robin (dsv4p/dsv4f/glm5_2_nv) 自适应吸收底层跨 key 瞬态失败

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, TIER_COOLDOWN_S=180, NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 恢复)
cc4101: PRIMARY 动态轮转 (primary=dsv4f0731_nv), FALLBACK=ms_gw:40007,
        STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步
- 长期观测。glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。
- hermes 周期 all_tiers_exhausted 属外部客户端 cron, 非 cc2 使命; 持续关注是否影响 NV 成功指标。
- 不改码。