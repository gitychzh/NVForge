# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R889 (NOP 巡检轮/不改码 — 实时实拉确证新判断)** 近 30min 窗口 SR 未见干净 (因窗口含簇2尾部),
> 但**实时态 100% 干净**; 本轮**修正 R885-888 的"末次错误=22:44, 此后再无错误"定界** — 实拉发现
> **第二波 NVCF 降级 (23:14–23:35 UTC)**, 末次 cc4101-primary 错误 = **23:35:46 UTC**, 此后 ~4.5min
> (23:36→23:40 UTC) 连续 17~28 条全 200 = **100% SR**, 全 fid=281478d0, buffer attempt-1 一次成交 (5~19s),
> 无 cooldown/429/transport 错误, 系统自愈锁定健康 fid, **不改码**; live DB now()=2026-08-07 07:40 CST (=23:40 UTC))
> 上轮: R888 (NOP — 误将末次错误定界为 22:44, 遗漏 23:14-23:35 第二波; 本轮以实时实拉修正)

## 本轮 (R889) 改动 + 依据 + 验证

### 改动: 无 (实时自愈; 第二波为上游 NVCF 瞬态 + func_health 被动健康降级对兄弟 fid 52e1ddb6 的正常过滤, 已锁健康 281478d0, 非 our-side 配置缺陷)

### 本轮关键修正: 前几轮定界 22:44 只覆盖簇1, 实拉命中有第二波簇2 (23:14-23:35)

R885-888 均记"末次错误=22:44:47 UTC, 自此 100% 干净"。**本轮实时实拉 (非窗口尾界推断) 证实**: 22:44 后
还有**第二个 NVCF 降级波 (23:14–23:35 UTC)** — all_tiers_exhausted ×5 + buffer_exhausted ×3 +
client_gone_during_flush ×1。其病根为 dsv4f0731_nv tier 在 23:14-23:33 窗口间歇命中**兄弟坏 fid `52e1ddb6`**
(ai-deepseek-v4-flash, 即 dsv4f_nv 的 fid; 50min 内 ~48 失败, 0% SR)。23:34 UTC 后 52e1ddb6 不再被轮转,
gateway 锁定健康 `281478d0` (100% SR, 540/540@3h), 实时彻底自愈。

### 本轮数据 (live DB now()=2026-08-07 07:40 CST, UTC=23:40)

| 指标 | 值 | 状态 |
|---|---|---|
| **末次 cc4101-primary 错误** | **23:35:46 UTC** (`client_gone_during_flush`, 簇2 残尾), 4.8min 前 | 已过去 |
| **自末次错误 SR (真实当前态)** | **100% (17~28 连续 200)** — 23:37:26→23:40:15 实时 chrono 17/17, 全 fid=281478d0 | ✅ 已自愈 |
| **primary 目标 tier** | **dsv4f0731_nv** (fid=281478d0, 100% SR 540/540), 单次 5~13s | ✅ |
| **错误分类 (cc4101-primary, 近3h)** | 簇1 (22:16-22:44) all_tiers_exhausted/buffer_exhausted + 簇2 (23:14-23:35) all_tiers_exhausted ×5, buffer_exhausted ×3, client_gone_during_flush ×1 | 已知类+1 残尾, 无新持续缺陷 |
| **fallback 触发** | 实时无 fallback 触发 (`f|57` 为总请求计数行, 非 fallback 数) | ✅ |
| **fid 分布 (dsv4f0731_nv, 50min)** | 281478d0: pexec_success ×135 (全 key); 52e1ddb6: ~48 失败 (529×10/RemoteDisc×28/Timeout×9/empty200×3), 末次 23:33, 此后下线 | ✅ 已锁 281478d0 |
| **nv_gw 实时日志 (07:36→07:40 CST)** | 全 NV-GLM52-ATTEMPT tier=dsv4f0731_nv fid=281478d0, buffer 全 attempt-1 SUCCESS (5~19s), 零 52e1ddb6/cooldown/exhaustion | ✅ 健康 |
| **hermes (外部 cron)** | 数条 502 all_tiers_exhausted (avg ~159s) — 已知独立 caller 模式, 与 cc2 路径无关 | ⚠️ 已知 |
| **三容器 health** | nv_gw / cc4101 / dsv4p_nv40066 均 ok, cc4101 primary=dsv4f0731_nv, 5 keys | ✅ |

### 关键判断: 实时已 100% 干净, 无需改码

- live DB `now()`=23:40 UTC; 末次 cc4101-primary 错误=23:35:46 UTC。
- 自 23:35:46 后连续 17~28 条 200 (chrono 实拉), 全 fid=281478d0, buffer attempt-1 (5~19s) 直接 flush。
- nv_gw 实时日志零 52e1ddb6、零 cooldown/429/transport marker, 系统已锁健康 fid。
- 簇2 根因为 **NVCF 上游瞬态 (281478d0 短暂降级时轮转试到兄弟坏 fid 52e1ddb6)**, func_health 被动健康降级
  正常过滤 (自 23:34 起不再轮转 52e1ddb6)。这是上游瞬态 + 轮转机制按设计工作, 非 our-side 配置缺陷。
- 无新持久错误类, 无进行中降级; 对已自愈状态做 pin 收紧属过度收紧 (会削弱跨候选容灾), 数据不足, 不改码。

## 修复链 (沿用, R827+R828+R829+R833+R813)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功, 用户无感知
3. 多 tier round-robin (dsv4p/dsv4f/dsv4f0731/glm5_2_nv) + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys, dsv4f0731_nv 在列)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)
- `docker ps` → nv_gw / cc4101 / dsv4p_nv40066 全 Up ✅

## 参数快照 (env, 本轮未改; R-fid0731 已于 08-07 03:28 CST 容器重启加载)

- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_FORCE_STREAM_UPGRADE=0, TIER_TIMEOUT_BUDGET_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, primary=dsv4f0731_nv, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (铁律4 不主动改)
- config.py: dsv4f0731_nv function_ids=[281478d0-f307-49f4-9e0f-080b63b16c47] (R-fid0731); dsv4f_nv function_ids=[52e1ddb6-...] (兄弟模型, 未动)

## 下一步
- 30min 窗口右移, 簇2 尾部 (23:35:46) 自动滑出 → 下一轮 window SR 预期回 100%。
- 监控 `52e1ddb6` 是否再被轮转且集中失败; 281478d0 SR 是否稳定 (当前 100% @540)。
- 保持 cc4101-primary fallback=dsv4f0731_nv 不动。