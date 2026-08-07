# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R905 (NOP 巡检轮/不改码 — cc2 主链路连续第 14 轮 100% 干净; 坏请求 all_tiers_exhausted ×3 + stream_absolute_cap ×1 (502) 全属 hermes 线, JOIN 铁证, 非 cc2 范围; 0 条 bad fid 52e1ddb6 泄漏进 cc2)**
> cc4101-primary (主 nv_gw:40006) 实时 30min = **132/132 = 100% SR, 0 bad** (实拉);
> live DB now()≈2026-08-07 09:00 CST
> 上轮: R904 (NOP, 主链 135/135=100%)

## 本轮 (R905) 改动 + 依据 + 验证

### 改动: 无 (NOP。cc2 主链路连续 14 轮 100% 干净, 无新错误类; bad 请求全属 hermes 非 cc2)

### 依据 (live DB 30min 实拉, ≈2026-08-07 09:00 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **132/132 全 200, 0 bad (100% SR)**。
  实拉 `WHERE caller='cc4101-primary' AND status!=200` → **0 条**。
- per-key (nv_tier_attempts JOIN 30min): 5 key × 26-27 = 全走健康 fid **281478d0**,
  error_type=pexec_success, 0 错误。0 条 52e1ddb6 泄漏进 cc2 候选池。
- 30min 所有 bad = `caller=hermes`: `all_tiers_exhausted ×3 (avg 178497ms)` +
  `stream_absolute_cap ×1 (avg 177533ms)`。
- buffer (cc4101-primary): 全 attempt=1/5 成交, 8-12s 复盘 success_tool_call, 0 重试 / 0 429 / 0 cooldown。
- fallback (cc2 线) 0 次。
- 容器 health: 4101/40006/40066 全 ok (200), nv_gw Up 6 hours。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **132/132 = 100% SR, 0 bad** (实拉) | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×3 + stream_absolute_cap ×1, avg ~178s | ⚠️ 越界 |
| bad fid 52e1ddb6 泄漏 | cc2 primary JOIN 0 条 | ✅ 隔离 |
| per-key (nv_tier_attempts) | 主链各 key 281478d0 ×26-27, 全 pexec_success, 0 错误 | ✅ |
| buffer (cc4101-primary) | 全 attempt=1/5, 0 重试 / 0 429 / 0 cooldown | ✅ |
| 三 scoped health | 4101/40006/40066 全 ok (200), nv_gw Up 6h | ✅ |
| fallback (cc2 线) | 0 次 | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok (200); cc4101 primary=dsv4f0731_nv。
- 30min nv_requests cc4101-primary 实拉 = 132/132 (0 bad)。
- 30min 所有 bad JOIN 铁证: 3+1 条全 caller=hermes, cc2 主链 0 bad。
- per-key 主链全 281478d0 健康 0 error, 0 bad-fid。

### 关键判断
cc2 主链路连续 14 轮 (R892-R905) 100% SR 干净。bad 请求 100% 属 hermes caller 活动,
JOIN 铁证未进 cc2 主链候选池; bad fid 52e1ddb6 = 0 泄漏进 cc2。
**不改码**: ①主链 SR 100% 无优化需求; ②坏请求全属 hermes 越 cc2 范围; ③容器级分离持续奏效, 已达稳态。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)
