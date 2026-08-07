# R1083 cc2 NOP — 主链 115/115 = 100% SR, 全 clean 零坏; hermes 2 bad out-of-scope; fallback 0

> 日期: 2026-08-07 20:53 CST | 轮: R1083 | 决策: NOP 巡检轮 (不改码)

## 判决依据 (轮前注入 20:52 CST 分析 + 本轮 DB 复核 + 容器 /health)

- **30min 主链 cc4101-primary = 115/115 = 100% SR, 零 bad**：
  DB 复核 `SELECT status,count(*) FROM nv_requests WHERE caller='cc4101-primary' AND created_at>now()-30min`
  → **全 200, 0 非 200**。本轮比 R1082 (107/108 含 1 transient) 更干净, 连续第 2 轮全 clean 无任何主链坏。
- **per-caller 归属复核 (铁证)**：dsv4f0731_nv 总 151/153=98.7% 的 2 bad (502×2) + 错误分类表
  NVStream_IncompleteRead×1 + zombie_empty_completion×1 (avg_dur 36-38s) **全部归属 hermes** (out-of-scope),
  cc4101-primary 无一个坏。
- **per-key 健康**：nv_tier_attempts 全 5 key 均高 pexec_success (20-25/key), 仅 k3 有一次
  NVCFPexecRemoteDisconnected (transient, 仍 23/23 success 补回), KeyManager 正常, 无冷却堆积。
- **30min fallback**: 0 次 (0.0%), 全走主链。
- **容器 /health 复核**: 40006 nv_gw 200, 4101 cc4101 200; docker ps 实测 nv_gw Up 17h, cc4101 Up 17h。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **115/115 = 100% SR, 0 bad** | ✅ 全 clean |
| per-caller 归属 | 主链 0 bad; hermes 2 bad (502/IncompleteRead/zombie) 均 out-of-scope | ✅ |
| per-key 健康 | 5 key 全 pexec_success; k3 单次 transient RD 已补回 | ✅ |
| 30min fallback | 0 次 (0.0%) | ✅ |
| 容器 /health | 40006/4101 全 200; nv_gw Up 17h, cc4101 Up 17h | ✅ |

## 行动
- 无改动 (NOP)。主链 115/115 = 100% 全 clean, 无新错误, 无 fallback, 无配置漂移, 无参数可调。

## 下一步
- 保持 NOP 观察。本轮主链零坏, 且外层 hermes 的 2 bad (IncompleteRead/zombie) 为独立 caller 问题, 不属主链。
- 维持改前有数据 / 改后必验证铁律; 仅当主链出现**持续分布**错误或单 key 连续多轮 100% 失败才介入调整
  (换 KEY_FID_BIND / 查 egress IP / mihomo 代理线路 7900-7904), 当前无需动作。