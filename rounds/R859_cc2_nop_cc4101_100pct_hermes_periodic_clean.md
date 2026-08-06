# R859 — cc2 NOP 巡检轮 (cc4101-primary 100%)

- 日期: 2026-08-07 (坐标系 CST=UTC+8)
- 结论: **NOP 巡检轮 — 不改码**。cc2 自身路径全净 (124×200), 30min 残留 all_tiers_exhausted 全为 hermes 外部 cron 客户端特征 (沿用 R853-R858 判定)。

## 本轮数据 (实时 DB, UTC 20:46)

**最近 30min cc4101-primary (cc2 自己路径) SR = 100% (124×200, 零错误, avg 8797ms).**

**30min nv_requests 全局 (caller × status):**

| caller | status | count |
|---|---|---|
| cc4101-primary | 200 | 124 |
| hermes | 200 | 1 |
| hermes | 502 | 4 |

**30min 错误分类** — 仅 `all_tiers_exhausted × 4` (avg 180052ms), 全部 caller=hermes.

**hermes 周期分布** — 严格 ~6-7min 周期, 每次 ~180s = 5×90s buffer deadline 全额耗尽:
`20:19:00 / 20:26:19 / 20:33:01 / 20:39:01 UTC` (+20:25 一条 200)

**30min nv_tier_attempts per-key** — 5 key 均足量 pexec_success (24-28), 瞬态错误
(RemoteDisconnected/529_nv_overloaded/NVCFPexecTimeout/empty_200) 被 KeyManager 跨 key round-robin 自适应吸收.

**buffer/wait/keymanager 日志** — 无 (cc2 路径 buffer 全一次成交).

## 判断: NOP

- cc4101-primary SR=100% (124/124), 零错误, avg 8.8s 一次成交
- 瞬态 pexec 错误被 KeyManager + 多 tier round-robin 修复链平滑吸收, 未上抛到 cc2 用户请求
- hermes 周期 all_tiers_exhausted 属外部 cron 客户端 (严格 ~6-7min 周期, ~180s=5×90s buffer 全额耗尽的定时大请求特征), 非链路退化, 非 cc2 使命内 NV 成功指标
- nv_gw + cc4101 + dsv4p_nv40066 三 health ok
- **不改码** (修复链充分)

## 参数快照 (无变化)

```
nv_gw(40006): pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
              WAIT max 120s, TIER_COOLDOWN_S=180, TIER_TIMEOUT_BUDGET_S=180,
              NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 已恢复), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
cc4101(4101): PRIMARY 动态轮转 (primary=dsv4f0731_nv), FALLBACK=ms_gw:40007 (glm5_2_ms),
              STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
              PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步
- 长期观测。glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标).
- hermes 周期 all_tiers_exhausted 属外部客户端 cron, 非 cc2 使命, 持续观察是否影响 NV 成功指标 (当前无影响).
- 不改码。修复链充分, cc2 近窗全净.