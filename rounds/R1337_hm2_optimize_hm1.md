# HM2 Optimize HM1 — Round R1337

> **Trigger**: double-dispatch (false trigger, `这是我提交的, 不触发`). R1336 already committed + symlink correct.
>
> **铁律**: 只改HM1不改HM2

## 1. 触发分析

- cron 输出: `这是我提交的, 不触发` (false trigger)
- 最新 commit: acda632 R1336 (opc2_uname, HM2自己提交)
- HM1 git log: 停留在 R1206 (131 rounds behind)
- 判定: 双倍派遣 — R1336 已提交且 symlink 正确, cron 仍派遣

## 2. HM1 数据收集 (改前必有数据)

### 容器状态
- nv_gw 重启时间: 2026-07-14 07:23:23 UTC
- 重启后请求: 仅 4 条 (docker logs 含 4 次 NV-REQ)
- 重启后 DB: 4 条记录

### 6h 窗口 (02:00–08:00 UTC)
- 总体: 81req / 67 OK = **82.7% SR**
- dsv4p_nv: 54req / 48 OK (88.9% SR), avg 26,577ms
- glm5_2_nv: 27req / 19 OK (70.4% SR), avg 11,875ms

### 错误细分
| 错误类型 | 数量 | 模型 | 平均延迟 | 备注 |
|---|---|---|---|---|
| zombie_empty_completion | 8 | glm5_2_nv | 9,114ms | 代码级 zombie 检测, 非配置可修 |
| all_tiers_exhausted | 6 | dsv4p_nv | 71,694ms | ⚠️ 全部在重启前 (05:57–06:37 UTC) |

### 重启后数据 (07:23+)
- 仅 4 条请求，全部 glm5_2_nv integrate: 3 OK + 1 zombie
- dsv4p_nv 重启后: **0 请��** — 无法评估 BUDGET=82 效果

### 上游
- nvcf_pexec: 48/48 **100% SR** (dsv4p_nv)
- nv_integrate: 19/27 70.4% SR (glm5_2_nv)
- (空): 6 ATE (全部重启前)

### 容灾
- fallback: 0 次
- ms_gw: 6req / 5 OK
- tier_attempts: 0 条
- 0 NV-TIER-FAIL, 0 NV-EMPTY-FASTBREAK, 0 NV-MS-FB

### 配置
- compose md5: `4c3e804d68a158d76937dfae32764edf` (与 R1336 一致)
- NVU_TIER_BUDGET_DSV4P_NV=82
- All params floor/optimal

## 3. 决策: NOP

| 信号 | 判定 | 理由 |
|---|---|---|
| 6 dsv4p_nv ATE | 零可修故障 | 全部在容器重启前 (05:57–06:37 UTC), 重启后 0 dsv4p 请求 |
| 8 zombie_empty_completion | 非配置可修 | 代码级 zombie 检测 (NVCF content-filter stop+12chars, 180K input), 网关正确处理 |
| dsv4p_nv pexec | 100% SR | 48/48, 健康 |
| 0 fallback / 0 tier_attempts | 正常 | 无 tier 重试, 无 ms_gw 回退触发 |
| Post-restart 仅 4 req | 数据不足 | 无法评估 R1334 BUDGET=82 效果 |
| compose md5 不变 | 配置稳定 | 无新变更 |

**结论**: 零参数变更, 零容器重启. 等待 HM1 提交新 commit 触发真正的优化回合.

## 4. NOP 验证

- ✅ 铁律: 只改HM1不改HM2 (本轮未改任何配置)
- ✅ 改前必有数据: DB + logs 已收集
- ✅ 6 dsv4p_nv ATE 全部在重启前, 重启后 0 dsv4p 请求 — 零可修故障
- ✅ 8 zombie = code-level zombie detection — 非配置可修
- ✅ dsv4p_nv pexec 100% SR (48/48)
- ✅ 0 fallback, 0 tier_attempts

## ⏳ 轮到HM1优化HM2
