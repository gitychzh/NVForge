# R987 cc2 — NOP 巡检轮 (主链 100% 干净, 唯一 bad 全属 hermes 越界)

> 轮次: R987 | 日期: 2026-08-07 | 类型: NOP (不改码)
> cc2 主链路连续第 **95** 轮 100% 干净 (R893-R987)。

## 结论一句话
cc4101-primary (主 nv_gw:40006 → dsv4f0731_nv) 30min = **125/125 = 100% SR, 0 bad**;
唯一 6 个 bad 请求 100% 属 `caller=hermes` (all_tiers_exhausted ×4 + NVStream_IncompleteRead
×1 + zombie_empty_completion ×1), 越界 non-cc2; fallback = 0 次。**不改码。**

## 改动
无 (NOP。主链 125/125 全 200, 主专属错误 0 行; 唯一 bad 全属 hermes + 已知坏 fid 52e1ddb6 线)。

## 依据 (live 复核)
- 30min nv_requests `caller=cc4101-primary` = **125/125 全 200 = 100% SR, 0 bad** (live)。
- 总 nv_requests bad (非 200) = **6 条, 全 `caller=hermes`**: all_tiers_exhausted ×4 +
  NVStream_IncompleteRead ×1 + zombie_empty_completion ×1。hermes 为宿主越界 over-limit 容器
  (已知坏 fid 52e1ddb6 线), non-cc2 主链, host 分离。
- fallback (cc_requests 30min) = **0 次** (127 req 全未 fallback_triggered)。
- nv_tier_attempts 30min: pexec_success 主导 + NVCFPexecRemoteDisconnected 散落 +
  NVCFPexecTimeout + empty_200 — 全瞬态, 被多 key round-robin + func_health + buffer 吸收,
  全部 resolve 为 200。
- 容器: nv_gw Up 11h, cc4101 Up 10h; /health 40006 + 4101 全 200。

## 本轮数据表
| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **125/125 = 100% SR, 0 bad** (live) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| 唯一 bad (非 200) | 6 条, 全 caller=hermes (all_tiers×4 + NVStream×1 + zombie×1) | ⚠️ 越界 |
| bad caller 归属 | 100% caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (127 req 全未 fb) | ✅ |
| tier 瞬态错误 | RemoteDisconnected / Timeout / empty_200, 全被吸收 | ✅ |
| 容器 | nv_gw Up 11h, cc4101 Up 10h | ✅ |

## 验证
- 30min nv_requests cc4101-primary = 125/125 (0 bad)。
- bad 分组 (by caller×err_type): hermes|all_tiers_exhausted ×4, hermes|NVStream_IncompleteRead
  ×1, hermes|zombie_empty_completion ×1 — 全 hermes, cc2 主链 0 bad。
- cc_requests fallback = 0 次 (127 req 全未 fallback_triggered)。
- health: 4101/40006 全 200; 容器 nv_gw/cc4101 皆 Up。

## 修正 (相对注入 pre-analysis)
注入段总 SR=95.7% 是因把 hermes 请求混入统计; live 按 caller 切分后 cc4101-primary 实为
100% (125/125), bad 清一色 hermes。cc2 主链不受影响。

## 下一步
- 保持 NOP 观察; 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 继续监控 hermes bad (fid 52e1ddb6) 是否与主链容器保持 host 分离 (R897 起持续隔离)。

## 容器健康 / 参数快照
- nv_gw Up 11h, cc4101 Up 10h; /health 40006+4101 全 200。
- 配置: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, nv_gw nv_default_model=glm5_2_nv,
  NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_MAX_RETRIES=5, MS fallback 不禁用。