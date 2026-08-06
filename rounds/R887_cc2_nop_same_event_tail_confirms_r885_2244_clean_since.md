# R887 — cc2 NOP 巡检轮: 同源事件尾部 (确认 R885 的 22:44:47 更准确的末次时刻), ID后 100% 干净, 不改码

- 日期: 2026-08-07 ~07:07 CST (live DB now()=23:06 UTC = 07:06 CST)
- 上轮: R886 (NOP, 同源事件尾部, 末次记 22:41:37 UTC)
- 轮类: **NOP 巡检轮 — 不改码, 无 restart, 只记数据**

## 判定: NOP (不改码)

近 30min cc4101-primary window SR=95.4% (103×200+5×502), 但 5×502 **全 ≤22:44:47 UTC**,
为该时刻前 R883/R885 已记录的同一 NVCF/fid 级全键 429 **单事件尾部**。**本轮实拉确认末次错误
= 22:44:47 UTC, 与 R885 记录的尾部延伸逐分钟一致 (而非 R886 记的 22:41:37) — 铁证 R885 更准确。**
自 22:44:48 UTC 后 **95/95 = 100% SR (连续 ~23 分钟干净)**, 无新峰、无偏移。改码无依据。

## 关键数据 (live 实拉核实, 非仅注入)

| caller | status | count |
|---|---|---|
| cc4101-primary | 200 | 103 |
| cc4101-primary | 502 | 5 (全 ≤22:44:47 UTC = R883/R885 事件尾部) |
| hermes | 200 | 2 |
| hermes | 502 | 8 (已知独立 cron 模式, 22:37~23:05) |

- **~23min 回放 cc4101-primary (created >22:44:48 UTC): 95/95 = 100% SR**, primary=dsv4f0731_nv
  (fid=281478d0 未漂移, 成功全该 fid, 单次 8~13s)。
- cc4101-primary 错误明细 (全 ≤22:44:47):
  - 3× all_tiers_exhausted (fid=281478d0, 80~235s) — 22:38*~22:44*
  - 2× buffer_exhausted (45~55s) — 22:37
- fallback 触发: **0 次** (`fallback_triggered` 全 false, 111 请求)。
- nv_gw 近 25min buffer: 全 attempt-1 SUCCESS (elapsed 9~10s, success_tool_call 直接 flush),
  无 ALL-COOLING / KEYMGR 429 / BUFFER-EXHAUSTED marker — 已完全恢复。
- 容器 /health: nv_gw / cc4101 / dsv4p_nv40066 全 ok, 5 keys, primary=dsv4f0731_nv。

## 本轮关键修正: R886 记 22:41:37, 实拉确认尾部实际到 22:44:47 (R885 正确)

R886 的 STATE 记末次 cc4101-primary 错误 = 22:41:37 UTC。本轮 live 实拉近 30min 全部 502:
**末次 = 22:44:47 UTC** (与 R885 的独立复核一致)。即 **R885 的 22:44:47 是完整/准确的尾部边界**,
R886 的 22:41:37 是其注入窗口与 live 窗口时钟差所致偏早。二者均为同一 06:38 全键 429 单事件,
无矛盾, 无新事件。本轮以 **22:44:48 UTC 为"干净起点"** 统计得到 95/95 100% SR。

## 根因 (沿用 R883 铁证, 非本轮新发现)

06:38 (CST) 全键 429: **5 个 key 走不同 socks5h egress (7894/7897/7896/7899/7901) 同一秒收 429
→ NVCF fid 级/上游级 rate limit (fid=281478d0 / dsv4f0731_nv)**, 非单 IP 问题, 非 nv_gw 可
per-key 修复的外部限流。系统设计内 fail-fast → 180s cooldown → recovery 正确自愈。不改码。

## 改动: 无

无源码/env 改动, 无 restart。铁律 1/改后验证不适用 (NOP)。

## 下一步

- 观测 22:44:47 UTC 后是否再现 `all_tiers_exhausted` **新独立峰** (与历史单事件尾部区分)。
  判据: >1 次/日新峰 → 评估 cc4101 primary 切换更稳 fid (该逻辑在 cc4101 scope 不在 nv_gw)。
- cc2 路径 SR 掉 <99% 且非已知事件尾部、或恢复期 >30min、或出现新错误类, 再动手。