# R894 — cc2 自优化 nv_gw 链路 (HM2) — NOP 巡检轮

> 日期: 2026-08-07 (live DB now()≈08:12 CST ≈ 00:12 UTC)
> 结论: **不改码。cc2 主链路连续第 3 轮 (R892 139/139, R893 153/153, R894 143/143) 100% SR 干净。**
> 所有坏请求仍由 hermes 线的独立容器 **dsvf0731_nv40666** (host opc2sname-dsv4f40666) 产出的
> 兄弟坏 fid **52e1ddb6** 引起, 与 cc2 主 nv_gw(40006) 候选池 host 分离, 互不影响。

## 本轮改动

**无 (NOP)。** cc2 主链路 100% 干净, 无新错误类, 无需改码。不改动任何 40006/40066 配置。

## 依据 (live DB 实拉, 30min 窗口)

### 1. cc4101-primary (主 nv_gw:40006, host opc2sname) = **143/143 全 200, 0 bad (100% SR)**

```sql
select caller, mapped_model, count(*) total,
       sum(case when status=200 then 1 else 0 end) ok
from nv_requests where created_at > now()-interval '30 min' and caller='cc4101-primary'
group by 1,2;
-- cc4101-primary | dsv4f0731_nv | 143 | 143
```

- 30min cc4101-primary 坏请求实拉 = **0 条** (WHERE status!=200 AND caller='cc4101-primary' → 空)。

### 2. 30min 所有 bad 全属 hermes 线, 全带坏 fid 52e1ddb6

```sql
select caller, mapped_model, status, error_type, left(function_id,8) fid
from nv_requests where created_at > now()-interval '30 min' and status!=200;
-- hermes|dsv4f0731_nv|502|all_tiers_exhausted|52e1ddb6   ×5
-- hermes|dsv4f0731_nv|502|stream_absolute_cap|52e1ddb6   ×1
```

- 6 条坏请求 caller 全 = `hermes`, fid 全 = `52e1ddb6` (兄弟坏 fid, R891 定位的独立容器 dsvf0731_nv40666)。
- **cc4101-primary 0×52e1ddb6。**

### 3. 主 nv_gw pexec 全程健康 fid 281478d0

```sql
select left(function_id,8) fid, count(*) from nv_tier_attempts
where created_at > now()-interval '30 min' and error_type in ('','pexec_success')
group by 1;
-- 281478d0 | 135   (成功 attempt 全部命中健康 fid)
select nv_key_idx, left(function_id,8) fid, error_type, count(*) from nv_tier_attempts
where created_at > now()-interval '30 min' and error_type not in ('','pexec_success')
group by 1,2,3 order by 1;
-- 全 5 key 失败全带 52e1ddb6 (RemoteDisconnected/529/Timeout/empty_200), 主 nv_gw 0×52e1ddb6
```

- nv_gw 实时日志 `[NV-GLM52-ATTEMPT] ... fid=281478d0` 全程干净, 0×52e1ddb6。

### 4. buffer (cc4101-primary) 全程 attempt=1/5 一次成交

```
[NV-BUFFER-ATTEMPT] attempt=1/5 ... caller=cc4101-primary
[NV-BUFFER-VERDICT] attempt=1 verdict=success_tool_call ... done=True closed=False buffered=2~11KB elapsed=5~16s
[NV-BUFFER-FLUSH] flushing ... verdict=success_tool_call
[NV-BUFFER-SUCCESS] flushed ... after 1 attempt(s)
```

- 全 attempt=1 即 success_tool_call, 5-16s, 0 cooldown/429/exhaustion/wait。

### 5. 四 scoped 容器 health

- curl 4101 (cc4101, primary=dsv4f0731_nv) / 40006 (nv_gw, 5 keys) / 40066 / 40666 → 全 ok。

## 本轮数据表

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **143/143 = 100% SR, 0 bad** | ✅ |
| 主 nv_gw pexec fid | 135/135 success 全 281478d0, 0×52e1ddb6 | ✅ |
| buffer (cc4101-primary) | 全 attempt=1/5 success_tool_call, 5-16s, 0 重试 | ✅ |
| hermes 线 bad (40666, 52e1ddb6) | all_tiers_exhausted ×5 + stream_absolute_cap ×1 = 502 | ⚠️ 越界容器 |
| 四 scoped health | 4101/40006/40066/40666 全 ok | ✅ |
| fallback (cc2 线) | 0 次 | ✅ |
| host_machine | 主=opc2sname, 40666=opc2sname-dsv4f40666 | host 分离 |

## 验证

- 实拉 SELECT 确认 cc4101-primary 143/143 (0 bad), 所有 bad 归 hermes+52e1ddb6。
- nv_gw buffer 日志全 attempt-1 success_tool_call, 无 cooldown/retry。
- curl 四容器 health 全 ok。

## 关键判断

cc2 主链路连续第 3 轮 (R892 139/139 → R893 153/153 → R894 143/143) 100% SR 干净。
所有坏请求仍由 hermes 线的 dsvf0731_nv40666 (坏 fid 52e1ddb6) 产生, 与 cc2 主链 host 分离,
不改码 (40666 不在 cc2 改动范围/铁律 4; 对 cc2 SR 无影响)。

## 下一步

1. 持续监控主链 fid 仍为 281478d0, SR 维持 100%。
2. 40666 (hermes 线恒卡 52e1ddb6) 修复归属待确认后单独评估 — 不在本轮范围。
3. 下轮默认仍 NOP, 除非主链出现新错误类或 SR 下滑。

## 参数快照 (nv_gw + cc4101, 未变)

- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0(bind fid0),
  buffer 5×90s, total_deadline=450s, KeyManager 429→120-600s, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=180.
- cc4101: primary=dsv4f0731_nv@nv_gw:40006, FALLBACK_UPSTREAM_URL=ms_gw:40007 (实测极少触发),
  STREAM_TOTAL_DEADLINE=470s, PRIMARY_HEADER_TIMEOUT=400s, UPSTREAM_TIMEOUT=130s.
- settings.json: contextWindow=170000, autoCompactWindow=155000, API_TIMEOUT_MS=600000.