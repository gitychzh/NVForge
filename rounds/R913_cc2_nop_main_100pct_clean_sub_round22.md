# R913 — cc2 NOP 巡检轮

## 结论
cc2 主链路连续第 **22** 轮 (R892-R913) 100% SR 干净。**不改码**。

## 数据 (live DB 30min 实拉, ≈2026-08-07 09:30 CST)

- **cc4101-primary (cc2 主 nv_gw:40006) = 121/121 = 100% SR, 0 bad**
  实拉: `33cc41...` caller 分组 → cc4101-primary total=121 ok=121 bad=0; `AND status!=200` → 0 条
- 30min 所有 bad (502) 全属 **hermes 线** ×4:
  - all_tiers_exhausted ×2 (status 502, avg_dur 180053ms)
  - stream_absolute_cap ×2 (status 502, avg_dur 155678ms)
- **JOIN 铁证** (nv_requests ⋈ nv_tier_attempts, request_id 级):
  4 个 bad request_id (056d2c5e / 493f9224 / 5d3afd42 / 9b4fd536) 全部 caller=hermes,
  各带 3~6 次 attempts (5/4/3/6), **0 个属于 cc2 主链**
- fallback (全部 caller) = **0 次 (0/1534)**, cc2 线 0 回退
- 三容器 health 全 ok (200): cc4101 primary=dsv4f0731_nv; nv_gw 9k 5 key passthrough; dsv4p_nv40066
- 容器: nv_gw Up 11h, cc4101 Up 6h
- 参数未变: NV_GLM52_MODE_CHAIN=pexec_us_rr, KEY_FID_BIND=0:0;...;4:0, NVU_DISABLE_MS_FALLBACK=0, buffer 5×90s

## 判断
主链 SR 100% 无优化需求; bad 请求 100% 属 hermes (JOIN 铁证, request_id 级) 越 cc2 范围;
fallback 0 次; 容器稳态。fid 层: bad fid 52e1ddb6 仍在 tier attempts 出现但全属 hermes 宿主,
cc2 主链候选池由 func_health 健康选择 (281478d0) 保障隔离。**NOP**。

## 改动
无。无 commit 源码变更。