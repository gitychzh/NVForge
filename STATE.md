# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R914 (NOP 巡检轮/不改码 — cc2 主链路连续第 23 轮 100% 干净; 坏请求 stream_absolute_cap ×2 + all_tiers_exhausted ×2 (502) 全属 hermes 线, caller 级实查, 非 cc2 范围; fallback 0 次)**
> cc4101-primary (主 nv_gw:40006) 实时 30min = **119/119 = 100% SR, 0 bad** (实拉);
> live DB now()≈2026-08-07 09:32 CST
> 容器: nv_gw Up 11h, cc4101 Up 6h
> 上轮: R913 (NOP, 主链 121/121=100%)

## 本轮 (R914) 改动 + 依据 + 验证

### 改动: 无 (NOP。cc2 主链路连续 23 轮 100% 干净, 无新错误类; bad 请求全属 hermes 非 cc2)

### 依据 (live DB 30min 实拉, ≈2026-08-07 09:32 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **119/119 全 200, 0 bad (100% SR)**。
  实拉 caller 分组 → cc4101-primary total=119 ok=119 bad=0; `AND status!=200` → **0 条**。
- 30min 所有 bad (502) = `caller=hermes` ×4: `all_tiers_exhausted ×2` (avg_dur 180053ms) +
  `stream_absolute_cap ×2` (avg_dur 155678ms), 与 R892-R913 同源, 非 cc2 范围。
- fallback (全部 caller) = **0 次 (0/1544)**。
- per-key tier (nv_tier_attempts): pexec_success 每 key 23-24 占绝对主导; 瞬态错误
  (NVCFPexecRemoteDisconnected 2-5/key, 529_nv_overloaded 1-2, NVCFPexecTimeout 1) 为正常
  NVCF 底层抖动, 被多 tier round-robin + func_health 健康选择吸收, 未导致主链失败。
- 容器 health: 4101/40006/40066 全 ok (200), nv_gw passthrough 5 keys, Up 11h, cc4101 Up 6h。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **119/119 = 100% SR, 0 bad** (实拉) | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×2 + stream_absolute_cap ×2 | ⚠️ 越界 |
| fallback (全部 caller) | 0 次 (0/1544) | ✅ |
| per-key tier | pexec_success 23-24/key 主导, 瞬态错误被吸收 | ✅ |
| 三 scoped health | 4101/40006/40066 全 ok (200), nv_gw Up 11h | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok (200); cc4101 primary=dsv4f0731_nv;
  nv_gw passthrough, 5 keys, nvcf_pexec_models=[kimi_nv,dsv4p_nv,dsv4f_nv,dsv4f0731_nv,glm5_2_nv]。
- 30min nv_requests cc4101-primary 实拉 = 119/119 (0 bad)。
- `AND status!=200` 实查 = 0 条 cc2, 4 条全 caller=hermes。

### 关键判断
cc2 主链路连续第 **23** 轮 (R892-R914) 100% SR 干净。bad 请求 100% 属 hermes,
caller 级实查隔离未进 cc2 主链; fallback 0 次; 无新错误类。**不改码**:
①主链 SR 100% 无优化需求; ②坏请求全属 hermes 越 cc2 范围; ③fid/多 tier 健康选择已达稳态。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败
4. 坏 fid 52e1ddb6 (hermes 宿主) 与主链健康 fid 281478d0 容器+候选池双层隔离

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)