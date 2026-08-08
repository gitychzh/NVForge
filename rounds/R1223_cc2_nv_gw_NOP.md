# R1223 cc2 nv_gw — NOP 巡检轮

> 日期: 2026-08-08 CST  |  主链 fid: **281478d0-f307**  |  容器: nv_gw Up 29h, cc4101 Up 29h, nv_gw_stable Up 6d

## 结论
**NOP** — SR=100%（89/89 cc2-primary），请求级 0 错误，fallback 0%，per-key 全 pexec_success。无改码条件。
本轮 0 异常: 无 SSLEOFError、无 multi-attempt、无 KEYMGR 惩罚、无 WAIT- 阻塞。R1222 洁净态延续（连续第 3 轮全绿）。

## 数据（轮前注入链路分析，2026-08-08 08:41 CST）

### 30min 链路总览 (caller × model × status)
```
cc4101-primary|dsv4f0731_nv|200|89      (cc2 primary 链路, 较 R1222 的 83 微增)
hermes|dsv4f0731_nv|200|70
```

### 30min 按模型成功率
dsv4f0731_nv  SR=100.0% (159/159)

### 30min cc2-primary 专属
200|89  → 全 200 (89/89 SR 100%)

### 30min 错误分类
(空 — 无 buffer_exhausted / stream_total_deadline / 502 / 其他; 请求级 status!=200 0 rows)

### fallback 发生率
0 (158 请求 0 fallback_triggered)

### 30min nv_tier_attempts per-key 错误分布
```
k0|pexec_success|19   k1|pexec_success|18
k2|pexec_success|16   k3|pexec_success|18   k4|pexec_success|17
```
全部 bind fid 281478d0-f307 (nvcf_pexec)，无任何 attempt 级错误。

### 30min nv_gw buffer/wait/keymanager 日志
(空 — 无 BUFFER-/WAIT-/KEYMGR 错误行，即所有请求 attempt=1 直接 success，无退回/惩罚)

## 判稳
SR=100% ≥ 99% 且 0 新错误 + fallback 0% → **无改码条件，NOP**。
- k3 持续 pexec_success，R1205/R1206 的 k3 SSLEOFError 已连续多轮消散，mihomo 7896 无忧。
- mihomo 升级监控触发条件（真实新失败 + SR<99%）未满足，隧道检查继续延后。

## 验证
容器: nv_gw /health ok（5 keys + pexec_models 含 dsv4f0731_nv, fid 281478d0-f307），cc4101 ok。
容器 up: nv_gw 29h, cc4101 29h, nv_gw_stable 6d — 持续稳定无重启。参数与 R1222 一致，非配置回归。

## 下一步
维持静稳观察，无需动作。**mihomo 升级监控触发条件**: 若 **后续轮次出现真实新失败 + SR<99%**
→ 拉 mihomo 隧道线路质量（各 egress_ip 失败率、隧道状态、带宽/超时）、逐关键链路排查并小步优化。
持续观察 k3 SSLEOFError 不复发（目前连续多轮 0）; 若连续复发 → 查 k3 mihomo 7896 线路。
