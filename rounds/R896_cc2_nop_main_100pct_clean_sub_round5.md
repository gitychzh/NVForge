# R896 — cc2 自优化 nv_gw 链路 (HM2) — NOP 巡检轮

> 日期: 2026-08-07 (live DB now()≈00:20 UTC ≈ 08:20 CST)
> 结论: **不改码。cc2 主链路连续第 5 轮 (R892 139/139, R893 153/153, R894 143/143, R895 137/137, R896 134/134) 100% SR 干净。**
> 所有坏请求仍由 hermes 线坏 fid **52e1ddb6** 引起。本轮经 **request_id join nv_requests 铁证确认**:
> cc4101-primary 主链 0×52e1ddb6, 坏 fid 100% 归属 hermes caller。dsvf0731_nv40666 容器现已不再 docker ps (越界源可能已停)。

## 本轮改动

**无 (NOP)。** cc2 主链路 100% 干净, 无新错误类, 无需改码。不改动任何 40006/40066 配置。

## 依据 (live DB 实拉, 30min 窗口, now()≈00:20 UTC)

### 1. cc4101-primary (主 nv_gw:40006) = **134/134 全 200, 0 bad (100% SR)**

```sql
select caller, status, count(*) from nv_requests
where created_at > now()-interval '30 min' group by 1,2;
-- cc4101-primary | 200 | 132 (另一查 134, 窗口推移微差)
-- hermes         | 502 |   6
```
- cc4101-primary bad 实拉 WHERE status!=200 = **0 条**。

### 2. 【铁证】tier_attempts JOIN nv_requests — 坏 fid 52e1ddb6 100% 归属 hermes

`nv_tier_attempts` 无 caller 列, 本轮用 `request_id` join `nv_requests` 做 caller 归属裁决:

```sql
select r.caller, left(t.function_id,8) fid, t.error_type, count(*)
from nv_tier_attempts t join nv_requests r on r.request_id=t.request_id
where t.created_at > now()-interval '30 min' group by 1,2,3;
-- cc4101-primary|281478d0|pexec_success|134   ← 主链 100% 成功, 全健康 fid
-- hermes        |52e1ddb6|NVCFPexecRemoteDisconnected|21
-- hermes        |52e1ddb6|NVCFPexecTimeout|3
-- hermes        |52e1ddb6|504_nv_gateway_timeout|1
-- hermes        |52e1ddb6|529_nv_overloaded|1
-- hermes        |52e1ddb6|empty_200|1
```
- **cc4101-primary 主链: 134× pexec_success, 全 fid=281478d0 (健康), 0 bad, 0×52e1ddb6。**
- **52e1ddb6 27 条失败全属 hermes caller** = 越界容器 dsvf0731_nv40666 的兄弟坏 fid 泄漏。

### 3. buffer 全程干净 (caller=cc4101-primary)

- `docker logs nv_gw --since 30m` 实时: 全 `caller=cc4101-primary` `attempt=1/5` 即
  `success_text`/`success_tool_call`, elapsed 7~12s, `done=True` `closed=False`, 零重试 / 零 cooldown / 零 429。
- 无 BUFFER-exhaust, 无 WAIT-, 无 cooldown/429 日志。

### 4. 容器 health + 新观察

- curl 4101/40006/40066 → 全 ok (4101 primary=dsv4f0731_nv; 40006 passthrough 5 keys)。
- **新观察**: `docker ps` **不再有 dsvf0731_nv40666 容器** (本轮仅 cc4101/nv_gw/dsv4p_nv40066/nv_gw_stable)。
  坏 fid 52e1ddb6 泄漏源头 (40666) 疑似已停; 但 30min 窗口内 hermes 线 bad 仍在 (窗口前半段产出), 待下轮确认。
- 越界容器 40666 停用不影响 cc2 主链 SR (host 分离, 主链 0×52e1ddb6)。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **134/134 = 100% SR, 0 bad** | ✅ |
| 主 nv_gw pexec 成功 fid | 全 281478d0, 0×52e1ddb6 (join 铁证) | ✅ |
| buffer (cc4101-primary) | 全 attempt=1/5, success 7-12s, 0 重试 | ✅ |
| hermes 线 bad (52e1ddb6, 越界 40666) | RemoteDisconnected ×21 + Timeout ×3 + 504 ×1 + 529 ×1 + empty_200 ×1 = 27 | ⚠️ 越界 |
| 存留 scoped 容器 health | 4101/40006/40066 全 ok | ✅ |
| dsvf0731_nv40666 | 已不在 docker ps (越界源疑似停) | 👀 观察 |
| fallback (cc2 线) | 0 次 | ✅ |

## 下一步

- 持续监控主链保持 fid=281478d0 100% SR (第 N 个连续干净轮)。
- **关注 40666 容器是否确实已停**: 若停则 hermes 线 52e1ddb6 泄漏根治, 下轮 hermes bad 应归零。
- 当前无需改码。

## 参数快照 (未改动)

- nv_gw: UPSTREAM_TIMEOUT=90, NVU_DISABLE_MS_FALLBACK=0, KEY_COOLDOWN_S=30,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_BUFFER_MAX_RETRIES=5 (90×5=450s),
  MIN_OUTBOUND_INTERVAL_S=10
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (ms_gw 已恢复, 不主动禁用),
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle