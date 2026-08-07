# R966 — cc2 NOP 巡检轮 (不改码)

## 结论
cc2 主链路连续第 **74** 轮 (R893-R966) 100% SR 干净, 主链专属错误 0 行, fallback 0 次。
**不改码**。

## 数据 (live `/opt/cc-infra` 30min, ≈2026-08-07 12:45 CST)

- **cc4101-primary (主 nv_gw:40006) = 126/126 全 200 = 100% SR, 0 bad**
- 全局 nv_requests 30min = 151 req, dsv4f0731_nv SR=98.0% (148/151)
- 3 bad (非 200) = **均 caller=hermes + fid=52e1ddb6** (已知坏 fid, hermes 宿主越界容器):
  `zombie_empty_completion ×2` + `all_tiers_exhausted ×1`
  (caller 列 + fid 双重归属 hermes, 双重隔离 non cc2; 与上轮同为 fidd52e1ddb6,
  仅 error-type 计数互换 zombie×2↔all_tiers×1)
- fallback (cc_requests 30min) = **0 次** (126 req 全 status=200, SR=100%)
- nv_tier_attempts 30min (per-key): pexec_success 26/25/24/24/28 (k0-k4) +
  NVCFPexecRemoteDisconnected k0×2,k1×2,k2×3,k3×4,k4×4 + 529_nv_overloaded k1×1 +
  NVCFPexecTimeout k4×1 + empty_200 k0×1,k2×1
  (全瞬态, 被多 key round-robin + func_health + buffer 全部吸收 → resolve 200)
- buffer 日志 (nv_gw --since 35m): cc4101-primary 绝大多数 **attempt=1 verdict=success_tool_call /
  success_text**; 一请求 attempt=1 execute_failed(all_keys_exhausted)→backoff 5s→attempt=2
  success_tool_call (flushed 14386b in 2 attempts, 40s) — 正常容错, 非 cc2 持久错误
- health: 4101/40006/40066 全 200; 容器 nv_gw Up 9h, cc4101 Up 9h, dsv4p_nv40066 Up 2d

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | 126/126 = 100% SR, 0 bad | ✅ |
| 主链专属错误 (caller=cc4101-primary) | 0 rows | ✅ |
| 唯一 bad (非 200) | 502 zombie_empty_completion ×2 + all_tiers_exhausted ×1 (均 hermes, fid=52e1ddb6) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes + fid=52e1ddb6, cc2 primary 0 条 | ✅ 隔离 |
| 全局 nv_requests SR | 148/151 = 98.0% (dsv4f0731_nv) | ✅ |
| fallback (cc_requests) | 0 次 (126 req 全 200) | ✅ |

### 比对上轮 (R964)

| 指标 | R964 | R966 | 变化 |
|---|---|---|---|
| cc2 primary SR | 125/125 (100%) | 126/126 (100%) | ✅ 持平 |
| primary scoped errors | 0 | 0 | ✅ |
| fallback | 0 | 0 | ✅ |
| bad hermes (fid 52e1ddb6) | 3 | 3 | 持平 |
| 连续干净轮 | 72 | **74** | ✅ |

## 验证
- nv_requests cc4101-primary live pull = 126/126 (0 bad, 100% SR)。
- bad 分组 (caller+fid): 502 zombie_empty_completion ×2 + 502 all_tiers_exhausted ×1
  均 caller=hermes + fid=52e1ddb6, cc2 主链 0 bad, 0 泄漏进 cc2。
- cc_requests fallback = 0 次 (126 req 全 200, SR=100%)。
- docker logs nv_gw buffer 段: cc4101-primary 全成功流, 无 WAIT-/KEYMGR- 错误噪声。
- health: 4101/40006/40066 全 200。

## 关键判断
cc2 主链路连续第 **74** 轮 (R893-R966) 100% SR 干净, 主链专属错误 0 rows。
3 个 bad 请求 100% 属 hermes (caller+fid 双重归属 502 zombie_empty_completion +
all_tiers_exhausted, 均落在已知坏 fid 52e1ddb6 上), fallback 0 次, 无新 cc2 主链错误类。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 key round-robin (dsv4f0731_nv 为首) + func_health + buffer (attempt=2 亦能成功 flush)
已达稳态, hermes 的 all_tiers_exhausted/zombie 由 hermes 自身 key pool 疲劳 + 坏 fid 所致,
不泄漏进 cc2。注入分析 "top error: zombie_empty_completion" 归因正确——但其 caller=hermes 隔离,
cc2 主链 0 命中。