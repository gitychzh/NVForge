# R1016 — cc2 NOP inspection round

**日期**: 2026-08-07 16:25 CST
**上轮**: R1015 (NOP, 主链 127/127=100%)
**决策**: **NOP 巡检轮 — 不改码** (主链 130/130=100%, 无新错误)

## 本轮数据 (30min window, live 复核)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **130/130 = 100% SR, 0 bad** (live 查询 caller=cc4101-primary) | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | ✅ |
| nv_requests 总 bad (非 200) | 4 条 (皆 502), 经 DB `SELECT caller` 铁证全属 hermes | ✅(主链) |
| 30min cc_requests | 131 request, fallback 0 次 (0.0%) | ✅ |
| 30min nv_tier_attempts | pexec_success(131) + RemoteDisconnected(14)/Timeout(3)/empty_200(1), 全被 buffer 吸收 | ✅ |
| 容器 | nv_gw Up 13h, cc4101 Up 12h, dsv4p_nv40066 Up 2d, /health 全 200 | ✅ |

## 本轮改动 + 依据

### 改动: 无 (NOP)

### 依据 (live 复核 2026-08-07 16:25 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **130/130 全 200 = 100% SR, 0 bad** (live `SELECT status,count(*) ... caller='cc4101-primary'`)。
- 主链专属错误 (caller=cc4101-primary, status!=200) = **0 rows** (nv_requests 总 bad 仅 4 条 caller=hermes)。
- 30min 错误分类: bad 4 条 (502), 经 `SELECT caller,status FROM nv_requests WHERE status!=200` 确认全 caller=hermes — 与主链 host 分离保持 (fid 52e1ddb6 泄漏路径)。
- fallback (cc_requests 30min 131 request) = **0 次 / 0.0%** 无 fallback 触发。
- nv_tier_attempts: pexec_success(131) + 瞬态 RemoteDisconnected(14)/Timeout(3)/empty_200(1), 全被 buffer 一次 attempt 吸收, 未穿透到 caller。
- buffer 日志: attempt=1 全 success_tool_call (elapsed 8.9s / 11.9s), NV-BUFFER-SUCCESS 一次 attempt flush — 瞬态错误未造成 retry。
- 主链当前首代模型 = dsv4f0731_nv, 无 tier 降级/无 key 疲劳。

## 验证
- docker exec logs_db psql: `SELECT caller,status FROM nv_requests WHERE created_at>now()-interval'30 min' AND status!=200` → 4 行全 caller=hermes, cc4101-primary 0 行。
- `SELECT status,count(*) ... caller='cc4101-primary'` → 130 行全 200 (130/130=100%)。
- `SELECT count(*),sum(fallback_triggered) FROM cc_requests WHERE created_at>now()-interval'30 min'` → 131/0 (0.0%)。
- nv_tier_attempts 瞬态 RemoteDisconnected/Timeout/empty_200 全被 buffer (attempt=1) 吸收, 未穿透到 caller。
- health: 40006/4101/40066 全 200; 容器 nv_gw Up 13h / cc4101 Up 12h / dsv4p_nv40066 Up 2d。

## 关键判断
cc2 主链路连续第 **124** 轮 (R893-R1016) 100% SR 干净, 主链专属错误 0 rows。
本轮 4 条 bad (502) 归属全属 hermes 越界宿主 (fid 52e1ddb6 泄漏路径) — 与主链 host 分离保持,
主链 130/130 全 200。fallback 0 次 (0.0%), 无新 cc2 主链错误类, 无持久 key 疲劳。
multi-key round-robin + func_health + buffer (attempt=1 全成功) 完全吸收瞬态错误,
未穿透到 caller, 已达稳态。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②本轮 bad 全属 hermes 越界, 主链无根因可查;
③参数处于稳态, 无参数可调。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 后续窗口继续确认 hermes 越界 bad (fid 52e1ddb6) 是否持续与主链隔离 (host 分离保持)。

## 容器健康
- nv_gw Up 13h, cc4101 Up 12h, dsv4p_nv40066 Up 2d; /health 40006/4101/40066 全 200。
- 配置快照: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, nv_gw nv_default_model=glm5_2_nv,
  NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_MAX_RETRIES=5, KeyManager 429 120s-600s 退避,
  ProbeWorker 15s, WaitQueue max 120s, nv_breaker mid-stream 软挂→OPEN。
  deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle。ms_gw fallback 保持不禁用。