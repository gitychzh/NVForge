# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: R885 (巡检轮/NOP — 近 30min 窗口 cc4101-primary SR=85.5% (59×200+10×502), 但 10×502
> 全 ≤22:44:47 UTC, 为 R883/R884 已记录的同一 NVCF/fid 级全键 429 突发的事件尾部;
> ⚠️ 独立复核比 R884 多抓到 2 个 cc2 错误 (22:43:17+22:44:47), 事件尾部比 R884 记录多延 ~3min,
> 仍属同一事件; **自末次错误 (22:44:47 UTC) 后 48×200 + 0 错误 = 100% SR, 10 分钟干净**, 系统自愈,
> 无新错误类, **不改码**, 2026-08-07 ~06:55 CST / DB UTC 22:55)
> 上轮: R884 (巡检轮/NOP — 相同 06:41 事件尾部, 以 22:41:37 为界, 不改码)

## 本轮 (R885) 改动 + 依据 + 验证

### 改动: 无 (窗口内 502 为 R883/R884 06:38 同源事件尾部, 事件后 100% 干净, 非代码缺陷, 不改码)

### 本轮数据 (~06:55 CST, 轮前链路分析注入 + 独立复核, DB UTC 22:55)

**近 30min cc4101-primary (cc2 路径) window SR = 85.5% (59×200 / 10×502) — 窗口伪象, 含同源事件尾部。**
**自末次错误 (22:44:47 UTC) 后: 48×200 + 0 错误 = 100% SR (10 个干净分钟).**

| 指标 | 值 | 状态 |
|---|---|---|
| **近 30min cc4101-primary SR (窗口)** | **85.5% (59/69)** — 10×502 全 ≤22:44:47, 为同源事件尾部伪象 | ⚠️ 窗口伪象 |
| **自末次错误 SR (真实当前态)** | **100% (48/48)** — 22:44:47 后 10 分钟干净 | ✅ 已自愈 |
| **primary 目标 tier** | **dsv4f0731_nv** (成功请求全 fid=281478d0, /health 确认) | ✅ |
| **cc2 错误时间轴** | 22:38:21 / 22:43:17 / 22:44:47 (all_tiers_exhausted dur 220~235s, buffer_exhausted 45~55s) | 单次事件尾部 |
| **⚠️ R884 边界修正** | R884 记"末次错误 22:41:37"; 独立复核实为 **22:44:47** (+3min) | ⚠️ 同一事件, 尾部更长 |
| **错误分类** | all_tiers_exhausted ×12 (220~235s), buffer_exhausted ×4 (45~55s) | 已知类, 无新错误 |
| **hermes (外部 cron) 错误** | 22:47:32 / 22:53:05 ×180s — 已知独立模式 (R875-R884), 与 cc2 路径无关 | ⚠️ 已知 |
| **nv_gw 近 5min 热度** | 无 NV-KEYMGR 429 / ALL-COOLING / BUFFER-EXHAUSTED marker | ✅ 已恢复 |
| **nv_gw 近 20min buffer** | 全 attempt-1 SUCCESS, elapsed 1~12s (dsv4f0731_nv) | ✅ 健康 |
| **per-key nv_tier_attempts** | dsv4f0731_nv 近 25min 各 key 残留 NVCFPexecRemoteDisconnected/529/timeout ×1 (事件恢复期) | ✅ 无新错误 |
| **三容器 health** | nv_gw / cc4101 / dsv4p 均 ok, primary=dsv4f0731_nv, 5 keys, nv_gw/cc4101 Up 3h | ✅ |

### 关键判断: 窗口内 502 是同源事件本体的尾部, 非新事件; 当前已 100% 干净, 不改码

- DB `now()`=22:55:03 UTC; **末次 cc4101-primary 错误=22:44:47 UTC (10 分钟前)**。
- **R884 边界修正**: R884 (22:49 提交) 以 22:41:37 为末次错误, 但本轮独立复核抓到其后两个
  22:43:17 / 22:44:47 错误 — 即事件尾部比 R884 记录多延 ~3min。**非独立复发, 仍为 06:38 单事件**。
- **~10min 来回放 cc2 (22:48~22:55) window: 48/48 = 100% SR**。成功全 fid=281478d0 未漂移。
- nv_gw 近 20min buffer 日志全 attempt-1 一次成交 (1~12s), 近 5min 无任何 exhaustion/429/cooldown
  marker — 系统已从 06:38 全键 429 中完全恢复。
- hermes 22:47/22:53 的 all_tiers_exhausted (180s) 为**已知外部 cron 模式** (caller=hermes),
  cc2 自身流量同时段 48/48 干净 → 上游已恢复, 属瞬态, 非 cc2 链路问题。
- 无新错误类, 无新事件峰。

关键点 (R883 已录铁证): **5 个 key 走不同 socks5h egress (7894/7897/7896/7899/7901) 同一秒收
429 → NVCF fid 级/上游级 rate limit, 非单 IP 问题**, 非 nv_gw 可 per-key 修复的外部限流。
系统设计内行为 (fail-fast → 180s cooldown → recovery) 正确自愈。本次新增观测: 06:38 事件尾部
持续约 6min (22:38~22:44:47), 比 R884 记录的略长, 但仍为单次自愈事件。不改码 —
对**已记录、已自愈、当前 100% 干净**的同源事件尾部做风险改动违反审慎原则。

## 修复链 (沿用, R827+R828+R829+R833+R813)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功, 用户无感知
3. 多 tier round-robin (dsv4p/dsv4f/glm5_2_nv) 自适应吸收底层跨 key 瞬态失败 (双 fid 现象)

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys, nvcf_pexec_models 含 kimi_nv/dsv4p_nv/dsv4f_nv/dsv4f0731_nv/glm5_2_nv)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066, passthrough, 5 keys)
- docker ps: nv_gw = Up 3h, cc4101 = Up 3h, dsv4p_nv40066 = Up 2d (nv_gw_stable = Up 5d 对照)

## 参数快照 (无变化, R885, 与注入配置一致)

```
nv_gw(40006): pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s, WAIT max 120s,
              TIER_COOLDOWN_S=180, TIER_TIMEOUT_BUDGET_S=180, KEY_COOLDOWN_S=30,
              NV_INTEGRATE_KEY_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90, MIN_OUTBOUND_INTERVAL_S=10,
              FORCE_STREAM_UPGRADE=0 (FORCE_STREAM_UPGRADE_TIMEOUT=150), NVU_DISABLE_MS_FALLBACK=0,
              NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
              NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
cc4101(4101): PRIMARY 动态轮转 (primary=dsv4f0731_nv), FALLBACK=ms_gw:40007 (glm5_2_ms, chat/completions),
              STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
              UPSTREAM_IDLE_TIMEOUT=150, PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30,
              FALLBACK_UPSTREAM_MODEL=glm5_2_ms, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步
- **观测窗口**: 确认 06:38 fid 级全键 429 事件是否**再出现独立新峰** (非本事件尾部)。判据:
  22:44:47 UTC 之后是否再现 `all_tiers_exhausted` 新错误。若 **新事件 >1 次/日** → 属
  dsv4f0731_nv (fid=281478d0) NVCF 级限流不稳定, 届时应评估 cc4101 primary 切换更稳 fid
  (cc4101 primary 决定逻辑不在 nv_gw scope, 只记录观察)。
- **不改码**。cc2 路径当前 (22:44:47 UTC 后) 已 100% 干净 (~10s)。待 cc2 路径 SR 掉 <99%
  且**非已知事件尾部** (即出现新错误峰) 或全键 429 恢复期 >30min 或出现新错误类 再动手。