# R1033 cc2 NOP — cc2 primary 100% clean (115/115), scoped errors 0 rows; bad 1 hermes (502 all_tiers_exhausted); fallback 0 (0/175)

- Round: **R1033** (2026-08-07)
- Type: **NOP 巡检轮, 不改码**
- Containers: nv_gw Up 14h, cc4101 Up 13h, dsv4p_nv40066 Up 2d

## 数据(注入轮前链路分析 + live 复核)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **115/115 = 100% SR, 0 bad** | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | ✅ |
| dsv4f0731_nv 全 caller SR | 99.4% (174/175) | ✅ (1 bad 属 hermes) |
| nv_requests 总 bad (非 200) | 1 条 (502 all_tiers_exhausted), caller=hermes, 主链 0 | ✅(主链) |
| cc_requests fallback | 0 次 / 0.0% (175 request) | ✅ |
| nv_tier_attempts 非成功 | RemoteDisconnected x4 / Timeout x1 / empty_200 x1 (全被吸收, 未穿透) | ✅ |
| 容器 health | 40006/4101/40066 全 200; nv_gw Up 14h, cc4101 Up 13h, dsv4p Up 2d | ✅ |

## 30min per-status (caller x status)
```
hermes|dsv4f0731_nv|200|59
hermes|dsv4f0731_nv|502|1
cc4101-primary|dsv4f0731_nv|200|115
```

## 判断
- cc2 primary 115/115 全 200, scoped 主链专属错误 0 rows, 连续 NOP 稳态。
- 本轮唯一 bad (502, all_tiers_exhausted) 经 caller 铁证归属 **hermes** 越界宿主, 与主链 host 分离完全干净。
- fallback 0 次, 无新 cc2 主链错误类, 无持久 key 疲劳。
- multi-key round-robin + func_health + buffer 完全吸收瞬态错误, 未穿透 caller。
- **不改码**: 主链 100% + 专属错误 0, 无优化需求; bad 全属 hermes, 主链无可查根因; 参数稳态。

## 改动
无 (NOP)

## 验证
- live psql: `SELECT caller,status,count(*) FROM nv_requests WHERE status!=200 ... GROUP BY 1,2` → 唯一 bad 502 caller=hermes。
- cc4101-primary 30min 全 200 (115 行), scoped 错误 0 rows。
- fallback 0/175 (0.0%)。
- health: 40006/4101/40066 全 200; 容器 Up nv_gw 14h / cc4101 13h / dsv4p 2d。

## 下一步
- 保持 NOP 观察; 继续确认 hermes 越界 bad 是否持续与主链隔离 (caller JOIN)。

此轮 NOP 结束, commit + push。