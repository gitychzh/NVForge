# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R916 (NOP 巡检轮/不改码 — cc2 主链路连续第 25 轮 100% 干净; 坏请求 stream_absolute_cap ×2 + all_tiers_exhausted ×3 (502) 全属 hermes 线, request_id 级 JOIN 铁证 (493f9224/9b4fd536/5d3afd42/056d2c5e/bfcd651d), 非 cc2 范围; fallback 0 次)**
> cc4101-primary (主 nv_gw:40006) 实时 30min = **117/117 = 100% SR, 0 bad** (实拉);
> live DB now()≈2026-08-07 09:38 CST
> 容器: nv_gw Up 6h, cc4101 Up 6h
> 上轮: R915 (NOP, 主链 113/113=100%)

## 本轮 (R916) 改动 + 依据 + 验证

### 改动: 无 (NOP。cc2 主链路连续 25 轮 100% 干净, 无新错误类; bad 请求全属 hermes 非 cc2)

### 依据 (live DB 30min 实拉, ≈2026-08-07 09:38 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **117/117 全 200, 0 bad (100% SR)**。
  实拉 caller 分组 → cc4101-primary total=117 ok=117 bad=0; `AND status!=200` → **0 条**。
- 30min 所有 bad (502) = `caller=hermes` ×5: `all_tiers_exhausted ×3` (avg_dur 180045ms) +
  `stream_absolute_cap ×2` (avg_dur 155678ms)。
- **request_id 级 JOIN 铁证** (nv_requests ⋈ nv_tier_attempts):
  5 bad request_id = 493f9224(4 attempts)/9b4fd536(6)/5d3afd42(3)/056d2c5e(5)/bfcd651d(5),
  **全部 caller=hermes, 0 个属于 cc2 主链**。
- fallback (cc_requests 30min total=118) = **0 次**。
- per-key 瞬态错误 (NVCFPexecRemoteDisconnected / Timeout / 529_nv_overloaded) 分散 k0~k4,
  被 multi-tier round-robin + func_health 健康选择吸收, pexec_success 稳定, 未达 cc2 全挂。
- 容器 health: 4101/40006 全 ok (200), nv_gw Up 6h, cc4101 Up 6h, dsv4p_nv40066 Up 2d。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **117/117 = 100% SR, 0 bad** (实拉) | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×3 + stream_absolute_cap ×2 | ⚠️ 越界 |
| bad request_id JOIN | 5 req JOIN 全属 hermes (4/6/3/5/5 attempts), cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (0/118) | ✅ |
| per-key tier | pexec_success 主导, 瞬态错误被吸收 | ✅ |
| scoped health | 4101/40006 全 ok (200), nv_gw Up 6h | ✅ |

### 验证
- curl 4101/40006 → 全 ok; cc4101 primary=dsv4f0731_nv; nv_gw passthrough 5 keys。
- 30min nv_requests cc4101-primary 实拉 = 117/117 (0 bad)。
- 30min 所有 bad JOIN 铁证 (request_id 级): 5 条全 caller=hermes, cc2 主链 0 bad。
- cc_requests fallback = 0 次 (0/118)。

### 关键判断
cc2 主链路连续第 **25** 轮 (R892-R916) 100% SR 干净。bad 请求 100% 属 hermes,
request_id 级 JOIN 铁证未进 cc2 主链; fallback 0 次; 无新错误类。**不改码**:
①主链 SR 100% 无优化需求; ②坏请求全属 hermes 越 cc2 范围; ③多 tier round-robin + func_health 健康选择已达稳态。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败
4. 坏 fid 52e1ddb6 (hermes 宿主) 与主链健康 fid 281478d0 容器+候选池双层隔离

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)