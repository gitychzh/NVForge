# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R912 (NOP 巡检轮/不改码 — cc2 主链路连续第 21 轮 100% 干净; 坏请求 stream_absolute_cap ×2 + all_tiers_exhausted ×1 (502) 全属 hermes 线, JOIN 铁证, 非 cc2 范围; bad fid 52e1ddb6 24 次 attempts 全命 hermes, 0 泄漏进 cc2 主链)**
> cc4101-primary (主 nv_gw:40006) 实时 30min = **119/119 = 100% SR, 0 bad** (实拉);
> live DB now()≈2026-08-07 09:25 CST
> 容器: nv_gw Up 6h, cc4101 Up 6h
> 上轮: R911 (NOP, 主链 119/119=100%)

## 本轮 (R912) 改动 + 依据 + 验证

### 改动: 无 (NOP。cc2 主链路连续 21 轮 100% 干净, 无新错误类; bad 请求全属 hermes 非 cc2)

### 依据 (live DB 30min 实拉, ≈2026-08-07 09:25 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **119/119 全 200, 0 bad (100% SR)**。
  实拉 `WHERE caller='cc4101-primary' AND status!=200` → **0 条**。
- 30min 所有 bad = `caller=hermes`: `stream_absolute_cap ×2` + `all_tiers_exhausted ×1` (均 502)。
- fid 级: 健康 fid **281478d0** = pexec_success ×122, 0 错误 (cc2 主链专用)。
  坏 fid **52e1ddb6** = 24 次 attempts 全错误 (NVCFPexecRemoteDisconnected ×19 / 529_nv_overloaded ×3 /
  NVCFPexecTimeout ×1 / empty_200 ×1), JOIN 铁证 `52e1ddb6|hermes|24` → 0 泄漏进 cc2 主链。
- 容器 health: 4101/40006/40066 全 ok (200), nv_gw Up 6h, cc4101 Up 6h。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **119/119 = 100% SR, 0 bad** (实拉) | ✅ |
| hermes 线 bad (502) | stream_absolute_cap ×2 + all_tiers_exhausted ×1 | ⚠️ 越界 |
| bad fid 52e1ddb6 泄漏 | 24 attempts 全属 hermes (JOIN), cc2 primary 0 条 | ✅ 隔离 |
| fid 健康 (nv_tier_attempts) | 281478d0 ×122 pexec_success 0 错; 52e1ddb6 全错未选中 | ✅ |
| 三 scoped health | 4101/40006/40066 全 ok (200), nv_gw Up 6h | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok (200); cc4101 primary=dsv4f0731_nv。
- 30min nv_requests cc4101-primary 实拉 = 119/119 (0 bad)。
- 30min 所有 bad JOIN 铁证: 3 条全 caller=hermes, cc2 主链 0 bad。
- 52e1ddb6 全部 24 次 attempts JOIN 归属 hermes (RemoteDisconnected/529/Timeout/empty_200), 0 进 cc2;
  func_health 健康选择 (281478d0) 未选中坏 fid。

### 关键判断
cc2 主链路连续第 **21** 轮 (R892-R912) 100% SR 干净。bad 请求 100% 属 hermes,
JOIN 铁证未进 cc2 主链候选池; bad fid 52e1ddb6 = 0 泄漏进 cc2 主链。
**不改码**: ①主链 SR 100% 无优化需求; ②坏请求全属 hermes 越 cc2 范围; ③fid 健康选择 (281478d0 vs 52e1ddb6) 已达稳态。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败
4. 坏 fid 52e1ddb6 (hermes 宿主) 与主链健康 fid 281478d0 容器+候选池双层隔离

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)