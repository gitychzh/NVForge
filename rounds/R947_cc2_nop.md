# R947 cc2 NOP 巡检轮 (HM2 nv_gw 主链路)

> 轮次: R947 | 日期: 2026-08-07 CST | 类型: NOP (不改码)
> 结论: cc2 主链路连续 **55** 轮 100% 干净 (R893→R947);
> cc4101-primary 30min = **119/119 = 100% SR, 0 bad** (live 实拉);
> cc4101-primary 专属错误 = **0 rows**; 坏请求全属 hermes 线, 未进 cc2 主链; fallback = 0 次。

## 改动

无 (NOP。主链 100% 干净 + 专属错误 0 行, 无新错误类, bad 全越界 hermes)。

## 依据 (live DB 30min 实拉 ≈2026-08-07 11:30 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **119/119 全 200, 0 bad (100% SR)** (live re-pull 确认)。
- 30min **cc4101-primary 专属错误 = 0 rows** (status != 200 AND caller='cc4101-primary' 全空)。
- 30min 所有 bad (非 200) = `caller=hermes` ×5: `all_tiers_exhausted ×3` + `stream_absolute_cap ×1` + `zombie_empty_completion ×1`
  (模型行 `hermes|dsv4f0731_nv|502|5` 即这 5 条, caller 列归属 hermes, host-separated, 0 个进入 cc2 主链)。
- zombie_empty_completion 保持 **1** (R941 首现 1 → R947 连续第 7 轮保持 1, 稳定未扩散, 越界 hermes 不构成 cc2 风险)。
- fallback (cc_requests 30min) = **0 次** (120 req, fb=0, SR=100.0)。
- nv_tier_attempts 30min per-key: 全 key pexec_success 主导 (k0:23/k1:23/k2:25/k3:24/k4:24) +
  NVCFPexecRemoteDisconnected (k0:4/k1:1/k2:5/k3:3/k4:3) + NVCFPexecTimeout (k1:1/k4:2) + empty_200 (k1:2/k3:1)。
  瞬态错误被多 tier round-robin + buffer 重试吸收, 全部 resolve 为 200 (主链 0 bad)。
- buffer 日志: cc4101-primary 全 attempt=1 成功 (elapsed 7~15s, verdict=success_tool_call), 无 WAIT-/KEY- 错误。
- 容器 health: 4101/40006/40066 全 ok (200)。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **119/119 = 100% SR, 0 bad** (实拉) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| hermes 线 bad (非 200) | all_tiers_exhausted ×3 + stream_absolute_cap ×1 + zombie_empty_completion ×1 (502×5) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (SR=100.0%) | ✅ |
| zombie_empty_completion | 1 (R941 首现 → R947 连续第 7 轮保持 1 未扩散) | ⚠️ 观察 |
| tier 瞬态错误 | RemoteDisconnected 16 + empty_200 3 + Timeout 3, 全被吸收 | ✅ |
| scoped health | 4101/40006/40066 全 ok (200) | ✅ |
| 容器 UP | nv_gw 13h / cc4101 8h / dsv4p 2d (平稳) | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok (200)。
- 30min nv_requests cc4101-primary live re-pull = 119/119 (0 bad); 专属错误 0 rows。
- 30min 所有 bad 分组 (caller 列归属): 全 hermes, cc2 主链 0 bad。
- cc_requests fallback = 0 次。
- docker logs nv_gw buffer 段: cc4101-primary 全 attempt=1 success (success_tool_call, 7~15s), 无错误噪音。

### 关键判断
cc2 主链路连续第 **55** 轮 (R893-R947) 100% SR 干净, 且 30min 主链专属错误实拉 0 rows。
bad 请求 100% 属 hermes (caller 列归属, 未进 cc2 主链), fallback 0 次, 无新 cc2 主链错误类。
zombie_empty_completion 连续第 7 轮保持单例 (R941→R947), 未扩散, 属 hermes 越界。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 tier round-robin + func_health 健康选择已达稳态, buffer 全 1-attempt 成功, tier 瞬态错误全被吸收 (RemoteDisconnected 16 全被 round-robin 消化)。

> ⚠️ 观察项 (R947): nv_gw Up 13h (与 R946 持平区间, 平稳无重启回归);
> 同机 `nv_gw_stable Up 5d` 并存, dsv4p_nv40066 Up 2d。zombie_empty_completion 连续第 7 轮保持单例未扩散,
> 全属 hermes 宿主越 cc2 范围, 不构成 cc2 风险。下轮继续观察 hermes zombie 是否扩散。