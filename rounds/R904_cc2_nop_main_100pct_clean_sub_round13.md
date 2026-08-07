# R904 cc2 NOP — 主链 100% 干净 (135/135), bad 全 hermes (1 all_tiers_exhausted ×4 + 1 stream_absolute_cap + 27× 52e1ddb6 JOIN-proven); 13th consecutive clean round

> 轮: R904 (NOP 巡检轮/不改码)
> cc4101-primary (主 nv_gw:40006) 实时 30min = **135/135 全部 200, 0 bad**
> live DB now()≈2026-08-07 (CST)
> 上轮: R903 (NOP, 主链 135/135 = 100%)

## 决策
**NOP, 不改码。** cc2 主链路连续第 13 轮 100% SR 干净; 全部 bad 请求 + 坏 fid 52e1ddb6
依旧 100% 属 hermes 线, JOIN 铁证, 容器级分离持续奏效, 已达稳态。

## 依据 (live DB 30min 实拉)

- 30min cc4101-primary (主 nv_gw:40006) = **135/135 全 200, 0 bad (100% SR)**。
  实拉 `WHERE caller='cc4101-primary' AND status!=200` → **0 条**。
- 30min 所有 bad payload = `caller=hermes`: `all_tiers_exhausted ×4` +
  `stream_absolute_cap ×1`。0 条进 cc2 主链。
- 坏 fid 52e1ddb6 (27 条/30min) 全走 dsv4f0731_nv tier 但 **request_id JOIN 铁证**:
  27 条全 caller=hermes, cc2 主链 0 泄漏 (越界容器 40666 hermes 线持续隔离)。
- fallback (cc2 线) 0 次; 0 429 / 0 buffer 重试 (上轮 buffer 全 attempt=1/5 成交)。
- 三 scoped 容器 health: 4101/40006/40066 全 ok (200, 5 keys); cc4101 primary=dsv4f0731_nv。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **135/135 = 100% SR, 0 bad** (实拉) | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×4 + stream_absolute_cap ×1 | ⚠️ 越界 |
| bad fid 52e1ddb6 | 27 条全 caller=hermes (JOIN 铁证), cc2 0 泄漏 | ✅ 隔离 |
| fallback (cc2 线) | 0 次 | ✅ |
| 容器 health | 4101/40006/40066 全 ok (5 keys), primary=dsv4f0731_nv | ✅ |

## 验证
- 实拉 cc4101-primary 30min = 135/135 (0 bad)。
- 30min bad payload 100% caller=hermes (all_tiers_exhausted ×4 + stream_absolute_cap ×1)。
- 52e1ddb6 JOIN 铁证: 27 条全 caller=hermes, cc2 主链 0 泄漏。
- curl 4101/40006/40066 → 全 ok。

## 下一步
主链 SR 100% 无优化需求, 维持 NOP 巡检节奏。继续观察 hermes 线坏 fid/bad 是否
随时间衰减; 若出现新主链错误类再介入。

## 修复链 (沿用)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv。
2. dsv4f0731_nv 主链已用健康 fid; 多 tier round-robin + func_health 自适应吸收底层瞬态失败。
3. 容器级分离持续隔离 hermes 线越界活动。