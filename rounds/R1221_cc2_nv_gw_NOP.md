# R1221 cc2 nv_gw — NOP 巡检轮

> 日期: 2026-08-08 CST  |  主链 fid: **281478d0-f307**  |  容器: nv_gw Up 29h, cc4101 Up 29h, ms_gw Up 3d

## 结论
**NOP** — SR=100%（81/81 cc2-primary），请求级 0 错误，fallback 0%，per-key 全 pexec_success。无改码条件。
唯一事件: 1 请求 (00a20c6d) k3 SSLEOFError attempt1 → 5s backoff → attempt2 success_tool_call 自愈，成功非回归。

## 数据（活查 30min + 轮前注入链路分析）

### 30min 链路总览 (caller × model × status)
```
cc4101-primary|dsv4f0731_nv|200|81      (cc2 primary 链路, 活查确认)
hermes|dsv4f0731_nv|200|70
```

### 30min 按模型成功率
dsv4f0731_nv  SR=100.0% (151/151)

### 30min cc2-primary 专属
200|81|12633|   → 全 200，平均耗时 ~12.6s

### 30min 错误分类
(空 — 无 buffer_exhausted / stream_total_deadline / 502 / 其他; 请求级 status!=200 0 rows)

### fallback 发生率
老列 (fallback_triggered): 0/81 → 0%

### 30min nv_tier_attempts per-key 错误分布
```
k0|pexec_success|17   k1|pexec_success|16
k2|pexec_success|13   k3|pexec_success|18   k4|pexec_success|17
```
全部 bind fid 281478d0-f307 (nvcf_pexec)，无任何 attempt 级错误。

### 30min nv_gw buffer/keymanager 日志摘要 (关键行)
```
[NV-BUFFER-SUCCESS] req=108d9635 flushed 1757b after 1 attempt, elapsed=1287ms
[NV-KEYMGR] transport_err tier=dsv4f0731_nv k3 type=SSLEOFError penalty=10s (no conn_count)
[NV-BUFFER-EXEC-FAIL] req=00a20c6d attempt1 fail key=k3 all_keys_exhausted=True
[NV-BUFFER-BACKOFF] backing off 5s before attempt 2
[NV-BUFFER-ATTEMPT] req=00a20c6d attempt=2/5 timeout=90s
[NV-BUFFER-SUCCESS] req=00a20c6d flushed 1613b after 2 attempt(s), elapsed=52697ms
[NV-BUFFER-SUCCESS] req=eb86623e / c2d3084d 均 1 attempt success_tool_call
```
→ 单 k3 SSLEOFError 瞬时 egress 抖动 (R1077 已知自愈模式)，Buffer 5s backoff attempt2 补刀成功,
最终请求仍 success。无 WAIT- 阻塞, 无 buffer_exhausted, 无 multi-attempt 连续失败, 无对用户可见错误。

## 判稳依据
- SR=100% (81/81) ≥ 99% 阈值
- 请求级 0 错误, fallback 0%
- 唯一 k3 SSLEOFError 为瞬时 attempt-level 抖动, request_id 00a20c6d 最终 200 自愈,
  非用户可见净新增, 属已知 self-heal 带内。
- **mihomo 升级监控触发条件 (R1206/R1207)**: 需"真实新失败 (非上轮 request_id) + SR<99%" —
  本轮无真实新失败 + SR=100% → 条件不满足, mihomo 隧道检查继续延后。

## 容器健康
nv_gw /health ok (5 keys, pexec_models 含 dsv4f0731_nv, fid 281478d0-f307),
cc4101 ok (Up 29h), ms_gw ok (Up 3d), nv_gw_stable Up 6d。参数与 R1220 一致 → 非配置回归。
NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 保持启用), 但 fallback 0% 实际不触发。

## 下一步
维持静稳观察。**mihomo 升级监控触发条件维持**: 后续轮次若出现真实新失败 (非上轮 request_id)
+ SR<99% → 拉 mihomo 隧道线路质量 (各 egress_ip 失败率、隧道状态、带宽/超时)、逐关键链路排查。
持续观察 k3 SSLEOFError 是否为离散瞬时 (本轮单例已自愈) 或连续复发 (连续复发须关注 7896 线路)。