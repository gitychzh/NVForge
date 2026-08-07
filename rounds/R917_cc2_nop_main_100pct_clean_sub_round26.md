# R917 cc2 NOP: primary 100% clean (120/120), bad all hermes (4 all_tiers_exhausted+1 stream_absolute_cap, caller+JOIN-proven hermes, 0 leak into cc2); fallback 0; 26th consecutive clean round (R892-R917)

**轮: R917 (NOP 巡检轮 / 不改码)**
**时间: 2026-08-07 09:43 CST (live DB now≈09:38)**
**容器: nv_gw Up 6h, cc4101 Up 6h, dsv4p_nv40066 Up 2d**

## 结论
cc2 主链路 (cc4101-primary → nv_gw:40006) 连续第 **26** 轮 (R892-R917) 100% SR 干净。
30min 实拉 **120/120 全 200, 0 bad**。所有 bad (502) 属 hermes 线, caller 列 + request_id JOIN 双重铁证,
cc2 主链 0 泄漏; fallback 0 次; 无新错误类。**不改码**。

## 本轮改动
无 (NOP)。

## 依据 (live DB 30min 实拉, 一次性核对 via caller 分组 + error_type 分组 + JOIN)

### 30min caller × status (nv_requests)
```
cc4101-primary | 200 | 120      ← cc2 主链 100% SR, 0 bad
hermes         | 200 |   2
hermes         | 502 |   5      ← 全部 bad 属 hermes
```

### 30min status!=200 分组 (error_type × caller)
```
all_tiers_exhausted | hermes | 4   (avg_dur 180053ms ≈ 180s)
stream_absolute_cap | hermes | 1   (avg_dur 158341ms ≈ 158s)
```
→ 5 条 bad **全属 caller=hermes**, cc4101-primary **0 条**。

### bad request_id 级 JOIN 铁证 (nv_requests ⋈ nv_tier_attempts)
```
 056d2c5e | all_tiers_exhausted | 5 attempts | RemoteDisconnected,Timeout          | touched_glm52=f
 33516449 | all_tiers_exhausted | 4 attempts | 504_gateway_timeout,Disconnected,Timeout | f
 5d3afd42 | stream_absolute_cap | 3 attempts | RemoteDisconnected                  | f
 9b4fd536 | all_tiers_exhausted | 6 attempts | 529_overloaded,Disconnected,Timeout | f
 bfcd651d | all_tiers_exhausted | 5 attempts | RemoteDisconnected,Timeout          | f
```
→ 5 条 bad request_id 的 attempt 记录全部来自 hermes 发起的请求, 无一条属 cc2 主链。

### fallback (cc_requests 30min total=122) = 0 次

### per-key tier 错误 (nv_tier_attempts)
瞬态错误 (NVCFPexecRemoteDisconnected / NVCFPexecTimeout / 529_nv_overloaded / 504) 分散 k0~k4,
pexec_success 稳定主导 (k0:24/k1:22/k2:24/k3:23/k4:23), 被 multi-tier round-robin + func_health 健康选择吸收, 未达 cc2 全挂。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **120/120 = 100% SR, 0 bad** (实拉) | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×4 + stream_absolute_cap ×1 | ⚠️ 越界 |
| bad caller 归属 | 5 req 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| bad request_id JOIN | 5/5 条 attempt 均属 hermes 发起 (3~6 attempts), cc2 0 泄漏 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (0/122) | ✅ |
| per-key tier | pexec_success 主导, 瞬态错误被吸收 | ✅ |
| scoped health | 4101/40006/40066 全 ok (200), nv_gw Up 6h | ✅ |

## 验证
- curl 4101/40006/40066 → 全 ok; cc4101 primary=dsv4f0731_nv; nv_gw passthrough 5 keys。
- 30min nv_requests cc4101-primary 实拉 = 120/120 (0 bad)。
- 30min 所有 bad 分组 (caller 列 + request_id JOIN 双铁证): 5 条全 hermes, cc2 主链 0 bad。
- cc_requests fallback = 0 次 (0/122)。

## 下一步
- 延续 NOP 稳态。保持多 tier round-robin + func_health 健康选择自适应吸收跨 key/fid 瞬态失败。
- 持续观察 hermes 线 bad (4 条 all_tiers_exhausted 180s + 1 条 stream_absolute_cap) 是否稳定越界;
  该模式已连续多轮 (R915×3exhausted+2cap, R916×3+2, 本轮×3+1), 如需根治属 hermes 侧 (越 cc2 范围), 记录不越权改。
- 主链 SR 100% 无优化需求, 下轮继续巡检。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败
4. 坏 fid 52e1ddb6 (hermes 宿主) 与主链健康 fid 281478d0 容器+候选池双层隔离

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)