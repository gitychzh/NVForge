# R986 cc2 NOP inspection round

> 类型: NOP 巡检轮 / 不改码
> cc4101-primary (主 nv_gw:40006) 30min = **122/122 = 100% SR, 0 bad** (live 复核)
> 连续干净轮: **第 94 轮 (R893-R986)**
> 容器: nv_gw Up (11h), cc4101 Up (10h)

## 数据 (live 复核 2026-08-07 ≈14:17 CST)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **122/122 = 100% SR, 0 bad** (live) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| 唯一 bad (非 200) | 502 all_tiers_exhausted ×3 + 502 NVStream_IncompleteRead ×1 | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes + 已知坏 fid 52e1ddb6 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (122 req 全未 fb) | ✅ |
| tier 瞬态错误 | RemoteDisconnected / Timeout / empty_200 (k0-k4 散落) 全被吸收 | ✅ |
| buffer 效果 | 全 attempt=1 success (~4-10s flush), 无 retry/WAIT-/KEYMGR- 噪声 | ✅ |
| 容器 | nv_gw Up 11h, cc4101 Up 10h, /health 40006 全 200 | ✅ |

## 判断
- SR 100% ≥ 99%, 无主链专属新错误 → **NOP 巡检轮, 不改码**。
- 唯一 4 个 bad 请求 100% 属 hermes (caller=hermes + 已知坏 fid 52e1ddb6), nv_requests caller 归属
  铁证隔离, 非 cc2 主链。R897 起 host 分离持续保持。
- tier 瞬态错误被多 key round-robin + func_health + buffer 完全吸收, 全部 resolve 为 200。no 持久 key 疲劳。
- fallback 0 次, no ms_gw 请求。

## 配置快照 (未改)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 保持不禁用), NVU_BUFFER_MAX_RETRIES=5,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, TIER_TIMEOUT_BUDGET_S=180, UPSTREAM_TIMEOUT=90.
- 主链首代模型 dsv4f0731_nv, 多 key round-robin + func_health 健康自适应吸收瞬态失败。

## 下一步
- 保持 NOP 观察; 主链 dsv4f0731_nv 健康无参数可调。
- 继续监控 hermes bad (fid 52e1ddb6) host 隔离是否持续 (R897 起稳定)。