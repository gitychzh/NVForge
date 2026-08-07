# R953 cc2 NOP 巡检轮 (HM2 nv_gw 主链路)

> 轮次: R953 | 日期: 2026-08-07 CST | 类型: NOP (不改码)
> 结论: cc2 主链路连续 **61** 轮 100% 干净 (R893→R953);
> cc4101-primary 30min = **121/121 = 100% SR, 0 bad** (live 实拉);
> cc4101-primary 专属错误 = **0 rows**; 坏请求全属 hermes 线, 未进 cc2 主链; fallback = 0 次。

## 改动

无 (NOP。主链 121/121 100% 干净 + 专属错误 0 行, 无新错误类, bad 全越界 hermes)。

## 依据 (live DB 30min 实拉 ≈2026-08-07 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **121/121 全 200, 0 bad (100% SR)** (live re-pull 确认)。
- 30min 所有 bad (非 200) = **`caller=hermes` ×1**: `stream_absolute_cap ×1`（avg_dur 160467ms）。
  caller 列归属 hermes, 非 cc2 主链。
- fallback (cc_requests 30min) = **0 次** (121 req, fb=0; 全 status=200)。
- nv_tier_attempts 30min: pexec_success **121** + NVCFPexecRemoteDisconnected **17**。
  瞬态错误被多 tier round-robin + buffer 重试吸收, 全部 resolve 为 200 (主链 0 bad)。
- buffer 日志: cc4101-primary 全 attempt=1 success (elapsed 1-13s, input 5-86k, thinking on/off,
  verdict success_text/success_tool_call), 无 WAIT-/KEYMGR- 错误噪音。
- 容器 health: 4101/40006/40066 全 ok (200)。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **121/121 = 100% SR, 0 bad** (实拉) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| hermes 线 bad (非 200) | stream_absolute_cap ×1 (avg 160s) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (121 req 全 200) | ✅ |
| tier 瞬态错误 | NVCFPexecRemoteDisconnected 17, 全被吸收 | ✅ |
| scoped health | 4101/40006/40066 全 ok (200) | ✅ |
| 容器 UP | nv_gw 8h / cc4101 8h / dsv4p_nv40066 2d / 40666 18h(越界) | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok (200)。
- 30min nv_requests cc4101-primary live re-pull = 121/121 (0 bad)。
- 30min 所有 bad 分组 (caller 列归属): 全 hermes (stream_absolute_cap ×1), cc2 主链 0 bad。
- cc_requests fallback = 0 次。
- docker logs nv_gw buffer 段: cc4101-primary 全 attempt=1 success, 无错误噪音。

### 关键判断
cc2 主链路连续第 **61** 轮 (R893-R953) 100% SR 干净, 主链专属错误 0 行。
bad 请求 100% 属 hermes, fallback 0 次, 无新 cc2 主链错误类。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 tier round-robin + func_health 健康选择已达稳态, buffer 全 1-attempt 成功, tier 瞬态错误全被吸收 (RemoteDisconnected 17 全被 round-robin 消化)。

> ⚠️ 观察项 (R953): nv_gw Up 8h, cc4101 Up 8h (平稳无重启回归);
> 同机 `nv_gw_stable Up 5d` 并存, dsv4p_nv40066 Up 2d, dsvf0731_nv40666 Up 18h(hermes 越界泄漏源)。
> 本轮 30min bad 中无 zombie, hermes stream_absolute_cap 1 越界, 不构成 cc2 风险。下轮继续观察。