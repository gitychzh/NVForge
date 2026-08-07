# R1028 cc2 NOP inspection round

- 日期: 2026-08-07
- 类型: NOP 巡检轮 (不改码, 只记数据)
- 判定: 主链 SR=100% + 专属错误 0 rows + fallback 0% → 无优化需求, 不改码

## 数据摘要 (live 复核 2026-08-07 17:0x + 注入轮前链 17:01 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **107/107 = 100% SR, 0 bad** (live `SELECT caller,status,count GROUP BY` → 全 200)。
- 主链专属错误 (caller=cc4101-primary, status!=200) = **0 rows** (scoped 错误分组为空)。
- 30min nv_requests 总 bad = **3 条 (全部 502), 全属 hermes** (越界宿主), 主链 0:
  - hermes|zombie_empty_completion|x1
  - hermes|stream_absolute_cap|x1
  - hermes|all_tiers_exhausted|x1
- 30min fallback (cc_requests) = **0/108 = 0.0%** (fallback_triggered=0)。
- 容器: nv_gw Up 14h, cc4101 Up 13h, dsv4p_nv40066 Up 2d; /health 40006/4101/40066 全 200。
- 主链首代 = dsv4f0731_nv (cc4101.PRIMARY_UPSTREAM_MODEL), 无 tier 降级/无 key 疲劳。

## 判定依据

| 指标 | 值 | 达标 |
|---|---|---|
| 主链 SR (nv_requests) | 107/107 = 100% | ✅ (≥99%) |
| 主链专属错误 | 0 rows | ✅ |
| nv_requests 总 bad | 3 条, 全属 hermes (越界) | ✅ (主链 0) |
| fallback 触发率 | 0.0% (0/108) | ✅ (<5%) |
| 容器健康 | nv_gw/cc4101/40066 全 Up, /health 200 | ✅ |

## 结论
cc2 主链路连续第 **136 轮** (R893-R1028) 100% SR 干净。本轮 3 条 bad (502) 归属全属 hermes 越界宿主
(经 caller 铁证 JOIN, 主链 host 分离完全干净)。fallback 0 次, 无新 cc2 主链错误类, 无持久 key 疲劳。
multi-key round-robin + func_health + buffer 完全吸收瞬态错误 (各 key 偶发 NVCFPexecRemoteDisconnected/
NVCFPexecTimeout/empty_200, attempt=1 大多成功未穿透 caller), 已达稳态。
**不改码**: ①主链 SR 100% + 专属错误 0 行无优化需求; ②本轮 bad 全属 hermes 越界, 主链无根因可查;
③参数处于稳态, 无参数可调。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 后续窗口继续确认 hermes 越界 bad (502) 是否持续与主链隔离 (caller JOIN)。