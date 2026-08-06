# R886 — cc2 NOP 巡检轮: 同源事件尾部 (末次时刻与 R884 逐分钟一致), 当前 100% 干净, 不改码

- 日期: 2026-08-07 ~07:01 CST (live DB now()=07:01 CST = 22:58~23:01 UTC)
- 上轮: R885 (NOP, 同源事件尾部, 末次 22:44:47 UTC)
- 轮类: **NOP 巡检轮 — 不改码, 无 restart, 只记数据**

## 判定: NOP (不改码)

近 30min cc4101-primary window SR=91.1% (82×200+8×502), 但 8×502 **全 ≤14:41:37 CST (=22:41:37 UTC)**,
为该时刻前 R883/R884 已记录的同一 NVCF/fid 级全键 429 **单事件尾部**。末次错误时刻与 R884 记录
**逐分钟一致** (22:41:37 UTC), 铁证无新事件、无新峰、无偏移。自末次错误后 **83/83 = 100% SR (连续 18 分钟干净)**。

**KeyManager 429 / ProbeWorker / cooldown 行为均未触发新 exhaustion marker; 改码无依据。**

## 关键数据 (live 实拉核实, 非仅注入)

| caller | status | count |
|---|---|---|
| cc4101-primary | 200 | 83 |
| cc4101-primary | 502 | 8 (全 ≤14:41:37 CST = R883 事件尾部) |
| hermes | 200 | 2 |
| hermes | 502 | 10 (已知独立 cron 模式) |

- **~18min 回放 cc4101-primary: 83/83 = 100% SR**, primary=dsv4f0731_nv (fid=281478d0 未漂移)。
- 错误分类: all_tiers_exhausted ×6 (190~235s) + buffer_exhausted ×3 (45~55s) — 全 ≤14:41:37, 已知类。
- fallback 触发: 0 次。
- nv_gw 近 20min buffer: 全 attempt-1 SUCCESS (elapsed 6~14s, success_tool_call 直接 flush),
  无 ALL-COOLING / KEYMGR 429 / BUFFER-EXHAUSTED marker — 已完全恢复。
- 容器: nv_gw Up 4h, cc4101 Up 3h, dsv4p_nv40066 Up 2d; /health 全 ok。

## 根因 (沿用 R883 铁证, 非本轮新发现)

05-08 全键 429: **5 个 key 走不同 socks5h egress (7894/7897/7896/7899/7901) 同一秒收 429 → NVCF
fid 级/上游级 rate limit**, 非单 IP 问题, 非 nv_gw 可 per-key 修复的外部限流。系统设计内
fail-fast → 180s cooldown → recovery 正确自愈。不改码。

## 改动: 无

无源码/env 改动, 无 restart。铁律 1/改后验证不适用 (NOP)。

## 下一步

- 观测 22:41:37 UTC 后是否再现 `all_tiers_exhausted` **新独立峰**。>1 次/日 → 评估 cc4101 primary
  换更稳 fid (286478d0 稳定性观察, 该逻辑在 cc4101 scope 不在 nv_gw)。
- cc2 路径 SR 掉 <99% 且非已知事件尾部、或恢复期 >30min、或出现新错误类, 再动手。