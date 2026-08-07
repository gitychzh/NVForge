# R1017 — cc2 NOP inspection round

**日期**: 2026-08-07 16:45 CST
**上轮**: R1016 (NOP, 主链 130/130=100%)
**决策**: **NOP 巡检轮 — 不改码** (主链 127/127=100%, 无新错误)

## 本轮数据 (30min window, live 复核)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **127/127 = 100% SR, 0 bad** (live 查询 caller=cc4101-primary) | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | ✅ |
| nv_requests 总 bad (非 200) | 4 条 (皆 502), 经 DB `SELECT caller` 铁证全属 hermes | ✅(主链) |
| 30min cc_requests | 2039 request, fallback 0 次 (0.0%) | ✅ |
| 30min nv_tier_attempts JOIN | fid 281478d0 (good)→128 全 cc4101-primary; fid 52e1ddb6(bad)→16 全 hermes | ✅(host 分离) |
| 容器 | nv_gw Up 13h, cc4101 Up 12h, dsv4p_nv40066 Up 2d, /health 全 200 | ✅ |

## 本轮改动 + 依据

### 改动: 无 (NOP)

### 依据 (live 复核 2026-08-07 16:45 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **127/127 全 200 = 100% SR, 0 bad** (live `SELECT caller,status,count(*) ... caller='cc4101-primary'`)。
- 主链专属错误 (caller=cc4101-primary, status!=200) = **0 rows** (nv_requests 总 bad 仅 4 条 caller=hermes)。
- 30min 错误分类: bad 4 条 (502), error_type = all_tiers_exhausted(2)/NVStream_IncompleteRead(1)/stream_absolute_cap(1),
  经 `SELECT caller,error_type FROM nv_requests WHERE status!=200` 确认 4 行全 caller=hermes — 与主链 host 分离保持。
- **fid JOIN 铁证**: `SELECT t.tier,left(function_id,8),caller,count(*) FROM nv_tier_attempts t LEFT JOIN nv_requests r ON t.request_id=r.request_id`
  → 主链 fid 281478d0 = **128 attempts 全 cc4101-primary**; 越界 fid 52e1ddb6 = **16 attempts 全 hermes**。
  host 分离完全干净, 主链从未触碰坏 fid。
- fallback (cc_requests 30min 2039 request) = **0 次 / 0.0%** 无 fallback 触发。
- nv_tier_attempts per-key: 5 key 全健康, pexec_success 主导, 瞬态 RemoteDisconnected(14)/Timeout(3)/empty_200(1)
  全被 buffer 一次 attempt 吸收, 未穿透到 caller。
- 主链当前首代模型 = dsv4f0731_nv (fid 281478d0), 无 tier 降级/无 key 疲劳。

## 验证
- docker exec logs_db psql: `SELECT caller,status,count(*) FROM nv_requests WHERE ts>now()-interval'30 min' GROUP BY 1,2` → cc4101-primary 127 行全 200; 4 行 bad 全 caller=hermes。
- `SELECT caller,error_type FROM nv_requests WHERE ts>now()-interval'30 min' AND status!=200` → 4 行全 hermes (all_tiers_exhausted 2 / NVStream_IncompleteRead 1 / stream_absolute_cap 1)。
- JOIN 铁证: 主链 fid 281478d0 全 cc4101-primary, 坏 fid 52e1ddb6 全 hermes — host 分离干净, 无泄漏到主链。
- `SELECT count(*),sum(fallback_triggered) FROM cc_requests WHERE ts>now()-interval'30 min'` → 2039/0 (0.0%)。
- nv_tier_attempts 瞬态错误全被 buffer (attempt=1) 吸收, 未穿透到 caller。
- health: 40006/4101/40066 全 200; 容器 nv_gw Up 13h / cc4101 Up 12h / dsv4p_nv40066 Up 2d。

## 关键判断
cc2 主链路连续第 **125** 轮 (R893-R1017) 100% SR 干净, 主链专属错误 0 rows。
本轮 4 条 bad (502) 归属全属 hermes 越界宿主, 经 fid JOIN 铁证 (52e1ddb6 越界 fid 16 attempts 全 hermes,
主链 fid 281478d0 全 cc4101-primary) 与主链 host 分离完全干净 — 主链 127/127 全 200。
fallback 0 次 (0.0%), 无新 cc2 主链错误类, 无持久 key 疲劳。
multi-key round-robin + func_health + buffer (attempt=1 全成功) 完全吸收瞬态错误,
未穿透到 caller, 已达稳态。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②本轮 bad 全属 hermes 越界, 主链无根因可查;
③参数处于稳态, 无参数可调。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv (fid 281478d0) 为首代, 无需参数改动。
- 后续窗口继续确认 hermes 越界 bad (fid 52e1ddb6) 是否持续与主链隔离 (host 分离保持)。

## 容器健康
- nv_gw Up 13h, cc4101 Up 12h, dsv4p_nv40066 Up 2d; /health 40006/4101/40066 全 200。
- 配置快照: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, nv_gw nv_default_model=glm5_2_nv,
  NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_MAX_RETRIES=5, KeyManager 429 120s-600s 退避,
  ProbeWorker 15s, WaitQueue max 120s, nv_breaker mid-stream 软挂→OPEN。
  deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle。ms_gw fallback 保持不禁用。