# R1087 cc2 NOP — primary 103/103=100% SR 全 clean 零坏 (连续第6轮); hermes 0 bad; fallback 0.0%; buffer 无重试; per-key 全 pexec_success 仅 k3 1x transient RD 补回

日期: 2026-08-07 21:13 CST

## 结论
**NOP 巡检轮, 不改码。** 主链 cc4101-primary (nv_gw:40006) 30min = **103/103 = 100% SR, 零 bad**,
连续第 6 轮全 clean (R1081 105/106 → R1082 107/108 → R1083 115/115 → R1084 103/103 → R1085 100/100 → R1086 100/100 → R1087 103/103)。
无新错误, 无 fallback, 无配置漂移。buffer 全程 attempt-1 直flush 零重试零抖动。

## 依据 (轮前注入 21:12:33 + DB 复核 21:13 + /health 复核 2026-08-07)

- **主链 cc4101-primary = 103/103 = 100% SR, 0 bad**。`SELECT status,count(*) FROM nv_requests
  WHERE created_at>now()-interval '30 min' AND caller='cc4101-primary'` → 全 200, 0 非 200。
- **30min 错误分类 (nv_requests status!=200)**: 空 → 无任何错误。
- **per-caller 归属**: dsv4f0731_nv 总 145 请求全 200 (SR=100.0%), hermes 亦零坏 (上轮 2 bad 已消, 无堆积)。
- **per-key 健康**: nv_tier_attempts(`created_at` 列) 全 5 key 高 pexec_success (k0 21/k1 20/k2 21/k3 21/k4 20);
  仅 k3 1 次 transient NVCFPexecRemoteDisconnected (21/22 补回), 无冷却堆积, 无单 key 连续失败。
- **buffer 日志**: 复窗口无 BUFFER-EXHAUSTED/WAIT-/KEYMANAGER 堆积日志, 全部 attempt-1 success 直接 flush, 零重试。
- **30min fallback 0/145 = 0.0%**, 全走主链。
- **/health 实测**: 40006 nv_gw 200 (passthrough, 5 key), 4101 cc4101 200 (primary dsv4f0731_nv)。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **103/103 = 100% SR, 0 bad** | ✅ 连续第 6 轮全 clean |
| 30min 错误分类 | 空 (无任何错误) | ✅ |
| per-caller 归属 | 主链 0 bad; hermes 0 bad | ✅ |
| per-key 健康 | 5 key 全 pexec_success (20-21/k); k3 1 次 transient RD 补回 | ✅ |
| 30min fallback | 0/145 = 0.0% | ✅ |
| buffer | 全部 attempt-1 直flush; 无重试/EXHAUSTED/WAIT | ✅ |
| 容器 /health | 40006/4101 全 200 | ✅ |

## 下一步
- 保持 NOP 观察。主链连续 6 轮全 clean, buffer 零重试零抖动, 退避/重试机制连续多轮证稳。
- 仅当主链出现**持续分布**错误 (多 key 连续多轮非 pexec_success) 或单 key 100% 失败堆积才介入
  (查 egress IP / mihomo 7900-7904 / KEY_FID_BIND), 当前无需动作。