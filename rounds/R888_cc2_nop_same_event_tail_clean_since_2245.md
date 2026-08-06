# R888 — cc2 NOP 巡检轮: 同源事件尾部 (末次 22:44 UTC 已验证 2 轮), 自 22:45 UTC 起 100% 干净, 不改码

- 日期: 2026-08-07 ~07:12 CST (live DB now()≈23:11 UTC = 07:11 CST)
- 上轮: R887 (NOP, 同源事件尾部, 末次记 22:44:47 UTC 为准确起点, ID后 100% 干净)
- 轮类: **NOP 巡检轮 — 不改码, 无 restart, 只记数据**

## 判定: NOP (不改码)

近 30min cc4101-primary window SR=98.3% (119×200+2×502), 2×502 **全 ≤22:44 UTC**
(= 22:43/22:44, 为 R883 06:38 全键 429 单事件尾部最后 2 个, 与 R885/R887 记录的末次
22:44:47 UTC 一致)。**自 22:45 UTC 起: 110/110 = 100% SR (连续 ~26 分钟干净)**, 无新峰、
无偏移、无新错误类。改码无依据。本轮窗口比 R887 多 1 个干净请求转折共 3 轮连续验证同一
22:44:47 尾部边界稳定正确。

## 关键数据 (live 实拉核实, 非仅注入)

| caller | status | count |
|---|---|---|
| cc4101-primary | 200 | 120 |
| cc4101-primary | 502 | 2 (全 ≤22:44 UTC = R883/R885/R887 事件尾部) |
| hermes | 200 | 2 |
| hermes | 502 | 6 (已确认 error_type=all_tiers_exhausted, avg 159s, 已知独立 cron 模式) |

- **~26min 回放 cc4101-primary (created >22:45 UTC): 110/110 = 100% SR**,
  primary=dsv4f0731_nv (fid=281478d0 未漂移, 成功全该 fid)。
- cc4101-primary 错误明细 (2×502, 全 ≤22:44):
  - all_tiers_exhausted (215s / 195s) — 22:43 & 22:44, 为末次事件尾部最后 2 个。
- fallback 触发: **0 次**。
- nv_gw 近 30min buffer: 全 attempt-1 SUCCESS (elapsed 4~18s, success_tool_call/success_text
  直接 flush), 无 ALL-COOLING / KEYMGR 429 / BUFFER-EXHAUSTED marker — 链路完全健康。
- 容器 /health: nv_gw (5 keys) / cc4101 (primary=dsv4f0731_nv) 全 ok。

## 关键判断: 2×502 = 同源单事件尾部 (非新事件), 当前 100% 干净, 不改码

- live DB now()=23:11 UTC; **末次 cc4101-primary 错误 = 22:44 UTC** (22:43/22:44 各 1)。
- R885→R887→R888 三轮独立实拉均确认同一 22:44:47 UTC 尾部边界, 稳定正确, 无新峰。
- 22:45 UTC 后 ~26min 连续回放 cc4101-primary: **110/110 = 100% SR**, buffer 全 attempt-1
  一次成交 (4~18s), 无任何 exhaustion/429/cooldown marker, fallback 0 次。
- hermes 的 all_tiers_exhausted (6×502 avg 159s) 为**独立外部 cron 模式**, caller=hermes,
  与 cc2 路径无关; cc2 自身流量同时段 110/110 干净 → 上游已恢复, 属已知瞬态。
- 无新错误类, 无新事件峰, 无 fallback 触发, primary fid 未漂移。

## 根因 (沿用 R883 铁证, 非本轮新发现)

06:38 (CST) 全键 429: **5 个 key 走不同 socks5h egress (7894/7897/7896/7899/7901) 同一秒收
429 → NVCF fid 级/上游级 rate limit (fid=281478d0 / dsv4f0731_nv)**, 非单 IP 问题, 非 nv_gw
可 per-key 修复的外部限流。系统设计内 fail-fast → 180s cooldown → recovery 正确自愈。不改码。

## 改动: 无

无源码/env 改动, 无 restart。铁律 1/改后验证不适用 (NOP)。

## 下一步

- 观测 22:44:47 UTC 后是否再现 `all_tiers_exhausted` **新独立峰** (与历史单事件尾部区分)。
  判据: >1 次/日新峰 → 评估 cc4101 primary 切换更稳 fid (该逻辑在 cc4101 scope 不在 nv_gw)。
- cc2 路径 SR 掉 <99% 且非已知事件尾部、或恢复期 >30min、或出现新错误类, 再动手。