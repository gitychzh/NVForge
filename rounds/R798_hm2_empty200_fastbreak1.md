# R798: HM2 NVU_EMPTY_200_FASTBREAK 2→1 (dsv4p_nv surge 时 62s 而非 125s)

> 承接 R797 (glm5_2_nv 快速失败 + peer-fb skip). 8 轮定时优化第 2 轮.
> 铁律: 改前有数据 (DB empty_200 日志), 改后有验证 (env 生效 + DB).
> 角色: HM2-only 部署 (纯 env 改动, 无源码变更).

## 改前数据 (2026-07-07, R797 部署后 3.5h 实测)

### DB (nv_requests, 210min 窗口, R797 效果)

| tier_model | status | count | avg_ms | 备注 |
|---|---|---|---|---|
| dsv4p_nv | 200 | 277 | 26451 | SR=95% (277/292) |
| dsv4p_nv | 502 | 15 | 107292 | empty_200, 每次 ~125s |
| glm5_2_nv | 502 | 13 | 64735 | SR=0% (R797 后 70s 502, 后续 NVCF DEGRADED → 0.6s 502) |

### dsv4p_nv empty_200 失败模式 (日志)

每次失败: 2 key × ~62s = **125s** (EMPTY_200_FASTBREAK=2):

```
[14:51:09] [NV-EMPTY-CYCLE] tier=dsv4p_nv k5 empty 200, cycling
[14:51:09] [NV-EMPTY-FASTBREAK] tier=dsv4p_nv 2 consecutive empty_200 ≥ threshold 2, fast-break
[14:51:09] [NV-TIER-FAIL] tier=dsv4p_nv ... empty200=2 ... elapsed=125345ms
```

### NVCF 直连实测 (dsv4p 74f02205, 全 key 504/62s)

| key | 请求 | 结果 | 耗时 |
|---|---|---|---|
| k1 | 裸 "hi" | 504 | 62.9s |
| k2 | 裸 "hi" | 504 | 62.9s |
| k3 | 裸 "hi" | 504 | 62.9s |

NVCF 74f02205 (ai-deepseek-v4-pro) 状态 ACTIVE 但间歇 surge (empty_200/504 交替). dsv4p_nv 仍是 hm4104 primary + cc 自用, 不能像 glm5_2_nv 那样 short-budget (会误杀成功请求, SR 95%).

### NVCF function 状态 (2026-07-07)

| function | name | status |
|---|---|---|
| 3b9748d8 | ai-glm-5_2 | **DEGRADED** (NVCF 现明确 400 拒绝) |
| 74f02205 | ai-deepseek-v4-pro | ACTIVE (间歇 surge) |
| 52e1ddb6 | ai-deepseek-v4-flash | ACTIVE (新, 400 bad-request 未通) |
| 8915fd28 | sglang-deepseek-v4-pro | ACTIVE (404 not-found-for-account, 账户权限不通) |
| f966661c | nvquery-kimi-k2_6 | ACTIVE |

## 根因

- dsv4p_nv 失败全是 `empty_200` (NVCF 74f02205 surge 返回 200 空 body), 单 key 烧 ~62s.
- `NVU_EMPTY_200_FASTBREAK=2` → 每次失败试 2 key = 125s. 改 1 → 第 1 个 empty_200 即 break = 62s, 省一半.
- dsv4p_nv SR 仍 95%, empty_200 是间歇性, 不能 short-budget (误杀成功请求).

## 修复方案 (HM2, 纯 env)

`docker-compose.yml` nv_gw.environment:
```yaml
- NVU_EMPTY_200_FASTBREAK=1        # R798: 2→1, 第1个 empty_200 即 break
```
影响: 全局 (dsv4p_nv/kimi_nv 受益; glm5_2_nv 不受影响, 它是 400/504 非 empty_200).

## 实施步骤 (HM2, 已执行)

1. 备份 `docker-compose.yml` → `.bak.R798`.
2. 改 `NVU_EMPTY_200_FASTBREAK=2` → `1`.
3. `docker compose up -d nv_gw` (重建容器读新 env).
4. 验证.

## 验证 (铁律: 改后有验证)

### V1: env 生效
```
$ docker exec nv_gw env | grep NVU_EMPTY_200_FASTBREAK
NVU_EMPTY_200_FASTBREAK=1
```
✓

### V2: health
```
$ curl nv_gw/health
{"status":"ok",...}
```
✓

### V3: DB 改后窗口 (glm5_2_nv 已 0.6s 502, dsv4p_nv 仍 200)

| tier_model | status | count | avg_ms |
|---|---|---|---|
| dsv4p_nv | 200 | 2 | 54106 |
| glm5_2_nv | 502 | 3 | 687 |

✓ glm5_2_nv 0.687s 502 (NVCF DEGRADED 立即 400, R797 peer-fb skip 仍保护).
注: 本次窗口未触发 dsv4p_nv empty_200 (本次是 504 cycling), R798 杠杆待下次 empty_200 事件验证 (预期 62s 而非 125s).

## 预期效果

- dsv4p_nv empty_200 失败: 125s → 62s (省 63s/失败请求).
- hm4104 (dsv4p_nv primary) surge 时卡顿减半.
- 成功请求不受影响 (fastbreak 只在 empty_200 触发).

## 回滚

`docker-compose.yml` 改回 `NVU_EMPTY_200_FASTBREAK=2` + `docker compose up -d nv_gw`.

## 跨机协作备注

- R798 纯 env 改动, HM2 已部署. HM1 同样 dsv4p_nv empty_200 问题 (同 NVCF 上游), 远程 CC 可同步改 HM1 compose.
- 注意: 远程 CC 已有 `rounds/R798_hm2_optimize_hm1.md` (NOP, HM2→HM1 方向). 本 round 文件名 `R798_hm2_empty200_fastbreak1.md` 区分, 不冲突.
