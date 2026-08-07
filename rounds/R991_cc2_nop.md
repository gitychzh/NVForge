# R991 — cc2 NOP 巡检轮 (不改码)

> 日期: 2026-08-07
> 结果: **NOP** — cc2 主链路连续第 **99** 轮 (R893-R991) 100% 干净
> 判定: cc4101-primary = **125/125 = 100% SR, 0 bad**; 唯一 bad 全属 hermes 越界; fallback 0

## 结论一句话

cc2 主链 (nv_gw:40006 → dsv4f0731_nv) 在 30min 窗口 125/125 全 200, 主链专属错误 **0 rows**, fallback 0 次;
唯一 5 个 bad (all_tiers_exhausted ×4 + zombie_empty_completion ×1) 100% 属 caller=hermes + 已知坏 fid 52e1ddb6
(宿主越界容器), 与主链 host 分离。**不改码, NOP 巡检。**

## 本轮数据 (live 复核 2026-08-07 14:4x + 注入轮前链路分析)

| 指标 | 值 | 状态 |
|---|---|---|
| cc4101-primary (主 nv_gw:40006) | **125/125 = 100% SR, 0 bad** (live re-pull) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| 唯一 bad (非 200) | 5 条, 全 caller=hermes 线 (fid 52e1ddb6: 4 all_tiers + 1 zombie) | ⚠️ 越界 |
| bad caller 归属 | 100% hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests 30min) | 0 次 (125 req 全未 fb) | ✅ |
| tier 瞬态错误 (nv_tier_attempts) | NVCFPexecRemoteDisconnected(16)/Timeout(3)/empty_200(3), 全被吸收 | ✅ |
| 容器 | nv_gw Up, cc4101 Up, health 全 200 | ✅ |

### nv_tier_attempts 30min (live 复核)
pexec_success 主导 (125), 瞬态逐 key: k0 RemoteDisconnected(2)/Timeout(1)/empty_200(1),
k1 RD(3)/Time(1)/empty(1), k2 RD(4), k3 RD(3)/Time(1)/empty(1), k4 RD(4) —
全被多 key round-robin + func_health + buffer 吸收, 无泄漏为 200 以外。

### buffer 日志 (nv_gw live)
cc2 primary 请求 attempt=1 一次成功, `verdict=success_text` (elapsed 11s, 1301b) 与
`success_tool_call` (elapsed 9-16s, 7291b-11106b) 交替, flushed 给 CC, **无 502 泄漏**。

## 依据 (注入轮前链路分析 + live 复核)

- 30min nv_requests cc4101-primary = **125/125 全 200** (live re-pull)。
- bad 分组 (by caller×err_type): `hermes | all_tiers_exhausted | 52e1ddb6 | 4` +
  `hermes | zombie_empty_completion | 52e1ddb6 | 1` — 全 hermes 线 + 已知坏 fid, R897 起持续 host 隔离。
- cc_requests 30min: total 125, fb=0, 全未 fallback_triggered。
- health: 40006/4101 全 200; nv_gw / cc4101 皆 Up。

## 关键判断

1. 主链 SR 100% + 专属错误 0 rows → 无 cc2 优化需求。
2. 唯一 5 bad 全属 hermes 线 (fid 52e1ddb6), host 分离, non cc2 范围。
3. 多 key round-robin (dsv4f0731_nv 为首) + func_health + buffer 已达稳态, 瞬态全被吸收, 无参数可调。
4. fallback 0 次, ms_gw fallback 保持不禁用 (NVU_DISABLE_MS_FALLBACK=0)。

## 下一步
- NOP 观察继续。主链 dsv4f0731_nv 健康, 无参数改动需求。
- 持续监控 hermes bad (fid 52e1ddb6) host 隔离是否保持 (R897 起持续隔离)。