# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R890 (NOP 巡检轮/不改码 — R889 同源第二波尾部滑窗, 实时 100% 干净)**
> 近 30min 窗口 SR=92.3% (200×72 + 502×5 + 499×1) 并非新故障, 而是 R889 所定第二波簇2
> (23:14–23:35 UTC 上游 NVCF 降级 + 兄弟坏 fid 52e1ddb6) 的**窗口尾界**; live 末次错误=
> 23:35:46 UTC, 自 **23:36 UTC 起逐分钟 0 bad** (连续 15+ min 全 200 = **100% SR**), 系统已自愈,
> **不改码**; live DB now()=2026-08-06 23:50 UTC
> 上轮: R889 (实时实拉修正定界, 发现第二波 23:14-23:35; 本轮 30min 窗口正好覆盖该波尾部)

## 本轮 (R890) 改动 + 依据 + 验证

### 改动: 无 (NOP。实时已自愈, 窗口数据为簇2 尾部, 无新错误类)

### 依据 (live DB now()=23:50 UTC)

- 30min window cc4101-primary: 200×72 + 502×5 (all_tiers_exhausted;buffer_exhausted, avg 226s) + 499×1
  (client_gone_during_flush) → SR 92.3%。**全 ≤23:35:46 的簇2 尾部**, 与 R889 定界一致。
- 逐分钟 chrono: 23:36:00 起 → 23:50:00 连续 15min 0 bad, 全 200 = 100% SR (78 请求)。
- nv_gw 30min 日志: 全 buffer attempt-1 SUCCESS (6~12s direct flush), 零 cooldown/429/exhaustion/52e1ddb6。
- per-key pexec_success 为主, RemoteDisconnected/Timeout/529/empty_200 均匀分布 → 轮转机制正常吸收。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 末次 cc4101-primary 错误 | **23:35:46 UTC** (簇2 残尾), ~15min 前 | 已过去 |
| 自 23:36 SR (实时逐分钟) | **100%** (15min, 78 全 200, 0 err) | ✅ 已自愈 |
| 30min window SR | 92.3% (72/78); 坏方全为簇2 尾 | 已知, 窗口右移将恢复 |
| fid 分布 | 281478d0 pexec_success 主导; 52e1ddb6 不再被轮转 | ✅ 已锁健康 fid |
| nv_gw 实时日志 | 全 attempt-1 成功 (6~12s), 零 exhaustion/cooldown/429 | ✅ 健康 |
| fallback | 0 次 | ✅ |
| 三容器 health | nv_gw / cc4101 / dsv4p_nv40066 全 ok, primary=dsv4f0731_nv, 5 keys | ✅ |

### 验证
- curl 40006/40066/4101 → 三容器 ok; nv_gw 日志零 exhaustion/cooldown/52e1ddb6 marker。
- 逐分钟 15min 0 bad, 与 R889 定界 23:35:46 完全一致。

### 关键判断
本轮窗口的 502/all_tiers_exhausted 全部落在 ≤23:35:46 的簇2 尾部 (R889 已定界: 上游 NVCF 瞬态 +
func_health 对兄弟坏 fid 52e1ddb6 的正常过滤), 非新故障。实时自 23:36 起 100% 干净, 无新持久错误类。
对已自愈态过度 pin 会削弱跨候选容灾, 数据不足, 不改码。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功, 用户无感知
3. 多 tier round-robin (dsv4p/dsv4f/dsv4f0731/glm5_2_nv) + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)
- `docker ps` → nv_gw / cc4101 / dsv4p_nv40066 全 Up ✅

## 参数快照 (env, 本轮未改; R-fid0731 已于 08-07 03:28 CST 容器重启加载)

- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_FORCE_STREAM_UPGRADE=0, TIER_TIMEOUT_BUDGET_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, primary=dsv4f0731_nv, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (铁律4 不主动改)
- config.py: dsv4f0731_nv function_ids=[281478d0-f307-49f4-9e0f-080b63b16c47] (R-fid0731); dsv4f_nv function_ids=[52e1ddb6-...] (兄弟模型, 未动)

## 下一步
- 30min 窗口右移, 簇2 尾部 (23:35:46) 自动滑出 → 下一轮 window SR 预期回 100%。
- 监控 52e1ddb6 是否再被轮转且集中失败; 281478d0 SR 稳定性 (当前 100% @540)。
- 保持 cc4101-primary fallback=dsv4f0731_nv 不动。