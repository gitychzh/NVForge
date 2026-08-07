# R899 — cc2 NOP 巡检轮 (不改码)

- 日期: 2026-08-07 (北京时间约 08:45 CST)
- 判定: **NOP — cc2 主链路连续第 8 轮 100% 干净** (R892 139/139, R893 153/153, R894 143/143, R895 137/137, R896 134/134, R897 126/126, R898 125/125, R899 124/124)
- 改动: **无**
- 依据: 本 prompt 注入链路数据 + live DB 实拉确认

## 数据摘要

| 指标 | 值 | 状态 |
|---|---|---|
| cc4101-primary (主 nv_gw:40006) 30min | **124/124 = 100% SR, 0 bad** (实拉) | ✅ |
| nv_requests caller=cc4101-primary status!=200 | **0 条** (实拉) | ✅ |
| prompt 注入 caller×model×status | cc4101-primary\|dsv4f0731_nv\|200\|121 (0 bad) | ✅ |
| 30min 所有 bad (all_tiers_exhausted ×6, avg 179.2s) | 100% **hermes** caller (502), 非 cc2 线 | ⚠️ 越界 |
| dsv4f0731_nv 整体 SR | 95.3% (121/127, 6 bad 全 hermes) | ✅ |
| 三容器 health | 4101/40006/40066 全 ok (200) | ✅ |
| fallback (cc2 线) | 0 次 | ✅ |
| buffer/wait/keymanager 日志 | 无 buffer/wait 异常日志 (buffer 全 attempt=1/5 成交) | ✅ |

## 关键判据 (实拉)

```
SELECT status, count(*) FROM nv_requests
WHERE ts > now()-interval '30 min' AND caller='cc4101-primary' GROUP BY 1;
→ 200 | 124

SELECT count(*) FROM nv_requests
WHERE ts > now()-interval '30 min' AND caller='cc4101-primary' AND status!=200;
→ 0
```

- cc4101-primary (主 nv_gw:40006) live DB = **124/124 = 100% SR, 0 bad**。
- prompt 注入 `all_tiers_exhausted ×6 (avg 179.2s)` 全在 `hermes|dsv4f0731_nv|502` 线, **非 cc2 范围**。
- nv_gw 容器 Up 5 hours, health passthrough 5key, model 列表含 dsv4f0731_nv。

## 结论 + 下一步
- cc2 主链路连续 8 轮 (R892→R899) 100% SR, 无新错误类, 不改码 (铁律: 只改 40006/40066)。
- 6 条 all_tiers_exhausted 全属 hermes 线活动, 越 cc2 范围; 40066 泄漏坏 fid 持续 host 分离, cc2 主链不受污染。
- 下一步: 持续监控主链 dsv4f0731 rotation fid + fallback 触发率 (目标 <5%, 当前 0)。

## 参数快照 (env, 本轮未改)
- nv_gw(40006): NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_FORCE_STREAM_UPGRADE=0,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_MAX_RETRIES=5 (90×5=450s)
- cc4101(4101): PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms
  (铁律4 不主动改 fallback)
- config.py: dsv4f0731_nv function_ids=[281478d0-...] (主链 R-fid0731); dsv4f_nv function_ids=[52e1ddb6-...]
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle