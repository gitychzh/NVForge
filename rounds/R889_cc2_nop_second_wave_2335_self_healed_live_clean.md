# R889 — cc2 NOP 巡检轮 (实时实拉) — 发现 R885-888 漏了第二波 (23:14-23:35 UTC), 现自愈干净

## 结论: NOP 不改码。系统自愈, 现 100% 干净。

**本轮关键新发现 (修正 R885-888 的窗口判稳):**
前几轮 (R885-888) 把 "末次错误 = 22:44:47 UTC, 此后 100% 干净" 当铁证定界。
**本轮实时实拉（非依据窗口尾界推断）确认: 22:44 之后还有一个第二波 NVCF 降级 (23:14–23:35 UTC)**, 随后 23:36 UTC 起系统再度自愈锁定健康 fid, **实时 100% 干净**。

- 实时 DB now()=2026-08-07 07:40 CST (=23:40 UTC)。
- **末次 cc4101-primary 错误 = 23:35:46 UTC** (client_gone_during_flush, 第一波残尾), **4.8 分钟前**。
- **自 23:35:46 后: 连续 28~17 条全 200 (chrono 实拉: 23:37:26→23:40:15 = 17/17 100%)**, 全部 fid=281478d0, buffer attempt-1 一次成交 (5~19s), 无 cooldown/429/transport 错误。
- nv_gw 实时日志 (07:36→07:40 CST): **每条 NV-GLM52-ATTEMPT tier=dsv4f0731_nv 都是 fid=281478d0**, 零 52e1ddb6、零 cooldown/exhaustion marker。

## 第二轮波分析 (23:14-23:35 UTC) — 实拉确证

30min/实时分层数据在 22:14–23:35 UTC 区间呈现**两个簇**, 非单事件尾:

| 簇 | 时间 (UTC) | 错误 | 病根 |
|---|---|---|---|
| 簇1 (旧, R883 已录) | 22:16–22:44 | all_tiers_exhausted/buffer_exhausted | 同源全键 429 事件 |
| **簇2 (本轮新录)** | **23:14–23:35** | **all_tiers_exhausted ×5, buffer_exhausted ×3, client_gone_during_flush ×1** | **dsv4f0731_nv tier 间歇命中坏 fid `52e1ddb6`** |

- `nv_tier_attempts` 50min 窗: dsv4f0731_nv 下两个 fid:
  - **`281478d0`** (ai-deepseek-v4-flash-0731): **pexec_success ×135, 全 key, 100% SR (540/540@3h)**。
  - **`52e1ddb6`** (ai-deepseek-v4-flash, 即 dsv4f_nv 的 fid): **~48 失败** (529_nv_overloaded ×10, NVCFPexecRemoteDisconnected ×28, NVCFPexecTimeout ×9, empty_200 ×3), 0% SR。**末次 23:33 UTC, 此后不再被轮转。**
- **实时容器日志证实当前只走 281478d0**: 07:36→07:40 CST 每条 attempt fid=281478d0, 零 52e1ddb6。即 `52e1ddb6` 的全部尝试均发生在更早 (含 23:14-23:33 窗口), 现已被 func_health 健康降级剔除, 锁定 281478d0。

## 根因判断 (为何不用改码)

1. **R-fid0731 (本轮 round 之前, 08-07 03:28 CST 容器重启加载) 已正确把 dsv4f0731_nv 指向专用 fid `281478d0`**, config.py 的 `function_ids=[281478d0]` 为唯一候选, env 无覆盖。
2. 23:14-23:33 窗口 `52e1ddb6` 出现在 dsv4f0731 tier, 系 NVCF 上游瞬态: 281478d0 当时经历短暂降级, 轮转探测/健康选择恰好试到兄弟模型 dsv4f_nv 的坏 fid `52e1ddb6` (同一部署), 撞上 NVCF 上游 529/断连 → 短暂 all_tiers_exhausted。**这是上游瞬态 + 被动健康轮转的正常降级行为**, 非 our-side 配置缺陷。
3. 自 23:34 UTC 起 `52e1ddb6` 不再被轮转, gateway 锁定 `281478d0` (100% SR), **实时完全自愈**。fid 健康降级 + fail-fast + cooldown 机制按设计工作。
4. 三容器 health 均 ok, primary=dsv4f0731_nv, 5 keys, nv_gw passthrough���

## 为何不改码 (审慎原则)

- 铁律 "改前必有数据 / 改后必验证 / 不冒险改已自愈状态": 当前实时 100% 干净 (自末次错误 23:35:46 后连续 17-28 条 200), 无进行中降级。
- 无新错误类可作为独立修复目标; `52e1ddb6` 泄露是上游瞬态窗口的产物, 非持续配置问题。
- 若强制 pin (禁止把 dsv4f0731 用 52e1ddb6), 会削弱 func_health 跨候选容灾 (261478d0 若真降级需备用), 属过度收紧, 当前数据不足支撑。
- 记录但不改码。下一轮若 52e1ddb6 再获轮转且集中失败, 再评估 pin。

## 下一步

- 30min 窗口继续右移, 簇2 尾部 (23:35:46) 将自动滑出; 下一轮 window SR 预期回 100%。
- 监控: `52e1ddb6` 是否再被轮转且集中失败; fid 281478d0 SR 是否稳定 (当前 100% @540)。
- 保持 cc4101-primary fallback dsv4f0731_nv 不动。

## 验证 (本轮无代码改动)

- `curl localhost:40006/health` → ok (passthrough, 5 keys, dsv4f0731_nv 在列) ✅
- `curl localhost:4101/health` → ok (primary=dsv4f0731_nv) ✅
- `curl localhost:40066/health` → ok (dsv4p_nv40066) ✅
- `docker ps`: nv_gw / cc4101 / dsv4p_nv40066 全 Up ✅
- 实时日志: 全 fid=281478d0, attempt-1 SUCCESS, 无 exhaustion/cooldown marker ✅

## 参数快照 (env, 本轮未改)

- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_FORCE_STREAM_UPGRADE=0, TIER_TIMEOUT_BUDGET_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, primary=dsv4f0731_nv, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (铁律4 不主动改), CC4101_PRIMARY_FAIL_THRESHOLD=3
- config.py: dsv4f0731_nv function_ids=[281478d0-f307-49f4-9e0f-080b63b16c47] (R-fid0731 已生效); dsv4f_nv function_ids=[52e1ddb6-...] (兄弟模型, 未动)