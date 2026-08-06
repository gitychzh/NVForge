# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R891 (NOP 巡检轮/不改码 — 实时 100% 干净, 但修正 R890: 兄弟坏 fid 52e1ddb6 仍被集中轮转)**
> 近 30min window SR=94.7% (200×89 + 502×4 + 499×1) 仍为 R889 簇2 尾部 (≤23:35:46 UTC);
> live 自 **23:36 UTC 起 102/102 = 100% SR** (连续 20+ min 0 bad), 系统自愈, **不改码**。
> ⚠️ 修正 R890「52e1ddb6 不再被轮转」不准确: 实拉显示 52e1ddb6 在 dsv4f0731 tier 内 30min=25/25
> 全败 (2h=91/91), 末次 23:53:27; 被 buffer 轮转吸收未影响 cc2 SR; 健康 281478d0 100% (317/317)。
> live DB now()=2026-08-06 23:56 UTC
> 上轮: R890 (NOP, 判定自愈; 本轮实拉修正其 52e1ddb6 状态记录)

## 本轮 (R891) 改动 + 依据 + 验证

### 改动: 无 (NOP。实时已自愈, 窗口数据为簇2 尾部, 无新错误类; 只修正 R890 对 52e1ddb6 的记录)

### 依据 (live DB now()=23:56 UTC)

- 30min window cc4101-primary: 200×89 + 502×4 (all_tiers_exhausted, avg 226s) + 499×1
  (client_gone_during_flush) → SR 94.7%。**全 ≤23:35:46 的簇2 尾部**, 与 R889/R890 定界一致。
- 逐分钟 chrono: 23:36:00 → 23:56:00 连续 20min 0 bad, 全 200 = 100% SR (102 请求)。
- ⚠️ **兄弟坏 fid 52e1ddb6 仍被轮转且全败**: 30min=25/25 bad, 2h=91/91 bad
  (RemoteDisconnected×15, empty_200×4, 529×3, Timeout×3; 末次 23:53:27 UTC), 均记在 dsv4f0731 tier 下。
  修正 R890「不再被轮转」—— 它**仍被集中轮转**。健康 fid 281478d0 同窗口 94/94 全 pexec_success (2h 317/317)。
- 52e1ddb6 全败被 buffer 跨候选轮转到 281478d0 吸收 → cc2 请求 SR 100% 无影响; 但浪费每次 ~30-57s
  RemoteDisconnected key 预算, 属纯浪费 + 潜在延迟风险。
- func_health HEALTH_THRESHOLD=0.10 + select_healthy(候选=[281478d0]) 不可能返回 52e1ddb6 → 注入点必在
  更上游 (多 tier/多 key 轮转 + 共享 NVCF model 串 deepseek-v4-flash 致 tier 歧义), 待下轮定位。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 末次 cc4101-primary 错误 | **23:35:46 UTC** (簇2 残尾), ~20min 前 | 已过去 |
| 自 23:36 SR (实时逐分钟 20min) | **100%** (102 全 200, 0 err) | ✅ 已自愈 |
| 30min window SR | 94.7% (89/94); 坏方全为簇2 尾 | 已知, 窗口右移将恢复 |
| 健康 fid 281478d0 | 30min 94/94 pexec_success; 2h 317/317, 0 bad | ✅ 100% 稳健 |
| 兄弟坏 fid 52e1ddb6 | 30min **25/25 全败**; 2h 91/91; 末次 23:53:27 | ⚠️ 仍被轮转 (修正 R890) |
| nv_gw 实时日志 | 全 attempt-1 成功 (1.5~19.6s), 零 exhaustion/cooldown/429 marker | ✅ 健康 |
| fallback | 0 次 | ✅ |
| 三容器 health | nv_gw / cc4101 / dsv4p_nv40066 全 ok, primary=dsv4f0731_nv, 5 keys | ✅ |

### 验证
- curl 40006/40066/4101 → 三容器 ok; nv_gw 日志全 buffer attempt-1 一次成交 (1.5~19.6s),
  零 exhaustion/cooldown/429 marker。
- 逐分钟 20min 0 bad, 与 R889/R890 定界 23:35:46 完全一致 (窗口右移尾部将滑出)。

### 关键判断
本轮窗口的失败全为 ≤23:35:46 簇2 尾部, 非新故障。实时 100% 干净 (102 全 200)。
**唯一修正**: R890「52e1ddb6 不再被轮转」不准确——它仍在 dsv4f0731 tier 内被集中轮转且 100% 失败,
但被 buffer 吸收无请求级影响。不立即 kill 的原因: 当前对 cc2 无影响 + R889 已警示过度 pin 削弱跨候选
容灾 + 需精确定位 52e1ddb6 注入路由源后数据支持才能改。不改码。

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

- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_FORCE_STREAM_UPGRADE=0, TIER_TIMEOUT_BUDGET_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, primary=dsv4f0731_nv, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (铁律4 不主动改)
- config.py: dsv4f0731_nv function_ids=[281478d0-f307-49f4-9e0f-080b63b16c47] (R-fid0731); dsv4f_nv function_ids=[52e1ddb6-c745-4802-93f5-ba012d04c336] (兄弟模型, 未动 — 但其 fid 正泄漏进 dsv4f0731 rotation)

## 下一步
- 30min 窗口右移, 簇2 尾部 (23:35:46) 自动滑出 → 下一轮 window SR 预期回 100%。
- **优先监控**: 52e1ddb6 是否继续以 ~91/2h + 全败速率被轮转; 定位其注入 dsv4f0731 rotation 的路由源
  (dsv4f_nv vs dsv4f0731_nv 共用 NVCF model 串 deepseek-v4-flash → 候选池/tier 合并?) 后,
  再评估是否从 dsv4f0731 候选剔除或单独降级惩罚(须先有数据)。
- 保持 cc4101-primary fallback=dsv4f0731_nv 不动。