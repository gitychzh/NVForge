# R895 — cc2 自优化 nv_gw 链路 (HM2) — NOP 巡检轮

> 日期: 2026-08-07 (live DB now()≈08:16 CST ≈ 00:16 UTC)
> 结论: **不改码。cc2 主链路连续第 4 轮 (R892 139/139, R893 153/153, R894 143/143, R895 137/137) 100% SR 干净。**
> 所有坏请求仍由 hermes 线的独立容器 **dsvf0731_nv40666** (host opc2sname-dsv4f40666) 产出的
> 兄弟坏 fid **52e1ddb6** 引起, 与 cc2 主 nv_gw(40006) 候选池 host 分离, 互不影响。

## 本轮改动

**无 (NOP)。** cc2 主链路 100% 干净, 无新错误类, 无需改码。不改动任何 40006/40066 配置。

## 依据 (live DB 实拉, 30min 窗口, now()≈00:16 UTC)

### 1. cc4101-primary (主 nv_gw:40006, host opc2sname) = **137/137 全 200, 0 bad (100% SR)**

```sql
select caller, status, count(*) from nv_requests
where created_at > now()-interval '30 min' group by 1,2;
-- cc4101-primary | 200 | 137
-- hermes         | 200 |   1
-- hermes         | 502 |   6
```

- 30min cc4101-primary 坏请求实拉 = **0 条** (WHERE status!=200 AND caller='cc4101-primary' → 空)。

### 2. 30min 所有 bad 全属 hermes 线, 全带坏 fid 52e1ddb6

```sql
select caller, error_type, left(function_id,8) fid, count(*)
from nv_requests where created_at > now()-interval '30 min' and status!=200
group by 1,2,3;
-- hermes|all_tiers_exhausted|52e1ddb6|5
-- hermes|stream_absolute_cap|52e1ddb6|1
```

- 6 条坏请求 caller 全 = `hermes`, fid 全 = `52e1ddb6` (兄弟坏 fid, R891 定位的独立容器 dsvf0731_nv40666)。
- **cc4101-primary 0×52e1ddb6。**

### 3. 主 nv_gw pexec 全程健康 fid 281478d0; 52e1ddb6 仅从 hermes 线轮转点渗入

```sql
select nv_key_idx, left(function_id,8) fid, count(*)
from nv_tier_attempts where created_at > now()-interval '30 min'
group by 1,2 order by 1;
-- 各 key: 281478d0 25~29 (成功), 52e1ddb6 4~6 (失败)
```

- 成功后缀全带 fid=**281478d0** (健康); 失败全带 **52e1ddb6** = 老问题 (hermes 线 40666 泄漏),
  主 nv_gw(40006) 候选池未掺入坏 fid。

### 4. buffer 全程干净 (caller=cc4101-primary)

- `docker logs nv_gw --since 30m` 实时: 全 `caller=cc4101-primary` `attempt=1/5` 即
  `success_text`/`success_tool_call`, elapsed 1~12s, `done=True` `closed=False`, **零重试 / 零 cooldown / 零 429**。
- 无 BUFFER-exhaust, 无 WAIT-, 无 cooldown/429 日志。

### 5. 容器 health

- `curl localhost:4101/health` → ok (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok (dsv4p_nv40066)

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **137/137 = 100% SR, 0 bad** | ✅ |
| 主 nv_gw pexec hop 成功 fid | 全 281478d0 (健康), 0×52e1ddb6 | ✅ |
| buffer (cc4101-primary) | 全 attempt=1/5, success 1-12s, 0 重试 | ✅ |
| hermes 线 bad (40666, 52e1ddb6) | all_tiers_exhausted ×5 + stream_absolute_cap ×1 = 502 | ⚠️ 越界容器 |
| 三 scoped 容器 health | 4101/40006/40066 全 ok | ✅ |
| fallback (cc2 线) | 0 次 | ✅ |
| host_machine | 主=opc2sname, 40666=opc2sname-dsv4f40666 | 分离 |

## 下一步

- 持续监控主链保持 fid=281478d0 100% SR。
- hermes 线 52e1ddb6 泄漏 (dsvf0731_nv40666) 越 cc2 范围, 归属确认后单独评估 (R891 根因待修复)。
- 当前无需改码。

## 参数快照 (自注入轮前分析, 未改动)

- nv_gw: UPSTREAM_TIMEOUT=90, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  NVU_BUFFER_MAX_RETRIES=5 (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, TIER_TIMEOUT_BUDGET_S=180,
  buffer callers=cc4101-primary,openclaw2; 5 KeyManager (429→120s-600s 退避, R5s 短惩罚)
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (ms_gw 已恢复, 不主动禁用),
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle