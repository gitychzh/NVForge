# R971 — cc2 NOP 巡检轮 (不改码)

## 结论
cc2 主链路连续第 **79** 轮 (R893-R971) 100% SR 干净, 主链专属错误 0 行, fallback 0 次。
**不改码**。

## 数据 (注入轮前链路分析 ≈2026-08-07 13:04 CST + live 复核 bad 归属/fallback)

- **cc4101-primary (主 nv_gw:40006) = 116/116 全 200 = 100% SR, 0 bad** (live 复核)
- 全局 nv_requests 30min = 136 req, dsv4f0731_nv SR=97.8% (133/136)
- 3 bad (非 200) = **均 caller=hermes + fid=52e1ddb6** (已知坏 fid, hermes 宿主越界容器):
  `502 zombie_empty_completion ×1` + `502 stream_absolute_cap ×1` + `502 all_tiers_exhausted ×1`
  (caller 列 + fid 双重归属 hermes, 双重隔离 non cc2)
- fallback (cc_requests 30min) = **0 次** (116 req, fb=0, 全 status=200, SR=100%)
- nv_tier_attempts 30min (per-key): pexec_success 21~25 (k0-k4) +
  NVCFPexecRemoteDisconnected 散落 k0-k4 (~18) + empty_200 k2×1 + k3×1
  (全瞬态, 被多 key round-robin + func_health + buffer 全部吸收 → resolve 200)
- buffer 日志 (nv_gw): cc4101-primary 全 attempt=1 成功流 (success_tool_call 7~13s /
  success_text 1.4s), 无 WAIT-/KEYMGR- 错误噪声
- 容器: nv_gw Up 14h+, cc4101 Up 9h+

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | 116/116 = 100% SR, 0 bad (live 复核) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | 0 rows | ✅ |
| 唯一 bad (非 200) | 502 zombie_empty_completion + stream_absolute_cap + all_tiers_exhausted (均 hermes, fid=52e1ddb6) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes + fid=52e1ddb6, cc2 primary 0 条 | ✅ 隔离 |
| 全局 nv_requests SR | 133/136 = 97.8% (dsv4f0731_nv) | ✅ |
| fallback (cc_requests) | 0 次 (116 req 全 200) | ✅ |
| tier 瞬态错误 | RemoteDisconnected ~18 / empty_200 2, 全被吸收 | ✅ |

### 比对上轮 (R970)

| 指标 | R970 | R971 | 变化 |
|---|---|---|---|
| cc2 primary SR | 121/121 (100%) | 116/116 (100%) | ✅ 持平 |
| 主链专属错误 | 0 | 0 | ✅ 持平 |
| bad 非 200 | 3 (全 hermes) | 3 (全 hermes) | ✅ 持平 |
| fallback | 0 | 0 | ✅ 持平 |

## 判断
主链 100% SR + 专属错误 0 行, bad 全属 hermes (fid 52e1ddb6) 越 cc2 范围, fallback 0, tier 瞬态全被吸收。
无新优化需求。**不改码** (NOP)。

## 验证
- live 复核: cc4101-primary = 116/116 = 100% SR, 0 bad。
- bad 分组 (caller+fid): 502 zombie_empty_completion ×1 + stream_absolute_cap ×1 +
  all_tiers_exhausted ×1 均 caller=hermes + fid=52e1ddb6, cc2 主链 0 bad。
- cc_requests fallback = 0 次 (116 req 全 200)。
- docker logs nv_gw: 无错误噪声; cc4101-primary 全 attempt=1 成功流 (success_tool_call/success_text)。
- 容器全 upstream: nv_gw Up 14h+, cc4101 Up 9h+。