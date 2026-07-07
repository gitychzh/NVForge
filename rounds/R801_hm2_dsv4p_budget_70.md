# R801: HM2 dsv4p_nv budget 130→70 (NVCF 74f02205 持续 504 SR=0%)

> 承接 R800 (dsv4p peer-fb skip). 8 轮定时优化第 5 轮.
> 铁律: 改前有数据 (dsv4p 20min SR=0% + NVCF 直连全 504), 改后有验证 (70s 502).
> 角色: HM2-only (纯 env).

## 改前数据 (R800 后, 20min 窗口)

| tier_model | status | count | avg_ms | max_ms |
|---|---|---|---|---|
| dsv4p_nv | 502 | 5 | 126405 | 130070 | ← R799 budget 130, 2 key 504 |
| glm5_2_nv | 502 | 9 | 774 | 1111 |

dsv4p_nv 20min SR=0% (5/5 全 502). NVCF 直连 74f02205 全 key 504/63s (R799 时已是, 持续未恢复).
对比 R797 时 (3.5h 前) dsv4p_nv SR=95% — NVCF 74f02205 从间歇 surge 恶化到持续 504.

kimi_nv (f966661c) 健康: 直连 200/11s. ms_gw 健康 (fallback 目标 OK).

## 根因

dsv4p_nv NVCF 持续 504 (20min SR=0%), R799 budget=130 让 2 key × 63s = 125s 才 fail.
既然 NVCF 504 是持续 (非间歇), 第 2 key 必也 504, 第 2 key 的 63s 是浪费.
budget 130→70: 1 key 504 (63s) 后 remaining<5s break → 70s fail, 省 60s.

## 修复方案 (HM2, 纯 env)

```yaml
- NVU_TIER_BUDGET_DSV4P_NV=70   # R799:130 → R801:70. NVCF 持续504, 1key即break
```

## 实施步骤 (HM2, 已执行)

1. 备份 compose → `.bak.R801`.
2. `NVU_TIER_BUDGET_DSV4P_NV=130` → `70`.
3. `docker compose up -d nv_gw`.
4. 验证.

## 验证

### V1: 70s 502
```
$ curl nv_gw dsv4p_nv → 502 70.020s
```
✓ 改前 (R799) 130s, 现 70s, 省 60s.

### V2: peer-fb skip 仍生效
```
[16:15:33] [NV-PEER-FB] model=dsv4p_nv in peer-fb skip list ... returning local 502
```
✓

### V3: health ok ✓

## 预期效果

- dsv4p_nv 全坏时: 130s → 70s 502 (省 60s).
- hm4104 + cc 自用 dsv4p: NVCF 504 期间 70s 落 ms_gw (改前 130s).
- ⚠ 风险: budget 70 < 成功 max 108s. 若 NVCF 74f02205 恢复且有慢成功请求 (>70s), 会被误杀.
  缓解: NVCF 恢复后改回 130 (env 一行). 当前 SR=0% + 直连全 504, 70 安全.

## 回滚

compose `NVU_TIER_BUDGET_DSV4P_NV=130` (R799 值) + restart. 或删该行回退全局 180s.

## 跨机协作备注

- R801 纯 env, HM2 已部署. HM1 同 dsv4p 持续 504 (HM1 直连 80s 超时), 可同步改 70.
- 远程 CC 已有 `R801_hm2_optimize_hm1.md` (NOP), 本 round `R801_hm2_dsv4p_budget_70.md` 区分不冲突.
