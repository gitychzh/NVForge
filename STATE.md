# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R904 (NOP 巡检轮/不改码 — cc2 主链路连续第 13 轮 100% 干净; 4 条 all_tiers_exhausted+1 条 stream_absolute_cap (502) + 27 条 bad fid 52e1ddb6 全属 hermes 线, JOIN 铁证, 非 cc2 范围)**
> cc4101-primary (主 nv_gw:40006) 实时 30min = **135/135 = 100% SR, 0 bad** (实拉);
> live DB now()≈2026-08-07 CST
> 上轮: R903 (NOP, 主链 135/135=100%)

## 本轮 (R904) 改动 + 依据 + 验证

### 改动: 无 (NOP。cc2 主链路连续 13 轮 100% 干净, 无新错误类; bad 请求 + bad fid 全属 hermes 非 cc2)

### 依据 (live DB 30min 实拉)

- 30min cc4101-primary (主 nv_gw:40006) = **135/135 全 200, 0 bad (100% SR)**。
  实拉 `WHERE caller='cc4101-primary' AND status!=200` → **0 条**。
- 30min 所有 bad payload = `caller=hermes`: `all_tiers_exhausted ×4` +
  `stream_absolute_cap ×1`。
- 坏 fid 52e1ddb6 (27 条/30min) 全走 dsv4f0731_nv tier 但 **request_id JOIN 铁证**: 27 条全
  caller=hermes, cc2 主链 0 泄漏 (越界容器 40666 hermes 线, 容器级分离奏效)。
- fallback (cc2 线) 0 次; 0 429 / 0 buffer 重试。
- 三 scoped 容器 health: 4101/40006/40066 全 ok (200, 5 keys), nv_gw primary=dsv4f0731_nv。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **135/135 = 100% SR, 0 bad** (实拉) | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×4 + stream_absolute_cap ×1 | ⚠️ 越界 |
| bad fid 52e1ddb6 | 27 条全 caller=hermes (JOIN 铁证), cc2 0 泄漏 | ✅ 隔离 |
| fallback (cc2 线) | 0 次 | ✅ |
| 三 scoped health | 4101/40006/40066 全 ok (200, 5 keys) | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok (200); cc4101 primary=dsv4f0731_nv。
- 30min nv_requests cc4101-primary 实拉 = 135/135 (0 bad)。
- 52e1ddb6 归属 JOIN 铁证: 27 条全 caller=hermes, cc2 主链 0 泄漏。
- 30min bad payload 100% caller=hermes (all_tiers_exhausted ×4 + stream_absolute_cap ×1)。

### 关键判断
cc2 主链路连续 13 轮 (R892 139/139, R893 153/153, R894 143/143, R895 137/137,
R896 134/134, R897 126/126, R898 125/125, R899 124/124, R900 126/126, R901 127/127,
R902 131/131, R903 135/135, **R904 135/135**) 100% SR 干净。bad 请求 + bad fid 52e1ddb6
100% 属 hermes caller 活动, JOIN 铁证未进 cc2 主链候选池。
**不改码**: ①主链 SR 100% 无优化需求; ②坏请求/坏 fid 全属 hermes 越 cc2 范围; ③容器级分离持续奏效, 已达稳态。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)