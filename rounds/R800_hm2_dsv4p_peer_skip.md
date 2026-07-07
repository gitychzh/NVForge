# R800: HM2 dsv4p_nv 加入 peer-fb skip (HM1 同 NVCF 504, 省 25s)

> 承接 R799 (dsv4p tier budget 130). 8 轮定时优化第 4 轮.
> 铁律: 改前有数据 (HM1 dsv4p 80s 超时 + peer-fb 3/3 FAILED), 改后有验证 (skip 日志).
> 角色: HM2-only (纯 env, 复用 R797 peer-fb skip 机制).

## 改前数据 (2026-07-07, R799 后)

### HM1 dsv4p_nv 直连 (peer-fb 目标)

```
$ curl HM1:40006 dsv4p_nv "hi"
HTTP 000 80.0s (timeout)
```
HM1 dsv4p_nv 也 80s 超时 — 同 NVCF 74f02205 持续 504, peer-fb 必失败.

### HM2 peer-fb for dsv4p_nv 最近 3/3 全 FAILED

```
[15:54:21] peer fallback FAILED for model=dsv4p_nv
[15:56:41] peer fallback FAILED for model=dsv4p_nv
[16:00:32] peer fallback FAILED for model=dsv4p_nv
```
每次 25s timeout → 浪费 25s, 总 125+25=150s 才 502.

### dsv4p_nv 最近 15min SR=0% (NVCF 持续 504)

| tier_model | status | count | avg_ms |
|---|---|---|---|
| dsv4p_nv | 502 | 3 | 125457 |

NVCF 74f02205 从间歇 surge (R797 时 SR 95%) 恶化到持续 504 (SR 0%).

## 根因

dsv4p_nv 全坏时 (NVCF 504), R799 让本地 125s fail, 但仍触发 peer-fb (25s) 到 HM1.
HM1 同 NVCF 74f02205 同 504 → peer-fb 必失败 → 多浪费 25s. 客户端等 150s 才 502→ms_gw.

## 修复方案 (HM2, 纯 env, 复用 R797 机制)

`docker-compose.yml`:
```yaml
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv  # R797+R800: peer 同 NVCF 504
```
R797 已加 per-model peer-fb skip (handlers.py). dsv4p_nv 加入列表, 无需改源码.

## 实施步骤 (HM2, 已执行)

1. 备份 compose → `.bak.R800`.
2. `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv` → `glm5_2_nv,dsv4p_nv`.
3. `docker compose up -d nv_gw`.
4. 验证.

## 验证

### V1: env 生效
```
$ docker exec nv_gw env | grep NVU_PEER_FB_SKIP_MODELS
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
```
✓

### V2: peer-fb skip for dsv4p (日志)
```
$ curl nv_gw dsv4p_nv → 502 130.074s
[16:06:06] [NV-PEER-FB] model=dsv4p_nv in peer-fb skip list (NVCF DEGRADING, peer same function also bad), returning local 502 for agent ms_gw fallback
```
✓ 130s 502 (改前 150s = 125 本地 + 25 peer-fb), peer-fb skipped, 省 20s.

### V3: health ok ✓

## 预期效果

- dsv4p_nv 全坏时: 150s → 130s 502 (省 20s).
- hm4104 (dsv4p_nv primary) + cc 自用 dsv4p 链路: NVCF 504 期间更快落 ms_gw.
- 注意: dsv4p_nv 是间歇性 (R797 时 SR 95%), 现 SR 0% 是 NVCF 持续 504. NVCF 恢复后应从 skip 列表移除 dsv4p_nv (恢复 peer-fb rescue 能力). env `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv` 即回退.

## 回滚

compose 改回 `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv` + restart.

## 跨机协作备注

- R800 纯 env, HM2 已部署. HM1 dsv4p 同坏 (peer-fb 本就失败), HM1 可同步加 dsv4p_nv 到 skip (省对 HM2 的 peer-fb? HM1 peer 是 HM2, 同 NVCF 同坏, 加 skip 同理).
- 远程 CC 已有 `R800_hm2_optimize_hm1.md` (NOP), 本 round `R800_hm2_dsv4p_peer_skip.md` 区分不冲突.
