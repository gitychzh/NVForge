# R802: HM2 链路验证 NOP — R797-R801 已通, agent 全落 ms_gw SR 100%

> 承接 R801 (dsv4p budget 70). 8 轮定时优化第 6 轮.
> 铁律: 改前有数据 (无新问题), 改后有验证 (端到端 + ms_requests DB).
> 角色: HM2-only. 决策: NOP — 零改动, 零重启.

## 改前数据 (R801 后, 10-20min 窗口)

### nv_requests (NV tier, 最近 10min)

| tier_model | status | count | avg_ms |
|---|---|---|---|
| dsv4p_nv | 502 | 1 | 70014 | ← R801 70s fail |
| glm5_2_nv | 502 | 3 | 741 | ← R797 0.77s fail (NVCF DEGRADED) |

NVCF 74f02205 (dsv4p) + 3b9748d8 (glm5_2) 持续坏, 两个 NV tier SR=0%. 但都已快速失败.

### ms_requests (fallback 目标, 最近 20min) — ★关键★

| backend_model | status | count | avg_ms |
|---|---|---|---|
| ZHIPUAi/GLm-5.2 | ok | 2 | 5774 |
| deepseek-ai/DeepSeek-V4-pro (各 variant) | ok | 16 | 13822-18226 |

**ms_gw 18/18 status=ok** — agent 全部成功落 ms_gw 兜底, 端到端 SR 100% (经 ms_gw).

### 端到端验证 (opclaw4103)

```
$ curl opclaw4103:4103 glm5_2_nv "1+1"
HTTP 200 13.959s, model: glm5_2_ms   ← primary 0.77s 502 → adapter fallback ms_gw → 200
```
✓ adapter 层 fallback 生效 (FALLBACK_ENABLED=1, ms_gw).

### 5 adapter fallback 配置审计

| adapter | primary | fallback_model | FALLBACK_ENABLED | 状态 |
|---|---|---|---|---|
| cc4101 | glm5_2_nv | dsv4p_ms | (默认) | ✓ 配置完整 |
| cx4102 | glm5_2_nv | glm5_2_ms | (默认) | ✓ FALLBACK_TIMEOUT=300 (长, 但 glm5 0.77s 不影响) |
| opclaw4103 | glm5_2_nv | glm5_2_ms | 1 | ✓ 验证 200 |
| hm4104 | dsv4p_nv | dsv4p_ms | 1 | ✓ 配置完整 |
| oc4105 | kimi_nv | glm5_2_ms | **0** | ⚠ fallback 关闭 (见下) |

### kimi_nv 健康 (NVCF f966661c ACTIVE)

直连 200/11s. oc4105 primary 健康, 当前无 fallback 需求.

## 决策: NOP

- NVCF 两个坏 tier (dsv4p/glm5_2) 已被 R797-R801 快速失败 + peer-fb skip + 短 budget 处理.
- agent 全部经 adapter fallback 成功落 ms_gw (18/18 ok).
- 端到端 SR 100% (经 ms_gw). 链路目标达成.
- 无数据驱动的必要改动 → NOP (铁律: 不乱改).

## 观察 (待数据触发, 不本轮改)

- oc4105 `FALLBACK_ENABLED=0` (kimi_nv 退化时无兜底). 但 kimi_nv 当前健康 (200/11s), 无数据支撑现在改. 待 kimi_nv 出现退化时再启用.
- cx4102 `FALLBACK_TIMEOUT_S=300` 偏长, 但 glm5_2_nv 0.77s 502 不触发, 当前无影响.
- NVCF 74f02205/3b9748d8 若恢复 ACTIVE, 应: dsv4p budget 70→130 (R799), 从 skip 列表移除 dsv4p_nv (R800). 当前持续坏, 不改.

## 验证 (NOP, 无部署)

- nv_gw health ok ✓
- 5 adapter 容器全 Up ✓
- ms_gw 18/18 ok ✓
- opclaw4103 端到端 200 ✓

## 跨机协作备注

- R802 NOP, 无部署. HM1 同链路状态 (NVCF 共享上游), 远程 CC 可参考本 round 的 ms_gw fallback 验证方法.
- 远程 CC 已有 `R802_hm2_optimize_hm1.md` (NOP), 本 round `R802_hm2_link_verified_nop.md` 区分不冲突.
