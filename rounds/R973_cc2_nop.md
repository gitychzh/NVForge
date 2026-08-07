# R973 — cc2 NOP 巡检轮 (不改码)

## 结论
cc2 主链路连续第 **81** 轮 (R893-R973) 100% SR 干净, 主链专属错误 0 行, fallback 0 次。
**不改码**。

## 数据 (注入轮前链路分析 ≈2026-08-07 13:12 CST + live 复核 bad 归属/fallback)

- **cc4101-primary (主 nv_gw:40006) = 111/111 全 200 = 100% SR, 0 bad** (live 复核)
- 全局 nv_requests 30min = 125 req, dsv4f0731_nv SR=97.6% (122/125)
- 3 bad (非 200) = **均 caller=hermes + fid=52e1ddb6** (已知坏 fid, hermes 宿主越界容器):
  `502 all_tiers_exhausted ×2` + `502 stream_absolute_cap ×1`
  (caller 列 + fid 双重归属 hermes, 双重隔离 non cc2)
- fallback (cc_requests 30min) = **0 次** (111 req live, fb=0)
- nv_tier_attempts 30min (per-key): pexec_success 20~24 (k0-k4) +
  NVCFPexecRemoteDisconnected 散落 k0-k4 (~17) + NVCFPexecTimeout k0×1 + empty_200 k3×1
  (全瞬态, 被多 key round-robin + func_health + buffer 全部吸收 → resolve 200)
- buffer 日志 (nv_gw): 本轮无 BUFFER-/WAIT-/KEYMGR- 错误噪声 (无 buffer 日志输出,
  cc4101-primary 全走 buffer attempt=1 成功流)
- 容器: nv_gw Up 14h+, cc4101 Up 9h+

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | 111/111 = 100% SR, 0 bad (live 复核) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | 0 rows | ✅ |
| 唯一 bad (非 200) | 502 all_tiers_exhausted ×2 + stream_absolute_cap ×1 (均 hermes, fid=52e1ddb6) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes + fid=52e1ddb6, cc2 primary 0 条 | ✅ 隔离 |
| 全局 nv_requests SR | 122/125 = 97.6% (dsv4f0731_nv) | ✅ |
| fallback (cc_requests) | 0 次 (111 req live 全未 fb) | ✅ |
| tier 瞬态错误 | RemoteDisconnected ~17 / NVCFPexecTimeout 1 / empty_200 1, 全被吸收 | ✅ |

### 比对上轮 (R972)

| 指标 | R972 | R973 | 变化 |
|---|---|---|---|
| cc2 primary SR | 111/111 (100%) | 111/111 (100%) | ✅ 持平 |
| 主链专属错误 | 0 | 0 | ✅ 持平 |
| bad 非 200 | 3 (全 hermes) | 3 (全 hermes) | ✅ 持平 |
| fallback | 0 | 0 | ✅ 持平 |

## 判断
主链 100% SR + 专属错误 0 行, bad 全属 hermes (fid 52e1ddb6) 越 cc2 范围, fallback 0, tier 瞬态全被吸收。
无新优化需求。**不改码** (NOP)。

## 验证
- live 复核: cc4101-primary = 111/111 = 100% SR, 0 bad。
- bad 分组 (caller+fid): 502 all_tiers_exhausted ×2 + stream_absolute_cap ×1
  均 caller=hermes + fid=52e1ddb6, cc2 主链 0 bad。
- cc_requests fallback = 0 次 (111 req live 全未 fallback_triggered)。
- docker logs nv_gw: 无 BUFFER-/WAIT-/KEYMGR- 错误噪声; cc4101-primary 全 attempt=1 成功流。
- 容器全 upstream: nv_gw Up 14h+, cc4101 Up 9h+ (health 40006 + 4101 全 200)。