# R958 (cc2) — NOP 巡检轮 (不改码)

> 轮次: R958  |  时间: 2026-08-07 ~12:10 CST  |  类型: NOP / inspection
> 判断: **cc2 主链路连续第 66 轮 (R893-R958) 100%干净 + 主链专属错误 0 行 → 不改码**

## 改动
无 (NOP)。cc4101-primary 主链路 30min = 122/122 全 200 (0 bad), 专属错误 0 行,
fallback 0 次, 无新 cc2 主链错误类。

## 依据 (live DB 30min 实拉 ≈2026-08-07 12:10 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **122/122 全 200, 0 bad (100% SR)** (live 实拉)。
- 总 nv_requests 30min = **148 req, 146 ok (98.6% SR), cc2_bad=0**。
- 3 个 bad (非 200) = **均 `caller=hermes`**: `502 all_tiers_exhausted ×2` (avg 177s) +
  `502 zombie_empty_completion ×1` (avg 39.6s), caller 列双重归属 hermes, non cc2 主链。
- fallback (cc_requests 30min) = **0 次** (122 req, fb=0; 全 status=200, SR=100%)。
- nv_tier_attempts 30min (dsv4p): 每 key NVCFPexecRemoteDisconnected 2-6 + pexec_success 22-28
  (k0:2/25, k1:3/24, k2:3/28, k3:6/24, k4:5/24)。瞬态错误被多 key round-robin + buffer 重试吸收,
  全部 resolve 为 200。
- buffer 日志 (nv_gw): cc4101-primary 全 attempt=1 成功 (elapsed 2-13s, verdict
  success_tool_call/success_text, input 68-70k), 无 WAIT-/KEYMGR- 错误噪声 (KEYMGR 429/cooldown = 0)。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **122/122 = 100% SR, 0 bad** (实拉) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| 唯一 bad (非 200) | 502 all_tiers_exhausted ×2 + 502 zombie_empty_completion ×1 (均 caller=hermes) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (122 req 全 200) | ✅ |
| tier 瞬态错误 | NVCFPexecRemoteDisconnected 每 key 2-6, 全被吸收 | ✅ |
| 全局 nv_requests SR | 146/148 = 98.6% | ✅ |

## 验证
- 30min nv_requests cc4101-primary live re-pull = 122/122 (0 bad)。
- bad 分组 (caller 列归属): 502 all_tiers_exhausted ×2 + 502 zombie_empty_completion ×1 均
  caller=hermes, cc2 主链 0 bad。
- cc_requests fallback = 0 次 (122 req 全 200, SR=100%)。
- docker logs nv_gw buffer 段: cc4101-primary 全 attempt=1 success, 无错误噪音。
- health: 4101/40006/40066 全 200。

## 关键判断
cc2 主链路连续第 **66** 轮 (R893-R958) 100% SR 干净, 且主链专属错误 0 rows。
3 个 bad 请求 100% 属 hermes (caller 列归属 all_tiers_exhausted ×2 + zombie_empty_completion ×1),
fallback 0 次, 无新 cc2 主链错误类。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 tier round-robin (dsv4f0731_nv 为首) + func_health 健康选择已达稳态, hermes 的
all_tiers_exhausted/zombie 由 hermes 自身 key pool 疲劳所致, 不泄漏进 cc2。

## 下一步
- 继续 NOP 巡检; 下轮重拉 30min 窗口。
- 若 cc4101-primary 专属错误 > 0 或 SR < 99%, 先找根因再小步改 (铁律 1/2)。
- 观察 hermes 线 all_tiers_exhausted/zombie 是否持续或泄漏进 cc2; hermes 线 bad 越界不属
  cc2 范围, 0 泄漏进 cc2 即无行动。