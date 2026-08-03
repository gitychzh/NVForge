# R1006: 清空 dsv4p_nv integrate 路径 (NV_KEY_INTEGRATE_KEYS)

**日期**: 2026-08-03  
**容器**: dsv4p_nv40066 (port 40066, DeepSeek V4 Pro via NVCF)  
**主机**: HM2 (opc2sname)

## 修改

| 参数 | 旧值 | 新值 | 生效方式 |
|------|------|------|---------|
| `NV_KEY_INTEGRATE_KEYS` | `dsv4p_nv:3` | `(空)` | docker compose up -d (recreate) |

## 依据

### 30min 窗口 (采集时)
- 总请求: 68, 成功: 59, SR=86.8% (请求级)
- **tier_attempts 显示全部 28 次尝试均失败**:
  - `nv_integrate` k2: 21 次, **0% SR**
    - `IntegrateRemoteDisconnected`: 20 次 (avg 46,869ms)
    - `429_integrate_rate_limit`: 1 次
  - `nvcf_pexec`: 7 次, **0% SR**
    - `NVCFPexecRemoteDisconnected`: 7 次 (avg 32,013ms)
    - `429_nv_rate_limit`: 1 次
    - `NVCFPexecTimeout`: 1 次 (90,455ms)

### 6h 趋势 (integrate 路径)
- `nv_integrate` 总计 42 次, **0% SR**
  - `IntegrateRemoteDisconnected`: 27 次 (avg 48,585ms)
  - `429_integrate_rate_limit`: 12 次
- `nvcf_pexec` 总计 97 次, 0% SR (但请求级 SR=92.5% = 764/826, 说明 pexec tier_attempts 记录的是失败重试, 成功请求不在此表)

### 根因分析
- `NV_KEY_INTEGRATE_KEYS=dsv4p_nv:3` 指定 key3 (1-based = key_idx 2, 0-based) 走 integrate.api 路径
- integrate 路径 6h 内 **0% 成功率** (42 次全失败), 原因:
  1. `IntegrateRemoteDisconnected` (27次): integrate.api.nvidia.com 远程断连, avg 48s — 接近 UPSTREAM_TIMEOUT=90 但先被远端断开
  2. `429_integrate_rate_limit` (12次): key3 上的 integrate 路径限流
- key3 走 integrate 全部失败后回退到 pexec, 但此过程浪费 ~48s (integrate 超时) + key cooldown 时间
- 5-key pool 实质只有 4 key 有效 (k3 的 integrate lane 完全失效)

### 与 nv_gw R2057 对齐
nv_gw 容器在 R2057 (hermes2 R5) 已清空 `NV_KEY_INTEGRATE_KEYS` — 同样发现 dsv4p_nv integrate lane 每次 429, 浪费 3.2s+90s cooldown, 5-key pool 变 4-key. 本次变更使 dsv4p_nv40066 与 nv_gw 保持一致策略: dsv4p_nv **全走 pexec DIRECT**.

## 预期效果
1. 消除 integrate 路径的 0% SR 浪费 (6h 内 42 次全失败的无效尝试)
2. k3 回归 pexec RR 轮转, 5-key pool 恢复完整
3. 减少 `IntegrateRemoteDisconnected` 错误 (当前 30min 占 33% 错误)
4. 减少 `all_tiers_exhausted` (由 integrate 浪费 budget 引起的 tier 耗尽)
5. 请求级 SR 从 86.8% → 预期 >95% (消除 integrate 失败的拖累)

## 验证
- `/health`: OK (status=ok, nv_num_keys=5, port=40066)
- `NV_KEY_INTEGRATE_KEYS=` 确认已清空
- 容器状态: Up, recreate 成功

## 下一步
- 下轮验证: 确认 integrate 错误归零, pexec SR 是否提升
- 关注: `NVCFPexecRemoteDisconnected` 是否仍存在 (可能是 NVCF 端问题)
- 若 pexec SR 恢复正常, 考虑降低 `UPSTREAM_TIMEOUT` (当前 90s 过高, NVCFPexecTimeout 的 90,455ms 说明有死连接)
