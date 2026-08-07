# R950 cc2 NOP 巡检轮 (HM2 nv_gw 主链路)

> 轮次: R950 | 日期: 2026-08-07 CST | 类型: NOP (不改码)
> 结论: cc2 主链路连续 **58** 轮 100% 干净 (R893→R950);
> cc4101-primary 30min = **117/117 = 100% SR, 0 bad** (live 实拉);
> cc4101-primary 专属错误 = **0 rows**; 坏请求全属 hermes 线, 未进 cc2 主链; fallback = 0 次。

## 改动

无 (NOP。主链 100% 干净 + 专属错误 0 行, 无新错误类, bad 全越界 hermes)。

## 依据 (live DB 30min 实拉 ≈2026-08-07 11:5x CST)

- 30min cc4101-primary (主 nv_gw:40006) = **117/117 全 200, 0 bad (100% SR)** (live re-pull 确认)。
- 30min **cc4101-primary 专属错误 = 0 rows** (status != 200 AND caller='cc4101-primary' 全空)。
- 30min 所有 bad (非 200) = `caller=hermes` ×3: `all_tiers_exhausted ×2` + `stream_absolute_cap ×1`
  (caller 列 + host_machine 双重归属 = host `opc2sname-dsv4f40666`, 全坏 fid `52e1ddb6`,
  hermes 越界泄漏源, 未进 cc2 主链)。
- zombie_empty_completion 本轮窗口未现 (R941 首现 1 → R948 连续 8 轮 1 → R949 0 → R950 0, 属 hermes 越界, 不构成 cc2 风险)。
- fallback (cc_requests 30min) = **0 次** (118 req, fb=0, SR=100.0)。
- nv_tier_attempts 30min per-key: 全 key pexec_success 主导 (k0:22/k1:24/k2:24/k3:23/k4:24) +
  NVCFPexecRemoteDisconnected (k0:3/k1:3/k2:6/k3:4/k4:2) + NVCFPexecTimeout (k4:2) + empty_200 (k1:1)。
  瞬态错误被多 tier round-robin + buffer 重试吸收, 全部 resolve 为 200 (主链 0 bad)。
- buffer 日志: cc4101-primary 全 attempt=1 成功 (elapsed 5~10s, verdict=success_tool_call), 无 WAIT-/KEYMGR- 错误。
- 容器 health: 4101/40006/40066 全 ok (200)。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **117/117 = 100% SR, 0 bad** (实拉) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| hermes 线 bad (非 200) | all_tiers_exhausted ×2 + stream_absolute_cap ×1 (502×3) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes + host=40666 + bad fid 52e1ddb6; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (SR=100.0%) | ✅ |
| zombie_empty_completion | 窗口 0 (R941→R948 保持 1, R949→R950 未现) | ✅ |
| tier 瞬态错误 | RemoteDisconnected 18 + empty_200 1 + Timeout 2, 全被吸收 | ✅ |
| scoped health | 4101/40006/40066 全 ok (200) | ✅ |
| 容器 UP | nv_gw 8h / cc4101 8h / dsv4p_nv40066 2d / 40666 18h(越界) | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok (200)。
- 30min nv_requests cc4101-primary live re-pull = 117/117 (0 bad); 专属错误 0 rows。
- 30min 所有 bad 分组 (caller 列 + host_machine 双重归属): 全 hermes (host=dsv4f40666, 坏 fid 52e1ddb6), cc2 主链 0 bad。
- cc_requests fallback = 0 次。
- docker logs nv_gw buffer 段: cc4101-primary 全 attempt=1 success (success_tool_call, 5~10s), 无错误噪音。

### 关键判断
cc2 主链路连续第 **58** 轮 (R893-R950) 100% SR 干净, 且 30min 主链专属错误实拉 0 rows。
bad 请求 100% 属 hermes (caller 列 + host_machine 双重归属: host=opc2sname-dsv4f40666, 坏 fid
52e1ddb6, 未进 cc2 主链), fallback 0 次, 无新 cc2 主链错误类。
hermes zombie_empty_completion 本轮窗口未现 (R949→R950 连续 2 轮 0)。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 tier round-robin + func_health 健康选择已达稳态, buffer 全 1-attempt 成功, tier 瞬态错误全被吸收 (RemoteDisconnected 18 全被 round-robin 消化)。

> ⚠️ 观察项 (R950): nv_gw Up 8h (容器于上次重启后运行平稳);
> 同机 `nv_gw_stable Up 5d` 并存, dsv4p_nv40066 Up 2d, dsvf0731_nv40666 Up 18h(hermes 越界泄漏源)。
> hermes zombie_empty_completion 本轮窗口 0, 全属 hermes 宿主越 cc2 范围, 不构成 cc2 风险。下轮继续观察。