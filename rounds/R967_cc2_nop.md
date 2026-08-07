# R967 — cc2 NOP 巡检轮 (不改码)

## 结论
cc2 主链路连续第 **75** 轮 (R893-R967) 100% SR 干净, 主链专属错误 0 行, fallback 0 次。
**不改码**。

## 数据 (注入轮前链路分析 ≈2026-08-07 12:45 CST + live 复核 health)

- **cc4101-primary (主 nv_gw:40006) = 126/126 全 200 = 100% SR, 0 bad**
- 全局 nv_requests 30min = 152 req, dsv4f0731_nv SR=98.0% (149/152)
- 3 bad (非 200) = **均 caller=hermes + fid=52e1ddb6** (已知坏 fid, hermes 宿主越界容器):
  `zombie_empty_completion ×2` + `all_tiers_exhausted ×1`
  (caller 列 + fid 双重归属 hermes, 双重隔离 non cc2; 与上轮同为 fid 52e1ddb6)
- fallback (cc_requests 30min) = **0 次** (152 req 全 status=200, SR=100%)
- nv_tier_attempts 30min (per-key): pexec_success 25/25/25/24/27 (k0-k4) +
  NVCFPexecRemoteDisconnected k0×3,k1×2,k2×4,k3×5,k4×5 + 529_nv_overloaded k1×1 +
  NVCFPexecTimeout k4×1 + empty_200 k0×1,k2×1
  (全瞬态, 被多 key round-robin + func_health + buffer 全部吸收 → resolve 200)
- buffer 日志 (nv_gw): 无 BUFFER-/WAIT-/KEYMGR- 错误噪声; cc4101-primary 全成功流
- health: 4101/40006/40066 全 200; 容器 nv_gw Up 9h, cc4101 Up 9h, dsv4p_nv40066 Up 2d

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | 126/126 = 100% SR, 0 bad | ✅ |
| 主链专属错误 (caller=cc4101-primary) | 0 rows | ✅ |
| 唯一 bad (非 200) | 502 zombie_empty_completion ×2 + all_tiers_exhausted ×1 (均 hermes, fid=52e1ddb6) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes + fid=52e1ddb6, cc2 primary 0 条 | ✅ 隔离 |
| 全局 nv_requests SR | 149/152 = 98.0% (dsv4f0731_nv) | ✅ |
| fallback (cc_requests) | 0 次 (152 req 全 200) | ✅ |

### 比对上轮 (R966)

| 指标 | R966 | R967 | 变化 |
|---|---|---|---|
| cc2 primary SR | 126/126 (100%) | 126/126 (100%) | ✅ 持平 |
| 主链专属错误 | 0 | 0 | ✅ 持平 |
| bad 非 200 | 3 (全 hermes) | 3 (全 hermes) | ✅ 持平 |
| fallback | 0 | 0 | ✅ 持平 |

## 关键判断
cc2 主链路连续第 **75** 轮 (R893-R967) 100% SR 干净, 主链专属错误 0 rows。
3 个 bad 请求 100% 属 hermes (caller+fid 双重归属, 均落在已知坏 fid 52e1ddb6 上),
fallback 0 次, 无新 cc2 主链错误类, 无持久 key 疲劳。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 key round-robin (dsv4f0731_nv 为首) + func_health + buffer 已达稳态, 瞬态错误
(RemoteDisconnected 19 / 529 1 / Timeout 1 / empty_200 2) 全被吸收。

## 下一步
- 继续观察 hermes 侧 bad fid 52e1ddb6 是否仍稳定隔离在 hermes 宿主 (不泄漏进 cc2)。
- 若 cc2 主链出现新错误类或 SR < 100%, 立即转修复轮。