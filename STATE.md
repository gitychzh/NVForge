# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: R888 (巡检轮/NOP — 近 30min 窗口 cc4101-primary SR=98.3% (120×200+2×502), 2×502
> 全 ≤22:44 UTC (22:43/22:44), 为 R883 06:38 同一 NVCF/fid 级全键 429 事件尾部最后 2 个,
> R885→R887→R888 三轮独立实拉均确认同一 22:44:47 UTC 尾部边界, 稳定正确;
> 自 22:45 UTC 后 110×200 + 0 错误 = 100% SR (连续 ~26 分钟干净),
> nv_gw buffer 全 attempt-1 一次成交 (4~18s), fallback 0 次, hermes 6×502 为已知独立 cron,
> 系统自愈, 无新错误类, **不改码**,
> live DB now()=2026-08-07 07:11 CST (=23:11 UTC))
> 上轮: R887 (巡检轮/NOP — 同源事件尾部, 末次记 22:44:47 UTC, ID后 100% 干净)

## 本轮 (R888) 改动 + 依据 + 验证

### 改动: 无 (窗口内 2×502 为 R883 06:38 事件尾部最后 2 个, 末次错误 22:44 UTC, 此后 100% 干净, 非代码缺陷, 不改码)

### 本轮数据 (live DB now()=2026-08-07 07:11 CST, 实拉核实; UTC=23:11)

**近 30min cc4101-primary (cc2 路径) window SR = 98.3% (119×200 / 2×502) — 窗口伪象, 含同源事件尾部最后 2 个。**
**自末次错误 (22:45 UTC) 后: 110×200 + 0 错误 = 100% SR (连续 ~26 个干净分钟).**

| 指标 | 值 | 状态 |
|---|---|---|
| **近 30min cc4101-primary SR (窗口)** | **98.3% (119/121)** — 2×502 全 ≤22:44 UTC, 为同源事件尾部最后 2 个 (215s/195s) | ⚠️ 窗口伪象 |
| **自末次错误 SR (真实当前态)** | **100% (110/110)** — 22:45 UTC 后 ~26 分钟干净 | ✅ 已自愈 |
| **末次错误时刻** | **22:44 UTC — R885/R887/R888 三轮实拉均一致, 尾部边界稳定** | ✅ 确证同源 |
| **primary 目标 tier** | **dsv4f0731_nv** (成功请求全 fid=281478d0, /health 确认), 单次 8~13s | ✅ |
| **错误分类 (cc4101-primary)** | all_tiers_exhausted ×2 (215s/195s) — 21:43 & 22:44, 全 ≤22:44 UTC | 已知类, 无新错误 |
| **fallback 触发** | 0 次 | ✅ |
| **hermes (外部 cron) 错误** | 6×502, error_type=all_tiers_exhausted, avg 159s — 已知独立 caller 模式 (R875-R885), 与 cc2 路径无关 | ⚠️ 已知 |
| **nv_gw 近 30min buffer** | 全 attempt-1 SUCCESS, elapsed 4~18s, verdict=success_tool_call/text, 无 exhaustion marker | ✅ 健康 |
| **三容器 health** | nv_gw / cc4101 / dsv4p_nv40066 均 ok, primary=dsv4f0731_nv, 5 keys | ✅ |

### 本轮关键判断: 窗口内 2×502 是同源事件本体的最后 2 个尾部, 自 22:45 UTC 起 100% 干净, 不改码

- live DB `now()`=08-07 07:11 CST (=23:11 UTC); **末次 cc4101-primary 错误=22:44 UTC (08-06)**。
- **~26min 连续回放 cc4101-primary (created >22:45 UTC): 110/110 = 100% SR**, 成功全 fid=281478d0
  未漂移 (单次 8~13s)。
- R885→R887→R888 三轮独立实拉均确认同一 22:44:47 UTC 尾部边界 — 数据源稳定, 无新事件, 无偏移。
- nv_gw 近 30min buffer 日志全 attempt-1 一次成交 (4~18s, success_tool_call/text 直接 flush),
  近无任何 exhaustion/429/cooldown marker — 系统已从 06:38 全键 429 中完全恢复。
- hermes 的 all_tiers_exhausted 6×502 (avg 159s) 为**已知外部 cron 模式** (caller=hermes), cc2 自身
  流量同时段 110/110 干净 → 上游已恢复, 属瞬态, 非 cc2 链路问题。
- 无新错误类, 无新事件峰, 无 fallback 触发, primary fid 未漂移。

关键点 (R883 已录铁证): **5 个 key 走不同 socks5h egress (7894/7897/7896/7899/7901) 同一秒收
429 → NVCF fid 级/上游级 rate limit (fid=281478d0/dsv4f0731_nv), 非单 IP 问题**, 非 nv_gw
可 per-key 修复的外部限流。系统设计内行为 (fail-fast → 180s cooldown → recovery) 正确自愈。
不改码 — 对**已记录、已自愈、当前 100% 干净**的同源事件尾部做风险改动违反审慎原则。

## 修复链 (沿用, R827+R828+R829+R833+R813)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功, 用户无感知
3. 多 tier round-robin (dsv4p/dsv4f/glm5_2_nv) 自适应吸收底层跨 key 瞬态失败 (双 fid 现象)

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys, nvcf_pexec_models 含 kimi_nv/dsv4p_nv/dsv4f_nv/dsv4f0731_nv/glm5_2_nv)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066, passthrough, 5 keys)
- docker ps: nv_gw = Up, cc4101 = Up, dsv4p_nv40066 = Up (对照)

## 参数快照 (无变化, R888, 与注入配置一致)

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
- cc2 路径 SR 掉 <99% 且非已知事件尾部、或恢复期 >30min、或出现新错误类, 再动手
- (尾部事件持续自愈已 3 轮稳定; 30min 窗口会自动滑出 22:44 旧尾部, 下一轮应预期 window SR 恢复 100%)