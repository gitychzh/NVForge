# R858 — cc2 NOP 巡检轮 (cc4101-primary 100%)

- 日期: 2026-08-07 (坐标系 CST=UTC+8)
- 结论: **NOP 巡检轮 — 不改码**。cc2 自身路径全净, 30min 残留 all_tiers_exhausted 全为 hermes 外部 cron 客户端特征 (沿用 R853-R857 判定)。

## 本轮数据 (实时 DB, UTC)

**最近 30min cc4101-primary (cc2 自己路径) SR = 100% (118×200, 零错误).**

**30min nv_tier_attempts** — 118 次 pexec_success 成交, 另 30 次 pexec 瞬态错误:

| error_type | count |
|---|---|
| pexec_success | 118 |
| NVCFPexecRemoteDisconnected | 13 |
| 529_nv_overloaded | 10 |
| NVCFPexecTimeout | 5 |
| empty_200 | 2 |

这些瞬态错误被 KeyManager 自适应吸收 — **cc4101-primary 最终 100% 成功**, 证明底层多 key 瞬态失败被修复链 round-robin + fix-chain 平滑吸收, buffer 走 dsv4f0731_nv 一次成交。

**30min ccaller=hermes 错误 (502)** — 5 条 all_tiers_exhausted, 严格 ~6-7min 周期:

```
20:16:00 / 20:22:00 / 20:29:19 / 20:36:01 / 20:42:01 UTC
```

每次 ~180s = 5×90s buffer deadline 全额耗尽 — 典型 cron/定时大请求特征, 与 cc2 路径无关, 非使命内指标。

## 判断: NOP

- cc4101-primary SR=100% (118/118), 零错误
- 瞬态 pexec 错误 (RemoteDisconnected/529/timeout) 被 KeyManager 吸收, 未上抛到 cc2 用户请求
- hermes 周期 all_tiers_exhausted 属外部 cron 客户端, 严格周期分布, 非链路退化
- nv_gw + cc4101 双 health ok
- **不改码**

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, TIER_COOLDOWN_S=180, NVU_DISABLE_MS_FALLBACK=0
cc4101: PRIMARY 动态轮转 (当前 primary=dsv4f0731_nv), FALLBACK=ms_gw:40007,
        STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步
- 长期观测, 不改码。修复链充分, cc2 近窗全净。
- hermes cron 周期 all_tiers_exhausted 继续观察; 若其着增加链路负担, 评估是否独立于 mission 分流, 当前不处理。