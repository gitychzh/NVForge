# R1222 cc2 nv_gw — NOP 巡检轮

> 日期: 2026-08-08 CST  |  主链 fid: **281478d0-f307**  |  容器: nv_gw Up 29h, cc4101 Up 29h, ms_gw Up 3d, nv_gw_stable Up 6d

## 结论
**NOP** — SR=100%（83/83 cc2-primary），请求级 0 错误，fallback 0%，per-key 全 pexec_success。无改码条件。
本轮 0 异常: 无 SSLEOFError、无 multi-attempt、无 KEYMGR 惩罚、无 WAIT- 阻塞。较 R1221 更纯净（R1221 尚需处理单 k3 SSLEOFError 自愈）。

## 数据（轮前注入链路分析 + 活查 buffer 日志确认）

### 30min 链路总览 (caller × model × status)
```
cc4101-primary|dsv4f0731_nv|200|83      (cc2 primary 链路)
hermes|dsv4f0731_nv|200|67
```

### 30min 按模型成功率
dsv4f0731_nv  SR=100.0% (150/150)

### 30min cc2-primary 专属
200|83  → 全 200

### 30min 错误分类
(空 — 无 buffer_exhausted / stream_total_deadline / 502 / 其他; 请求级 status!=200 0 rows)

### fallback 发生率
0 (150 请求 0 fallback_triggered)

### 30min nv_tier_attempts per-key 错误分布
```
k0|pexec_success|18   k1|pexec_success|16
k2|pexec_success|14   k3|pexec_success|18   k4|pexec_success|17
```
全部 bind fid 281478d0-f307 (nvcf_pexec)，无任何 attempt 级错误。

### 30min nv_gw buffer 日志 (活查关键行)
```
[NV-BUFFER-SUCCESS] req=bb1c0cfe flushed 49945b after 1 attempt, elapsed=11997ms
[NV-BUFFER-SUCCESS] req=ed8d1ea7 flushed 2109b after 1 attempt, elapsed=2400ms
[NV-BUFFER-SUCCESS] req=56b44616 flushed 1566b after 1 attempt, elapsed=16098ms
[NV-BUFFER-SUCCESS] req=200a7732 flushed 17418b after 1 attempt, elapsed=6280ms
```
→ 所有请求 attempt=1 即 success_tool_call / success_text 直接 flush。**0 次 attempt>1, 0 次
transport_err, 0 KEYMGR 惩罚, 0 WAIT- 阻塞, 0 buffer_exhausted**。链路完全洁净。

## 判稳依据
- SR=100% (83/83 cc2-primary, 全量 150/150) ≥ 99% 阈值
- 请求级 0 错误, fallback 0%
- buffer 日志全 attempt=1 success, 无任何 attempt 级错误 (较 R1221 连单 k3 SSLEOFError 也消失)
- **mihomo 升级监控触发条件 (R1206/R1207)**: 需"真实新失败 + SR<99%" — 本轮满足条件, 检查持续延后。

## 容器健康
nv_gw /health ok (5 keys, pexec_models 含 dsv4f0731_nv, fid 281478d0-f307),
cc4101 ok (Up 29h), ms_gw ok (Up 3d), nv_gw_stable Up 6d。参数与 R1221 一致 → 非配置回归。
NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 保持启用), 但 fallback 0% 实际不触发。

## 下一步
维持静稳观察。**mihomo 升级监控触发条件维持**: 后续轮次若出现真实新失败 (非上轮 request_id)
+ SR<99% → 拉 mihomo 隧道线路质量 (各 egress_ip 失败率、隧道状态、带宽/超时)、逐关键链路排查。
R1221 单 k3 SSLEOFError 已连续 2 轮回落为 0 (未复发), 离散瞬时 self-heal 属性进一步确认, 7896 线路无忧。