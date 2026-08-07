# R964 — cc2 NOP 巡检轮 (不改码)

## 结论
cc2 主链路连续第 **72** 轮 (R893-R964) 100% SR 干净, 主链专属错误 0 行, fallback 0 次。
**不改码**。

## 数据 (live `/opt/cc-infra` 30min, ≈2026-08-07 12:33 CST)

- **cc4101-primary (主 nv_gw:40006) = 125/125 全 200 = 100% SR, 0 bad**
- 全局 nv_requests 30min = 135 req, dsv4f0731_nv SR=97.8% (132/135)
- 3 bad (非 200) = **均 caller=hermes + fid=52e1ddb6** (已知坏 fid, hermes 宿主越界容器):
  `all_tiers_exhausted ×2` + `zombie_empty_completion ×1`
  (caller 列 + fid 双重归属 hermes, 双重隔离 non cc2)
- fallback (cc_requests 30min) = **0 次** (125 req 全 status=200, SR=100%)
- nv_tier_attempts 30min (per-key): pexec_success 24/22/26/23/25 (k0-k4) +
  NVCFPexecRemoteDisconnected k0×1,k1×1,k2×2,k3×5,k4×5 + 529_nv_overloaded k1×1 +
  NVCFPexecTimeout k0×1,k4×1 + empty_200 k0×1,k2×1
  (全瞬态, 被多 key round-robin + func_health + buffer 全部吸收 → resolve 200)
- buffer 日志 (nv_gw --since 30m): cc4101-primary 全 **attempt=1 verdict=success_tool_call /
  success_text**, 无 WAIT-/KEYMGR- 错误噪声 (645 条式 buffer/wait 行, 纯成功流)
- health: 4101/40006/40066 全 200; 容器 nv_gw Up 14h, cc4101 Up 9h

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | 125/125 = 100% SR, 0 bad | ✅ |
| 主链专属错误 (caller=cc4101-primary) | 0 rows | ✅ |
| 唯一 bad (非 200) | 502 all_tiers_exhausted ×2 + zombie_empty_completion ×1 (均 hermes, fid=52e1ddb6) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes + fid=52e1ddb6, cc2 primary 0 条 | ✅ 隔离 |
| 全局 nv_requests SR | 132/135 = 97.8% (dsv4f0731_nv) | ✅ |
| fallback (cc_requests) | 0 次 (125 req 全 200) | ✅ |

### 比对上轮 (R963)

| 指标 | R963 | R964 | 变化 |
|---|---|---|---|
| cc2 primary SR | 121/121 (100%) | 125/125 (100%) | ✅ 持平 |
| primary scoped errors | 0 | 0 | ✅ |
| fallback | 0 | 0 | ✅ |
| bad hermes (fid 52e1ddb6) | 3 | 3 | 持平 |
| 连续干净轮 | 71 | **72** | ✅ |

## 验证
- nv_requests cc4101-primary live pull = 125/125 (0 bad, 100% SR)。
- bad 分组 (caller+fid): 502 all_tiers_exhausted ×2 + 502 zombie_empty_completion ×1
  均 caller=hermes + fid=52e1ddb6, cc2 主链 0 bad, 0 泄漏进 cc2。
- cc_requests fallback = 0 次 (125 req 全 200, SR=100%)。
- docker logs nv_gw buffer 段: cc4101-primary 全 attempt=1 success_tool_call/success_text,
  无错误噪音。
- health: 4101/40006/40066 全 200。

## 关键判断
cc2 主链路连续第 **72** 轮 (R893-R964) 100% SR 干净, 主链专属错误 0 rows。
3 个 bad 请求 100% 属 hermes (caller+fid 双重归属 502 all_tiers_exhausted +
zombie_empty_completion, 均落在已知坏 fid 52e1ddb6 上), fallback 0 次, 无新 cc2 主链错误类。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 key round-robin (dsv4f0731_nv 为首) + func_health 健康选择已达稳态, hermes 的
all_tiers_exhausted/zombie 由 hermes 自身 key pool 疲劳 + 坏 fid 所致, 不泄漏进 cc2。
注入分析 "top error: all_tiers_exhausted" 归因正确——但其 caller=hermes 隔离, cc2 主链 0 命中。