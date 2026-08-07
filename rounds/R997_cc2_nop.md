# R997 — cc2 NOP 巡检轮

- 轮次: **R997** | 2026-08-07 | cc2 (HM2, nv_gw 40006)
- 类型: **NOP (不改码)** — cc2 主链路连续第 **105** 轮 100% 干净 (R893-R997)
- 依据: live 复核 + 注入轮前链路分析 (2026-08-07 15:03)

## 本轮数据 (30min live re-pull)

| 指标 | 值 | 状态 |
|---|---|---|
| cc4101-primary (主 nv_gw:40006) | **119/119 = 100% SR, 0 bad** | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | ✅ |
| nv_requests 总 bad (非 200) | 2 条, 全属 hermes (dsv4f0731_nv 502: all_tiers_exhausted + stream_absolute_cap) | ✅(主链) |
| 30min fallback (cc_requests) | **0 次** (119 req 全未 fallback_triggered) | ✅ |
| buffer/wait 日志 | 全 attempt=1 一次成功, flush 1.1–13.4KB, elapsed 2–13s, 无 WAIT 停滞 | ✅ |
| 模型 SR | dsv4f0731_nv = 139/141 = 98.6% (含 hermes 2 bad) | — |
| 容器 | nv_gw Up 12h, cc4101 Up 11h, /health 40006+4101 全 200 | ✅ |

## 判定依据

- cc2 主链 (caller=cc4101-primary, nv_gw primary) **119/119 全 200 = 100% SR, 0 bad**。
- 2 条非 200 (all_tiers_exhausted + stream_absolute_cap) 经 caller JOIN 判定**全属 hermes** 越界宿主
  (已知坏 fid 52e1ddb6 泄漏), 与 cc2 主链 host 分离保持。
- cc_requests fallback = 0 次 (119 req 全未 fallback_triggered)。
- buffer 日志: NV-BUFFER-START/ATTEMPT/VERDICT/FLUSH/SUCCESS 全 attempt=1, 无 attempt>1, 无 WAIT 停滞。
- nv_tier_attempts 本轮窗口无 tier 错误行 (5 key 全成功, 已废弃 round-robin 吸收)。

## 改动

**无 (NOP)。** 主链 SR 100% + 专属错误 0 行 + fallback 0 次 + buffer 全一次成功,
无优化需求, 无参数可调。ms_gw fallback 保持不禁用 (NVU_DISABLE_MS_FALLBACK=0)。

## 验证

- 30min nv_requests caller 分组: cc4101-primary=119×200, hermes=21×200+2×502。
- 主链专属错误分组 = 空 (0 rows)。
- cc_requests: 119 req / 0 fb。
- buffer 日志: 全 attempt=1 success, flush 1081b–13445b, elapsed 1868ms–12898ms。
- health: 40006+4101 全 200; 容器 nv_gw/cc4101 皆 Up。

## 下一步

- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 持续确认 hermes 越界 bad (fid 52e1ddb6) 与主链 host 分离保持。