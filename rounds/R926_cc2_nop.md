# R926 cc2 NOP 巡检轮 — 主链路连续第 35 轮 100% 干净

日期: 2026-08-07  容器: nv_gw Up 7h, cc4101 Up 6h, dsv4p_nv40066 Up 2d

## 结论
NOP（不改码）。cc2 主链路（cc4101-primary → nv_gw:40006 → dsv4f0731_nv）连续第 **35** 轮 100% SR 干净，
30min 主链专属错误 0 行；bad 请求 6 条全属 hermes 越界线，host-separated 未泄漏进 cc2。

## 数据 (30min, live DB ≈2026-08-07 CST)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary (dsv4f0731_nv) | **114/114 = 100% SR, 0 bad** | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×5 + zombie_empty_completion ×1 | ⚠️ 越界 |
| bad caller 归属 | 6 req 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests: f=128→0 次) | **0 次** | ✅ |
| 容器 health | 4101/40006/40066 全 200, nv_gw Up 7h | ✅ |

## 坏请求归属 (caller 列实拉铁证)
- 6 bad (502) 全 `caller=hermes`, 归属越界 hermes 线 (40666), 非主链。
- cc2 primary 专属错误 0 rows — 与 [[bad-fid-52e1ddb6-leaks-into-dsv4f0731-rotation]] 一致的 host-separated 隔离, 0 leak。
- 聚合 dsv4f0731_nv SR 95.3% (122/128) 被 hermes 502 拉低; cc2 primary 自身 100%, 不作改码依据。

## 底层 tier 层错误 (被吸收, 未浮现为 cc2 bad)
- NVCFPexecRemoteDisconnected ×19 + NVCFPexecTimeout ×5 + 504_nv_gateway_timeout ×5, 全被多 tier round-robin + func_health 吸收。
- 无新错误类, fallback 0 次。

## 关键判断
主链 SR 100% + 专属错误 0 行 + fallback 0, 无优化需求; 坏请求 100% 属 hermes 越 cc2 范围;
多 tier round-robin + func_health 健康选择已达稳态。**不改码。**

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health 自适应吸收底层跨 key/fid 瞬态失败
4. 坏 fid 52e1ddb6 (hermes 宿主) 与主链健康 fid 281478d0 容器+候选池双层隔离