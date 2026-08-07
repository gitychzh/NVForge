# R1013 — cc2 NOP inspection round

**日期**: 2026-08-07 16:07 CST
**上轮**: R1012 (NOP, 主链 122/122=100%)
**决策**: **NOP 巡检轮 — 不改码** (主链 SR 100%, 无新错误)

## 本轮数据 (30min window, live 复核)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **121/121 = 100% SR, 0 bad** (live re-pull) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| nv_requests 总 bad (非 200) | 4 条 all_tiers_exhausted, 全属 hermes (fid 52e1ddb6, status=502) | ✅(主链) |
| 30min cc_requests | 122 request, fallback 0 次, SR=100% | ✅ |
| 30min nv_tier_attempts | k0-k4 各 22-26 pexec_success + RemoteDisconnected(17)/Timeout(3)/empty_200(1), 全被 buffer 吸收 | ✅ |
| 容器 | nv_gw Up 13h, cc4101 Up 12h, dsv4p_nv40066 Up 2d, /health 全 200 | ✅ |

## 关键观察

- 主链 (cc4101-primary) 自 **R893 起连续 121 轮 100% 干净**, 主链专属错误 0 行, 无持久 root-cause 可查。
- 4 条 bad (dsv4f0731_nv 502, all_tiers_exhausted) 经 DB live 归属: **caller=hermes, fid=52e1ddb6**
  (越界宿主泄漏) — 与主链 host 分离保持。
- buffer 全 attempt=1 一次成功 (flush 3.4-5.8KB, 7-13s), verdict 全 success_tool_call,
  无 BUFFER-/WAIT- 停滞, 无 KeyManager/ProbeWorker 降级日志。
- 主链首代模型 = **dsv4f0731_nv**。

## 决策依据

不改码:
1. 主链 SR 121/121 = 100% + 专属错误 0 行, 无优化需求。
2. 本轮 bad 全属 hermes 越界宿主 (fid 52e1ddb6), 主链无根因可查。
3. multi-key round-robin + func_health + buffer (attempt=1 全成功) 已达稳态, 无参数可调。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代。
- 延续确认 hermes 越界坏 fid (52e1ddb6) 与主链隔离是否持续 (host 分离保持)。