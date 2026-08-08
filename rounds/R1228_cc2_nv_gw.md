# R1228 cc2 nv_gw (HM2) — semi-NOP 观察轮 (transient NVCF jitter spike)

轮次: R1228
日期: 2026-08-08 (当前轮)

## 结论

**semi-NOP 观察轮 — 不改码。** 30min cc2-primary SR 96.6% (57/59, 含 2 个真实 502 buffer_exhausted),
**低于 NOP 的 ≥99% 门槛**。但根因 = **共享 NVCF 上游瞬时连接抖动 (NVCF 侧)**,
跨 caller 相关 + 跨 key/IP 弥散, **无单一 mihomo 线路/配置可改的杠杆**。
最新 15min 已 100% self-heal (attempt 1/2 吸收)。R1207 触发条件(真实新失败+SR<99%)技术上满足,
但证据指向 NVCF-side 而非 mihomo 隧道, **不贸然改隧道** (R1077: 弥散抖动上改线路反增回归风险)。

## 30min 链路数据 (自查询, 01:40 UTC)

### 请求级 (nv_requests, caller=cc4101-primary)
- `200|57` + `502|2` (buffer_exhausted, duration 118387ms/x128169ms, error_message="last verdict: execute_failed")
  → **SR=96.6% (57/59)**。这 2 个 502 是**真实新失败** (新 request_id, 非上轮复发)。
- 最新 15min (01:23-01:35) **全 200** (35+ req), attempt-2 self-heal 生效 → 窗口滚动, 已过去。

### 失败根因 (docker logs nv_gw 铁证)
a17ed596 一个请求 3 次 attempt 全部 `Remote end closed connection without response`:
```
attempt1 k2 conn err: Remote end closed connection without response → all_keys_exhausted
attempt2 k3 conn err: ... → all_keys_exhausted
attempt3 k4 conn err: ... → AKE fail-fast(3连) → skip WaitQueue → ms_gw fallback also failed → 502
```
- 每次 attempt 失败在不同 **key** (k2→k3→k4) = 弥散, 非单一坏 key。
- ms_gw fallback 也失败才触底 (NVU_DISABLE_MS_FALLBACK=0, ms_gw 侧瞬时也不通)。

### 6h 全量失败 (跨 caller, 证实 NVCF-side)
```
22:42 had hermes 502 + 22:43 cc4101-primary 502   ← 同窗口双 caller 同挂
22:45 cc2 502  /  22:46 hermes 502                 ← 同窗口双 caller 同挂
23:04 cc2 502
01:08, 01:17 cc2 502
```
**hermes 与 cc2 在相同时间窗 (22:42-22:46) 同时失败** → 共享 NVCF 上游连接抖动, 非 cc2 路由/配置/单一隧道问题。

### per-egress-IP (6h): 全健康, 无单一差线
```
134.195.101.195 | 233 | 100.0%
134.195.101.180 | 235 |  99.6%  (1 次失败)
134.195.101.193 | 461 | 100.0%
```
### per-key (6h nv_tier_attempts): 全健康, 无单一坏 key
k0~k4 每 key 216~238 total, ok 230~235 (per-key 成功率 97~99%), 无集中失败。

### fallback
30min fallback_occurred=0 (2 个 502 是 NVCF+ms 双败后直出, 记录为 buffer_exhausted, 不触发 fallback 计数)。

## 决策与依据

**不满足 R1207 的 mihomo 排查触发执行条件** —— 触发条件: 真实新失败 + SR<99% **且** 定位到
单条 mihomo 线品质差。本 6h 数据:
- 无单条 egress IP 差 (全 ≥99.6%, 最差 180 仅 1 失败/235)
- 无单 key 差 (5 key 全健康)
- 失败 diffip/mode 弥散 (每 attempt 换 key) + 双 caller 相关
→ 这是 **NVCF 侧 (远程端) 瞬时连接抖动**, 会自愈 (最新 15min 100%)。
**在此类弥散瞬态上改 mihomo 线路或 nv_gw 参数, 无依据且可能引入回归** (R1077 铁律)。

故本轮 = **semi-NOP 观察轮**: 不改码, 如实记录 spike, 下轮若连续复发 + 单线恶化再动。

## 验证
容器 health ok (nv_gw /health: 5 keys + dsv4f0731_nv pexec, 参数无漂移; cc4101 ok)。
无改动, 无 restart。最新 15min 100% self-heal 已证链路恢复。

## 参数快照
与 R1225/R1226/R1227 完全一致 (nv_gw UPSTREAM_TIMEOUT=90, BUFFER 5×90s=450s,
NVU_DISABLE_MS_FALLBACK=0 已恢复, KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90,
TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10, dsv4f0731_nv 单模式 fid 281478d0-f307
5 key 全 bind; cc4101 PRIMARY=dsv4f0731_nv, STREAM_TOTAL_DEADLINE=470, HEADER_TIMEOUT=400)。
参数无漂移 → 非配置回归。

## 下一步
1. **维持观察, 不改码**。下轮先看 30min 是否仍含 502 → 若连续 >1 轮出现真实 502
   (非 self-heal) + 集中在单条 egress IP/key → 再拉 mihomo 隧道线路质量逐线排查。
2. 持续关注 ms_gw fallback: 本轮 2 次 buffer_exhausted 时 ms_gw fallback 也失败 (双败)。
   若 cc2 请求持续在 NVCF 抖动时 ms_gw 也不通, 需评估 (但 ms_gw 已恢复启用, 非本轮改动范围)。
3. 跟踪 `Remote end closed connection without response` 触发频率: 若从弥散瞬态转为
   持续多 key 连续失败 (AKE fail-fast 频繁), 再深入 NVCF 侧 (fid 健康/换 pos 备用) 排查。
