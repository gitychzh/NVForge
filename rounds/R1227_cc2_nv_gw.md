# R1227 cc2 nv_gw (HM2) — NOP 巡检轮

轮次: R1227
日期: 2026-08-08 (当前轮)

## 结论

**NOP — SR 100%, 0 请求级错误, fallback 0%, 连续第 7 轮全绿洁净。**

## 30min 链路数据 (轮前注入 + 自查询 09:20 CST)

### 请求级 (nv_requests)
- `cc4101-primary|dsv4f0731_nv|200|97` → cc2 专属 **SR=100% (97/97)** (较上轮 R1226 的 100 微降, 正常流量波动)
- `hermes|dsv4f0731_nv|200|55` → 全量 **dsv4f0731_nv SR=100% (152/152)**

### 错误分类 (status!=200)
- **空 (0 rows)** → 无 buffer_exhausted / stream_total_deadline / 4xx / 5xx / 其他请求级错误。

### tier 错误 (nv_tier_attempts) — 瞬时, attempt 已吸收
```
nv_key_idx | error_type                | count
0          | pexec_success             | 21
1          | NVCFPexecRemoteDisconnected | 1
1          | pexec_success             | 17
2          | NVCFPexecTimeout          | 1
2          | pexec_success             | 19
3          | NVCFPexecTimeout          | 2
3          | pexec_success             | 21
4          | pexec_success             | 19
```
- 3 次瞬时 egress 抖动 (key1 RemoteDisconnected×1, key2+key3 Timeout×3) 均被后续 attempt success 吸收,
  最终请求全 200 (SR=100%)。符合 R1077 self-heal / transient egress 模式, **非真实新失败**。
- 无连续复发 (非上轮 request_id), 无需查 mihomo 线路。

### buffer 日志 (docker logs nv_gw --since 30m)
- 全 `NV-BUFFER-SUCCESS ... after 1 attempt(s)`, elapsed 2-14s, verdict 全 success_text / success_tool_call。
- 0 退回 / 0 惩罚 / 0 阻塞 / 0 attempt≥2。

### fallback
- 0% (97/97 cc2-primary 全 200, 无 fallback_triggered)。

### 容器健康 + 参数无漂移
- `nv_gw /health`: ok, 5 keys, pexec_models 含 dsv4f0731_nv, port 40006。
- `cc4101 /health`: ok, primary=dsv4f0731_nv, port 4101。
- 参数快照与 R1225/R1226 一致 → 非配置回归。

### mihomo 升级监控触发条件 (R1206/R1207 收紧) 判定
- 无真实新失败 (SR=100%) + SR ≥ 99% → **条件不满足, 延后**。
- 触发条件: 后续轮次出现 **真实新失败 (非上轮 request_id) + SR<99%** 才拉 mihomo 隧道线路排查。

## 依据
- 铁律 1 (改前有数据): 已核 30min 全量数据, SR=100%, 0 请求级错误。
- 铁律 5 (写入仓库): 本文件 + STATE.md 镜像 + commit + push。
- NOP 判定标准 (每轮工作流步骤 2): nv_gw SR ≥ 99% 且无新错误 → NOP。

## 改动
**无 (NOP)。** 无改码条件 — SR=100%, 0 错误, fallback 0%, 全 attempt=1, 参数无漂移。

## 验证
30min cc2-primary 97/97 (0 错误), 全量 152/152, fallback 0%, buffer 全 attempt=1 success。
仅 3 次 tier 瞬时抖动 (RemoteDisconnected×1 + Timeout×3) 被 attempt success 吸收, 请求级全 200。
容器 health ok、参数无漂移。→ 无改码条件, NOP。

## 参数快照 (与 R1226 一致)
见 STATE.md 参数快照段 (nv_gw/cc4101 全量 env 快照)。

## 下一步
维持静稳观察。mihomo 升级监控触发条件沿用 R1206/R1207 收紧版: 真实新失败 + SR<99% → 拉 mihomo
隧道线路。持续观察 k3 SSLEOFError 不复发 (已 7+ 轮), 若连续复发查 k3 mihomo 7896。