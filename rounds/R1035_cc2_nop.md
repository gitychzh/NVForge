# R1035 cc2 NOP — cc2 primary 100% clean (119/119), scoped errors 0 rows; bad 2 hermes (502); fallback 0 (0/119)

- Round: **R1035** (2026-08-07)
- Type: **NOP 巡检轮, 不改码**
- Containers: nv_gw Up 14h, cc4101 Up 14h, dsv4p_nv40066 Up 2d

## 数据(注入轮前链路分析 + live 复核)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **119/119 = 100% SR, 0 bad** (live 查询) | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | ✅ |
| dsv4f0731_nv 全 caller SR | 98.9% (182/184) | ✅ (2 bad 属 hermes) |
| nv_requests 总 bad (非 200) | 2 条 (502), caller 全 = **hermes**, 主链 0 | ✅(主链) |
| cc_requests fallback | 0 次 / 0.0% (119 request) | ✅ |
| nv_tier_attempts 非成功(30min) | RemoteDisconnected x4 / Timeout x1 / empty_200 x1 (全被吸收, 未穿透) | ✅ |
| 容器 health | 40006/4101/40066 全 200; nv_gw Up 14h, cc4101 Up 14h, dsv4p Up 2d | ✅ |

## 30min per-status (caller x status)
```
cc4101-primary|dsv4f0731_nv|200|119
hermes|dsv4f0731_nv|200|63
hermes|dsv4f0731_nv|502|2
```

注意: 本轮 window 主链 119 条 (比 R1034 的 113 略多, 滚动窗口自然推进) — 主链全 200 仍 100%。

## 30min nv_tier_attempts per-key 错误分布
```
0|pexec_success|24
1|empty_200|1
1|pexec_success|21
2|NVCFPexecRemoteDisconnected|2
2|pexec_success|27
3|NVCFPexecRemoteDisconnected|1
3|pexec_success|24
4|NVCFPexecRemoteDisconnected|1
4|NVCFPexecTimeout|1
4|pexec_success|23
```
多 key round-robin 分散瞬态错误 (各 key 偶发 RDisconn/Timeout/empty_200), buffer attempt=1 即成功, 未穿透 caller。

## buffer 证据 (docker logs nv_gw)
- 主链请求全 `[NV-BUFFER-VERDICT] attempt=1 verdict=success_text|success_tool_call` → 1 attempt 成功 flush。
- 无重试/无 WAIT- (WaitQueue)/无 buffer 耗尽。

## 判断
- cc2 primary 119/119 全 200, scoped 主链专属错误 0 rows, 连续第 **143** 轮 (R893-R1035) NOP 稳态。
- 本轮 2 条 bad (502) 经 caller 铁证归属 **hermes** 越界宿主, 与主链 host 分离完全干净 (主链 0 bad)。
- fallback 0 次, 无新 cc2 主链错误类, 无持久 key 疲劳。
- multi-key round-robin + func_health + buffer (attempt=1 大多成功) 完全吸收瞬态错误, 未穿透 caller。
- **不改码**: ①主链 SR 100% + 专属错误 0, 无优化需求; ②本轮 bad 全属 hermes 越界, 主链无可查根因; ③参数稳态, 无可调项。

## 改动
无 (NOP)

## 验证
- live psql: `SELECT caller,status,count(*) FROM nv_requests WHERE created_at>now()-interval '30 min' AND caller='cc4101-primary'` → 119 行全 200。
- `... WHERE status!=200 GROUP BY 1,2` → 唯一 bad 2 条 502 caller 全 = hermes, 主链专属错误 0 rows。
- `SELECT count(*),sum(case when fallback_triggered...) FROM cc_requests` → 119/0 (0.0%)。
- docker logs nv_gw --since 30m grep BUFFER- → 全 attempt=1 success flush, 无重试。
- health: 40006/4101/40066 全 200; nv_gw/cc4101 Up 14h, dsv4p_nv40066 Up 2d。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 后续窗口继续确认 hermes 越界 bad (502) 是否持续与主链隔离 (caller JOIN)。