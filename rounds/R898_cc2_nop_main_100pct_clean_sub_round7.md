# R898 — cc2 NOP 巡检轮 (不改码)

- 日期: 2026-08-07 08:35 CST
- 判定: **NOP — cc2 主链路连续第 7 轮 100% 干净** (R892 139/139, R893 153/153, R894 143/143, R895 137/137, R896 134/134, R897 126/126, R898 125/125)
- 改动: **无**
- 依据: live DB now() ≈ 08:35 CST; 本 prompt 注入链路数据 + 实拉确认

## 数据摘要

| 指标 | 值 | 状态 |
|---|---|---|
| cc4101-primary (主 nv_gw:40006) 30min | **125/125 = 100% SR, 0 bad** | ✅ |
| nv_requests caller=cc4101-primary status!=200 | **0 条** (实拉) | ✅ |
| 30min 所有 bad (502 ×5) | 100% **hermes** (all_tiers_exhausted, avg 178.9s) | ⚠️ 越界 |
| 坏 fid 52e1ddb6 命中 | 26× (RemoteDisconnected/Timeout/504), JOIN 铁证 **100% hermes** | ⚠️ 40666 越界 |
| 主链 pexec fid | 全 5 key 健康 **281478d0** (cc2 0 命中 52e1ddb6) | ✅ |
| buffer (cc4101-primary) | 全 attempt=1/5 success_tool_call, 9-10s, 0 重试 | ✅ |
| 三容器 health | 4101/40006/40066 全 ok (200) | ✅ |
| fallback (cc2 线) | 0 次 | ✅ |

## 关键判据 (实拉 JOIN 铁证)

```
SELECT r.caller, left(t.function_id,8) AS fid, count(*) as n, sum(200 ok)
FROM nv_tier_attempts t JOIN nv_requests r ON r.request_id = t.request_id
WHERE t.created_at > now()-interval '30 min' AND tier='dsv4f0731_nv'
AND left(function_id,8)='52e1ddb6'
GROUP BY 1,2;
```
→ `hermes | 52e1ddb6 | 26 | 0` — **坏 fid 100% 归属 hermes 线**, cc2 主链 0 命中。

per-key 分布: k0=281478d0×24, k1=×26, k2=×26, k3=×25, k4=×24 (健康 fid); 各 key 另有 5-6 条 52e1ddb6 全为 hermes。

## 结论 + 下一步
- cc2 主链路连续 7 轮 100% SR, 无新错误类。不改码 (铁律: 只改 40006+40066; 坏 fid hermes 线越界非 cc2 范围)。
- buffer 全 attempt=1/5 成交, 0 重试, 说明主链稳定无背压。
- 下一步: 持续监控主链 fid=281478d0 + fallback 触发率 (目标 <5%, 当前 0)。

## 参数快照
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_HEADER_TIMEOUT=400, CC4101_STREAM_TOTAL_DEADLINE_S=470, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms