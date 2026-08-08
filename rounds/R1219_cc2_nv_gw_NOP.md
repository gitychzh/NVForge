# R1219 cc2 nv_gw — NOP 巡检轮

> 日期: 2026-08-08 CST  |  主链 fid: **281478d0-f307**  |  容器: nv_gw Up 29h, cc4101 Up 28h

## 结论
**NOP** — SR=100%（84/84），请求级 0 错误，fallback 0%，per-key 全 pexec_success。无改码条件。

## 数据（活查 30min + 轮前注入链路分析）

### 30min 链路总览 (caller × model × status)
```
cc4101-primary|dsv4f0731_nv|200|84      (cc2 primary 链路)
hermes|dsv4f0731_nv|200|70
```

### 30min 按模型成功率
dsv4f0731_nv  SR=100.0% (154/154)

### 30min cc2-primary 专属
200|84|13074|   → 全 200，平均耗时 ~13s

### 30min 错误分类
(空 — 无 buffer_exhausted / stream_total_deadline / 502 / 其他)

### fallback 发生率
0 / 84 = **0%**

### 30min nv_tier_attempts per-key 错误分布
```
0|pexec_success|17
1|pexec_success|17
2|pexec_success|15
3|pexec_success|16
4|pexec_success|19
```
→ 全 key 整窗 clean，无 execute_failed / RemoteDisconnected / 429。

### nv_gw buffer/wait/keymanager 日志
(无 buffer/wait/keymanager 相关日志 — 请求均在 attempt=1 直接成功)

### 容器健康
- nv_gw /health ok（5 keys + pexec_models 含 dsv4f0731_nv, fid 281478d0-f307）
- cc4101 /health ok（primary=dsv4f0731_nv）
- 容器 up 状态: nv_gw 29h, cc4101 28h, ms_gw 3d, logs_db 8d
- 参数无漂移（与 R1218 一致）→ 非配置回归

## 本轮改动
无（NOP 巡检轮。SR 100% + 0 请求级错误，mihomo 升级监控条件不触发，不改码不查 mihomo）。

## 依据
- 30min cc2-primary 84/84 SR=100%，0 错误，fallback 0%，per-key 全 pexec_success。
- mihomo 升级监控触发条件（R1206/R1207 收紧: **真实新失败（非上轮 request_id）+ SR<99%**）不满足 → mihomo 隧道检查继续延后。

## 验证
活查 30min：84/84 200，error_type 空，fallback 0/84；容器 health ok、参数无漂移。
→ 无改码条件，NOP。

## 下一步
维持静稳观察。mihomo 升级监控触发条件（R1206/R1207 收紧）: 若 **后续轮次出现真实新失败（非上轮 request_id）+ SR<99%** → 拉 mihomo 隧道线路质量（各 egress_ip 失败率、隧道状态、带宽/超时）、逐关键链路排查并小步优化。