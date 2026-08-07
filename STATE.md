# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R913 (NOP 巡检轮/不改码 — cc2 主链路连续第 22 轮 100% 干净; 坏请求 stream_absolute_cap ×2 + all_tiers_exhausted ×2 (502) 全属 hermes 线, request_id 级 JOIN 铁证 (056d2c5e/493f9224/5d3afd42/9b4fd536), 非 cc2 范围; bad fid 52e1ddb6 仍在 tier attempts 但全属 hermes 宿主, 0 泄漏进 cc2 主链)**
> cc4101-primary (主 nv_gw:40006) 实时 30min = **121/121 = 100% SR, 0 bad** (实拉);
> live DB now()≈2026-08-07 09:30 CST
> 容器: nv_gw Up 11h, cc4101 Up 6h
> 上轮: R912 (NOP, 主链 119/119=100%)

## 本轮 (R913) 改动 + 依据 + 验证

### 改动: 无 (NOP。cc2 主链路连续 22 轮 100% 干净, 无新错误类; bad 请求全属 hermes 非 cc2)

### 依据 (live DB 30min 实拉, ≈2026-08-07 09:30 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **121/121 全 200, 0 bad (100% SR)**。
  实拉 caller 分组 → cc4101-primary total=121 ok=121 bad=0; `AND status!=200` → **0 条**。
- 30min 所有 bad (502) = `caller=hermes` ×4: `all_tiers_exhausted ×2` (avg_dur 180053ms) +
  `stream_absolute_cap ×2` (avg_dur 155678ms)。
- **request_id 级 JOIN 铁证** (nv_requests ⋈ nv_tier_attempts):
  4 bad request_id = 056d2c5e(5 attempts)/493f9224(4)/5d3afd42(3)/9b4fd536(6),
  **全部 caller=hermes, 0 个属于 cc2 主链**。
- fallback (全部 caller) = **0 次 (0/1534)**。
- fid 级: 健康 fid **281478d0** 仍为主链候选; 坏 fid **52e1ddb6** 仍在 tier attempts 出现但全属
  hermes 宿主, cc2 主链候选池由 func_health 健康选择 (281478d0) 隔离, 0 泄漏。
- 容器 health: 4101/40006/40066 全 ok (200), nv_gw Up 11h, cc4101 Up 6h。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **121/121 = 100% SR, 0 bad** (实拉) | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×2 + stream_absolute_cap ×2 | ⚠️ 越界 |
| bad request_id JOIN | 4 req JOIN 全属 hermes (5/4/3/6 attempts), cc2 primary 0 条 | ✅ 隔离 |
| fallback (全部 caller) | 0 次 (0/1534) | ✅ |
| fid 健康 (nv_tier_attempts) | 281478d0 主链候选; 52e1ddb6 全属 hermes 未选中 | ✅ |
| 三 scoped health | 4101/40006/40066 全 ok (200), nv_gw Up 11h | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok (200); cc4101 primary=dsv4f0731_nv。
- 30min nv_requests cc4101-primary 实拉 = 121/121 (0 bad)。
- 30min 所有 bad JOIN 铁证 (request_id 级): 4 条全 caller=hermes, cc2 主链 0 bad。
- 52e1ddb6 全部 attempts JOIN 归属 hermes (RemoteDisconnected/529/Timeout/empty_200), 0 进 cc2;
  func_health 健康选择 (281478d0) 未选中坏 fid。

### 关键判断
cc2 主链路连续第 **22** 轮 (R892-R913) 100% SR 干净。bad 请求 100% 属 hermes,
request_id 级 JOIN 铁证未进 cc2 主链候选池; bad fid 52e1ddb6 = 0 泄漏进 cc2 主链;
fallback 0 次。**不改码**: ①主链 SR 100% 无优化需求; ②坏请求全属 hermes 越 cc2 范围; ③fid 健康选择 (281478d0 vs 52e1ddb6) 已达稳态。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败
4. 坏 fid 52e1ddb6 (hermes 宿主) 与主链健康 fid 281478d0 容器+候选池双层隔离

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)