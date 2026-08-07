# R907 — cc2 NOP 巡检轮 (main 100% clean, sub round 16)

> 2026-08-07 | HM2 cc2 → HM2 nv_gw:40006 (primary=dsv4f0731_nv)
> **判定: NOP, 不改码.** cc2 主链路连续第 16 轮 100% SR 干净 (R892-R907).
> 坏请求 3 条 100% 属 hermes caller (JOIN 铁证, 越 cc2 范围); bad fid 52e1ddb6 0 泄漏进 cc2 主链.

## 改动: 无 (NOP)

cc4101-primary 主链 30min 实拉 = **134/134 = 100% SR, 0 bad**。
bad fid 52e1ddb6 在候选池 ×5-7 (0 success, 未被选中) → 0 泄漏进 cc2 主链。

## 依据 (live DB 实拉 2026-08-07 ~09:05 CST)

- **30min cc4101-primary** (主 nv_gw:40006): `WHERE caller='cc4101-primary' AND status!=200` → **0 条**, 134/134 全 200 (100% SR)。
- **30min 所有 bad** (JOIN 铁证): `all_tiers_exhausted ×2` + `stream_absolute_cap ×1` = 3 条, **全 caller=hermes** (502), 非 cc2。
- **per-key (nv_tier_attempts)**: 5 key 全走健康 fid **281478d0** ×26-27 = 100% pexec_success, 0 错误。
  bad fid 52e1ddb6 在候选池 ×5-7 (0 success, 0 选中) → 0 泄漏。
- **buffer (cc4101-primary)**: 全 `attempt=1/5` 成交, 1-13s 复盘 success, 0 重试 / 0 429 / 0 cooldown。
- **fallback (cc2 线)**: 0 次。
- **容器 health**: 4101 (primary=dsv4f0731_nv) / 40006 (5 keys) / 40066 — 全 ok (200)。nv_gw Up ~10h。

## 数据快照 (30min)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **134/134 = 100% SR, 0 bad** (实拉) | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×2 + stream_absolute_cap ×1, avg ~177s | ⚠️ 越界 |
| bad fid 52e1ddb6 泄漏 | cc2 primary JOIN 0 条 (候选池 ×5-7 未被选中) | ✅ 隔离 |
| per-key (nv_tier_attempts) | 主链各 key 281478d0 ×26-27, 全 pexec_success 0 错误 | ✅ |
| buffer (cc4101-primary) | 全 attempt=1/5, 1-13s, 0 重试 / 0 429 / 0 cooldown | ✅ |
| 三 scoped health | 4101/40006/40066 全 ok (200), nv_gw Up 10h | ✅ |
| fallback (cc2 线) | 0 次 | ✅ |

## 验证
- curl 4101/40006/40066 → 全 ok (200).
- 30min nv_requests cc4101-primary 实拉 = 134/134 (0 bad).
- 30min 所有 bad JOIN 铁证: 3 条全 caller=hermes, cc2 主链 0 bad.
- per-key 主链全 281478d0 健康 0 error; 52e1ddb6 ×5-7 候选池 0 success 0 选中.

## 关键判断
cc2 主链路连续第 16 轮 (R892-R907) 100% SR 干净。bad 请求 100% 属 hermes caller 活动,
JOIN 铁证未进 cc2 主链候选池; bad fid 52e1ddb6 = 0 泄漏进 cc2。
**不改码**: ①主链 SR 100% 无优化需求; ②坏请求全属 hermes 越 cc2 范围; ③容器级 + fid 级分离持续奏效, 已达稳态。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败

## 下一步
继续 NOP 监控。若 hermes 线 all_tiers_exhausted 频率上升或 52e1ddb6 开始泄漏进 cc2 主链
(JOIN 后 caller=cc4101-primary 且 fid=52e1ddb6), 再介入。当前无 cc2 范围改动需做。