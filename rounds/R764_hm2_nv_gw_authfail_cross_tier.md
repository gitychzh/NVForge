# R764: HM2 nv_gw auth-fail (401/403) 改 per-key 跨 tier cooldown

> R762 把 401/403 加入 should_cycle, 但 cooldown 仍是 per-(tier,key) → k3 在 dsv4p_nv
> 标 cooldown 后, glm5_2_nv 还会试 k3, 失败, 再标一次. 每个 tier 都要独立踩 k3 的 403 坑.
> 修复: 独立 per-key (跨 tier) auth-fail map, 一次 403 全 tier 跳过.

## 改前数据 (10min)

### k3 在多个 tier 被重复 attempt
```
01:57:42 [NV-AUTH-FAIL] tier=dsv4p_nv k3 403 → cooling, cycling
02:00:08 [NV-AUTH-FAIL] tier=glm5_2_nv k3 403 → cooling, cycling  (重复踩)
02:01:28 [NV-AUTH-FAIL] tier=glm5_2_nv k3 403 → cooling, cycling  (再次)
```
根因: cooldown.py _key_cooldown_map key=(tier_model, key_idx) → per-tier 独立.
k3 的 403 是 NVAPI key 本身失效 (跨所有 tier), 但 cooldown 不跨 tier.

### 浪费
每个 tier 首次试 k3 → 403 (~1s + 1次请求) → 才标 cooldown.
HM2 有 3 个 NV model (dsv4p/glm5_2/kimi), k3 失效 → 3 次踩坑 = 3s + 3 请求.

## 改动

### cooldown.py: 新增 per-key (跨 tier) auth-fail 状态机
| 函数 | 作用 |
|---|---|
| `is_key_auth_failed(key_idx)` | 检查某 key 是否 auth-fail (跨所有 tier) |
| `mark_key_auth_failed(key_idx)` | 标记某 key auth-fail (跨所有 tier) |
| `KEY_AUTHFAIL_COOLDOWN_S` | 默认 600s (10min, auth 失效不自愈, 远长于 429 的 15s) |

独立 map `_key_authfail_map[key_idx] = expiry`, 不影响现有 429 per-(tier,key) cooldown.

### config.py: re-export 新函数
### upstream.py: 3 处改动
1. import is_key_auth_failed, mark_key_auth_failed
2. pexec 401/403 分支: mark_key_auth_failed(key_idx) + mark_key_cooling(tier, key)
3. integrate 401/403 分支: 同上
4. pexec + integrate is_key_cooling 检查点: 加 `or is_key_auth_failed(key_idx)` → 跳过

### 逻辑
- 401/403 命中 → 同时标 per-tier cooldown (15s, 原有) + per-key auth-fail (600s, 新)
- 后续任何 tier 试该 key → is_key_auth_failed 直接 skip, 不发请求
- 600s 后过期重试 (key 可能被平台恢复, 虽然概率低)

### 不改
- 429 cooldown 逻辑 (per-tier 仍保留, 429 是 per-tier 限流)
- nv_gw/ms_gw 其他逻辑 (模块化)
- HM1 (冻结)
- 41xx 适配器 (不受影响)

## 改后验证

### 6 请求 (3 dsv4p + 3 glm5_2) 全 200 OK
```
dsv4p req1: 200 1.1s, req2: 200 21.4s, req3: 200 6.0s
glm5_2 req1: 200 17.8s, req2: 200 15.4s, req3: 200 18.6s
```

### k3 跨 tier 被 skip
```
02:06:22 [NV-AUTH-FAIL] tier=glm5_2_nv k3 403 → marked cooling + auth-fail (cross-tier)
02:07:10 [NV-KEY] tier=dsv4p_nv k3 is in cooldown/auth-failed, skipping    ← 跨 tier 生效!
02:07:56 [NV-KEY] tier=glm5_2_nv k3 is in cooldown/auth-failed, skipping
```
glm5_2_nv 标记后, dsv4p_nv 也直接 skip k3 (不再发请求). k3 不再被 attempt.

## 预期
- k3 失效: 每个 tier 踩 1 次坑 (首次) → 之后 600s 内全 tier skip
- 省: (3 tier - 1) × (1s + 1请求) = 2s + 2 请求 / 10min 周期
- dsv4p_nv/glm5_2_nv/kimi_nv 三 tier 共享 k3 auth-fail 状态

## 风险
- 低: auth-fail 600s 远长于 429 的 15s, 但 auth 失效确实不自愈
- 误判恢复: 若 key 被平台恢复, 600s 后自动重试 (可接受)
- 回滚: cooldown.py.bak.R764, upstream.py.bak.R762

## 遗留
- k3 NVAPI key 仍需用户更换 (R762/R764 已最大化隔离其影响)
- HM1 同步待授权 (HM1 k3 可能也失效)
- ms_gw stream_no_data cycle (非阻塞)
