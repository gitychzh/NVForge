# R850 — cc2 NOP 巡检轮 (近窗 100% 全净, primary=dsv4f0731_nv)

> 日期: 2026-08-07 04:14 CST | 决策: **不改码 (NOP 巡检)** | 连续 NOP: R844-R850 (~7 轮)

## 结论一句话
最近 10min cc4101-primary (cc2 自己路径) **SR=100% (34×200, 零错误)**; 30min 窗口的
`buffer_exhausted×6` 的 last 时间戳=19:53、`client_gone×2` last=19:55, 全为窗口早期
glm5_2_nv 风暴旧痕, 已被多 key round-robin + fail-fast 自适应吸收. 修复链充分, 不改码.

## 本轮数据 (04:14 CST 实时拉取, CLAUDE.md 注入 + DB 复核, UTC 对齐)

**最近 10min cc4101-primary: 34×200, 零错误 (SR=100%).**

**30min cc4101-primary (nv_requests):**
| status | count | error_type | last_seen |
|---|---|---|---|
| 200 | 83 | — | 当前 |
| 502 | 6 | buffer_exhausted | **19:53** (窗口早期旧痕) |
| 499 | 2 | client_gone_pre_attempt | **19:55** (窗口早期旧痕) |

→ 所有错误 last_seen 都在 ~04:00 之前, 当前时刻已全净. 与 R846-R849 恢复同型.

**30min nv_tier_attempts (底层 attempt 健康):**
- `pexec_success × 83` (全量成功 attempt, 含被吸收的瞬态)
- 瞬态: RemoteDisc×17 / 529×4 / empty_200×2 / NVCFPexecTimeout×1 / budget_exhausted×1
  → 跨多 key 分布 (k0:16 ok, k1:15 ok, k2:16 ok, k3:16 ok, k4:16 ok), 无单点失控, 被 round-robin 吸收

**30min nv_gw buffer 日志 (尾部):** 全走 **dsv4f0731_nv** e.g.
- req=dbc0138a: attempt1 k4 all_keys_exhausted → backoff 5s → **attempt2/5 success_tool_call flush 2620b (39s)**
- req=44063913: **attempt1 success** flush 1886b (5s)
- req=706d5a4d: **attempt1 success** flush 3599b (9s)
→ buffer 自适应重试充分, 无 buffer_exhausted 无 WAIT.

**第二 primary 目标:** cc4101 `/health` → `primary=dsv4f0731_nv` (自适应轮转持有).

## 分析与结论
- 双 primary 现象延续: dsv4f0731_nv 走 281478d0 (成功) / 52e1ddb6 (失败), round-robin 设计意图,
  单 key-fid 瞬态失败被其余 key 成功吸收, 请求最终 200. 无死锁.
- 底层 NVCF 仍有持久瞬态 (RemoteDisc/529), 但修复链 (R829/R833 fail-fast + buffer retry +
  动态 primary) 全量吸收, 最终 SR 100%. 系统健康.
- 无新增错误类, 无配置漂移, 不改码.

## 健康检查
- `curl 4101/health` → ok, primary=dsv4f0731_nv ✅
- `curl 40006/health` → ok, nv_gw 5 keys (kimi_nv/dsv4p_nv/dsv4f_nv/dsv4f0731_nv/glm5_2_nv) ✅
- docker ps: nv_gw Up 47min, cc4101 Up 21min, dsvf0731_nv40666 Up 11h, dsv4p_nv40066 Up 2d — 全 Up ✅

## 下一步
- 持续监控 NVCF 瞬态是否演化成持久风暴 (参考 R846 回潮模式).
- 若近窗 SR < 99% 或出现新错误类, 再小步改码; 否则维持 NOP.