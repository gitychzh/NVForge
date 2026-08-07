# R952 cc2 NOP 巡检轮 (HM2 nv_gw 主链路)

> 轮次: R952 | 日期: 2026-08-07 CST | 类型: NOP (不改码)
> 结论: cc2 主链路连续 **60** 轮 100% 干净 (R893→R952);
> cc4101-primary 30min = **120/120 = 100% SR, 0 bad** (live 实拉);
> cc4101-primary 专属错误 = **0 rows**; 坏请求全属 hermes 线, 未进 cc2 主链; fallback = 0 次。

## 改动

无 (NOP。主链 120/120 100% 干净 + 专属错误 0 行, 无新错误类, bad 全越界 hermes)。

## 依据 (live DB 30-45min 实拉 ≈2026-08-07 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **120/120 全 200, 0 bad (100% SR)** (live re-pull 确认)。
- 45min 宽窗口 **cc4101-primary 专属错误 = 0 rows** (status != 200 AND caller='cc4101-primary' 全空)。
- 30min 所有 bad (非 200) = **`caller=hermes` ×1**: `stream_absolute_cap ×1` (caller 列归属 hermes, 非 cc2 主链)。
- fallback (cc_requests 30min) = **0 次** (119 req, fb=0; cc4101-primary 专属 SR=100%)。
- nv_tier_attempts 30min: pexec_success 120 (k0:23/k1:24/k2:25/k3:23/k4:24) +
  NVCFPexecRemoteDisconnected (k0:3/k1:3/k2:5/k3:3/k4:3)。
  瞬态错误被多 tier round-robin + buffer 重试吸收, 全部 resolve 为 200 (主链 0 bad)。
- buffer 日志: cc4101-primary 全 attempt=1 success (elapsed 1-13s), 无 WAIT-/KEYMGR- 错误噪音。
- 容器 health: 4101/40006/40066 全 ok (200)。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **120/120 = 100% SR, 0 bad** (实拉) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** (45min 宽窗) | ✅ |
| hermes 线 bad (非 200) | stream_absolute_cap ×1 (30min) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (cc4101-primary SR=100%) | ✅ |
| tier 瞬态错误 | NVCFPexecRemoteDisconnected 17, 全被吸收 | ✅ |
| scoped health | 4101/40006/40066 全 ok (200) | ✅ |
| 容器 UP | nv_gw 8h / cc4101 8h / dsv4p_nv40066 2d / 40666 18h(越界) | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok (200)。
- 30min nv_requests cc4101-primary live re-pull = 120/120 (0 bad); 45min 专属错误 0 rows。
- 30min 所有 bad 分组 (caller 列归属): 全 hermes (stream_absolute_cap ×1), cc2 主链 0 bad。
- cc_requests fallback = 0 次 (cc4101-primary SR=100%)。
- docker logs nv_gw buffer 段: cc4101-primary 全 attempt=1 success, 无错误噪音。

### 关键判断
cc2 主链路连续第 **60** 轮 (R893-R952) 100% SR 干净, 且主链专属错误实拉 0 rows (45min 宽窗)。
bad 请求 100% 属 hermes (caller 列归属), fallback 0 次, 无新 cc2 主链错误类。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 tier round-robin + func_health 健康选择已达稳态, buffer 全 1-attempt 成功, tier 瞬态错误全被吸收 (RemoteDisconnected 17 全被 round-robin 消化)。

> ⚠️ 观察项 (R952): nv_gw Up 8h (平稳无重启回归);
> 同机 `nv_gw_stable Up 5d` 并存, dsv4p_nv40066 Up 2d, dsvf0731_nv40666 Up 18h(hermes 越界泄漏源)。
> 本轮 zombie 未在 30min bad 中现, 她 main hermes stream_absolute_cap 1 越界, 不构成 cc2 风险。下轮继续观察。