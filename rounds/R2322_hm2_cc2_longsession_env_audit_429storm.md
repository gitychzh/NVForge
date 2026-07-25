# R2322 (hm2_cc2): 长驻 session 首轮巡检 — env 疑点核实 + 429 storm 分析

> 首个 long-session(8h) 模式轮. 接棒 STATE.md(15:53 HM1 代刷, 停 R2192 cc2 自主).
> 本轮 **0 改动 0 restart**, 纯巡检+核实 STATE 待查疑点. 三阈值全不满足 → 冻结.

## 1. 接棒与启动

- git pull --ff-only origin main → HEAD=`d465b73 R2321` (HM2->HM1 桥接: BIG_INPUT_FAIL_N 4→3).
- cc2 自主最后轮仍 R2192 (944c013). R2317-R2321 全是 HM1 桥接轮 (作者 opc_uname 在 HM1, 标 "HM2->HM1").
- **关键发现**: `/opt/cc-infra` **不是 git 仓库** (无 .git), 且 hermes_improve_self 仓里**无 docker-compose.yml**.
  → HM2 的 `/opt/cc-infra/docker-compose.yml` 是独立活页, 非 git 跟踪, HM2 自己的真理源.
  → HM1 桥接轮 (R2317/R2319/R2321) commit message 里说的 env 改动 (BIG_INPUT_MODELS +dsv4p_nv, FAIL_N 4→3)
    **本就不打算落到 HM2** — 它们改的是 HM1 自己的 compose (HM1 的 /opt/cc-infra).
  → STATE 疑点 1/2 的"commit 写了但 env 没落地"是**误读**: 不是没落地, 是**对 HM2 无关**.

## 2. STATE 三疑点核实 (全部解决, 非 bug)

| 疑点 | STATE 15:53 实测 | 16:30 再实测 | compose 文件 | 结论 |
|---|---|---|---|---|
| 1. BIG_INPUT_MODELS 缺 dsv4p_nv | glm5_2_nv (单) | glm5_2_nv (单) | line 61 `=glm5_2_nv` | HM2 真理源本就单模型; R2317 是 HM1 改, 非 HM2 漏落地 |
| 2. BIG_INPUT_FAIL_N=1 vs R2313 的 4/R2321 的 3 | 1 | 1 | line 59 `=1` | HM2 真理源 = 1; R2313/R2321 是 HM1 改, 非 HM2 回退 |
| 3. 默认模型 (CLAUDE.md R2286 称 kimi_nv) | glm5_2_nv | glm5_2_nv (health) | line 209/248/285/328 `PRIMARY_*=glm5_2_nv` | R2291/R2293 已从 kimi_nv 回滚 → glm5_2_nv (glm5.2 恢复, kimi 差). R2286 注记 stale, 非 bug |

- compose line 209 注释原文: `R2291: kimi_nv->glm5_2_nv 应急回滚(30min 6fallback+5ATE+1zombie, glm5_2_nv 已恢复100%)... 改回减少 fallback 空洞+降499`
- compose line 285 注释: `R2293 (2026-07-23): kimi_nv->glm5_2_nv. glm5.2 已恢复... 回滚=改回 kimi_nv+restart`
- → glm5_2_nv 默认是**有意为之**, 非 bug. CLAUDE.md R2286 段"默认模型改为 kimi_nv"已被 R2291/R2293 覆盖 (memory 提醒: 文档写时为真, 已核实现值为 glm5_2_nv).

## 3. 30min 窗口数据 (16:00-16:30 CST = 08:00-08:30 UTC)

```
nv_requests: 44×200 / 5×502 → SR = 89.8% (面向 cc4101)
errors: 4× stream_absolute_cap + 1× zombie_empty_completion
fallback_occurred: 18/49 = 36.7% (nv_gw 内部 ms_gw 兜底)
```

502 明细 (全 fallback_occurred=t):
| ts(UTC) | model | error | dur_ms | out_tok | caller |
|---|---|---|---|---|---|
| 08:00 | glm5_2_nv | stream_absolute_cap | 292447 | 0 | cc4101-primary |
| 08:20 | glm5_2_nv | stream_absolute_cap | 150374 | 0 | unknown |
| 08:25 | glm5_2_nv | stream_absolute_cap | 197629 | 0 | unknown |
| 08:29 | glm5_2_nv | stream_absolute_cap | 163735 | 0 | unknown |
| 08:30 | glm5_2_nv | zombie_empty_completion | 130461 | 791 | unknown |

cc4101 真 fallback = 1 (req 2a521b4b, 60s timeout → ms_gw 救回 3739ms, SKIP-CIRCUIT 不计 circuit).

## 4. 内部 fallback 率 (核心负向指标, 深挖)

```
2h:  331 req / 315×200 / 16×err / fb=180 → fb_pct=54.4%   ← 偏高!
30min: 37 req / 33×200 / 4×err  / fb=19  → fb_pct=51.4%
```

**真 NVCF 直发成功** = 331 - 180(fb) - 16(err) = 135 → 真直发 SR ≈ 40.8% (2h). 这是 fb 率高的根因.

### 429 storm 根因 (NVCF 账户配额, 非旋钮治)

30min tier_attempts:
```
pexec_429=28  pexec_success=23  pexec_conn_RemoteDisconnected=6  pexec_SSLEOFError=2
```
429 按 key 分布 (全 5 key 都中): k0=3, k1=1, k2=3, k3=5, k4=7 (+ k0 还有 5 conn_RemoteDisconn + 1 SSL2).
→ all_keys_exhausted storm, NVCF 账户配额耗尽. 历史 R2320 已确认"~2h周期 all-5-keys-429, 非旋钮治".

nv_gw 日志 16:35-16:39 (storm 集中区) 验证 breaker 正确行为:
```
[NV-MS-FB-ATTEMPT] all_keys_exhausted glm5_2_nv breaker=CLOSED → ms_gw
[NV-MS-FB-OK] ms_gw success 2152-25562ms (breaker CLOSED 期要跑完 5 key 尝试才 fb, 慢)
[NV-MS-FB-BREAKER-OPEN] breaker OPEN state=('OPEN',5,17) → 直跳 nv chain, 直接 ms_gw (快 ~2-3s)
```
- breaker CLOSED 期: 跑完 5 key 429 才 fb, fb 耗时 ~25s (慢).
- breaker OPEN 期: 跳过 nv chain 直接 ms_gw, fb 耗时 ~2-3s (快).
- breaker COOLDOWN=900s 自动 HALF_OPEN→CLOSED, 设计自愈.

## 5. R2192 三任务状态

- 任务1 (cc4101 透传 cache_control): ✅ 落地, 持续生效 (cache_read 历史 38.8%).
- 任务2 (nv_gw zombie body dump probe): ✅ **probe 仍 ACTIVE**. 新增 1 sample 本窗口:
  `/app/logs/zombie_dumps/zombie_20260724T083219_182de7f6_passthrough_stream_zombie.json`
  (对应 08:32 UTC 的 zombie). 累计 sample 持续增长, hypothesis A 继续证伪.
- 任务3 (路径B zombie 内部 key 重试): ⏳ 未动. 本窗口仅 1 zombie (素材不足连续多轮≥5阈值). 
  spec+双路径骨架仍位 `~/cc_ps/cc2_repair_self/specs/`. 留待 zombie 累积达标再推进.

## 6. 三阈值判定 → 冻结

| 阈值 | 条件 | 实测 | 触发? |
|---|---|---|---|
| 1 | 30min SR < 85% | 89.8% | 否 |
| 2 | cc4101 fallback > 5 且新错误类型 | 1, 无新类型 | 否 |
| 3 | 新错误类型出现 | stream_absolute_cap/zombie 均 known | 否 |

全不满足 → **NOP, 0 改动 0 restart**.

> 备注: 真 NVCF 直发 SR ≈ 41% (2h) / fb 率 54% 偏高, 但根因是 NVCF 账户配额 429 storm (非旋钮治),
> 且 ms_gw 兜底使面向 cc4101 SR 维持 89.8%、cc2 自身无中断. 当前无 config-tunable 改动能降 fb 率
> 而不引入风险 (历史改大 KEY_COOLDOWN 反触发更多 primary timeout 恶化). 维持观测.

## 7. 长驻 session 机制验证 (首轮)

- `~/.claude/cc2.heartbeat`: touch @ 16:36 CST (启动时 age 9.3min 已 touch). watchdog 15min 阈值内.
- R-guard (R2192 内化): gateway/*.py 本轮未改, 无需触发. nv_gw StartedAt=2026-07-24T06:32:14Z RC=0 (稳定).
- auto-compact: 本轮未触发 (context 增长中, STATE 接棒机制就位).

## 8. 容器无漂移

```
nv_gw: StartedAt=2026-07-24T06:32:14Z RC=0 (Up 2h)
cc4101: StartedAt=2026-07-23T07:38:11Z RC=0 (Up 25h)
ms_gw: StartedAt=2026-07-21T12:50:09Z RC=0 (Up 2 days, 重启热备就位)
```
env 逐项核对比 STATE 15:53 快照无漂移 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, 
KEY_COOLDOWN_S=60, MIN_OUTBOUND=10, NVU_FORCE_STREAM_UPGRADE=0, NVU_EMPTY_200_FASTBREAK=3 等).

## 9. 下一轮

1. 继续巡检. 盯 429 storm 周期: 若连续多窗口 fb_pct 持续 >50% 且 storm 不自愈, 评估 breaker
   阈值 (NVU_MS_FALLBACK fail-N, 当前 5) 是否下调让 storm 期更快 OPEN 省 25s/key-尝试. (谨慎, 需数据证稳)
2. 盯 zombie 累积: 若连续多轮 ≥5 zombie, 推进 R2192 任务3 (先 cat specs/ 三份文件, grep -n 核实行号).
3. 盯 stream_absolute_cap: 若持续高频, 评估是否 NVCF 输出 cap (非旋钮治, 记录).
4. 长驻机制: 每 30min touch heartbeat, 每子任务刷 STATE, 改 .py 触发 R-guard.
5. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 40007, 只改 HM2, 写入仓库.

HM2 only. 本轮 0 改动 0 restart 0 碰 settings.
Co-Authored-By: Claude <noreply@anthropic.com>
