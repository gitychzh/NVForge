# STATE.md — cc2 HM2 nv_gw 自优化当前状态

## 当前轮: R622 (2026-08-03 13:29 CST) — NOP 巡检轮

## 基线 (R622 实测, 05:01-05:27 UTC = 13:01-13:27 CST 窗口, 与 R621 同窗口延伸)
- cc2 (cc4101-primary) 30min: **0 req** (session 间歇空闲, 无 cc2 评估样本, 铁律1 cc2 视角不满足)
- dsv4p_nv 30min: 14 req, 9×200 + 5×429 (SR=64.3%, hermes caller)
  - vs R621 57.1% / R620 62.5% / R619 70.6% / R618 75.0% / R617 75.0% / R616 77.3%
    → 本轮尾部 05:26-05:27 一波 7×200 (k3 恢复) 把 SR 从 57.1% 拉回 64.3%
    → **仍处 R612 以来波动区间 (57-91%), 非线性恶化, 是周期性配额耗尽 + 采样窗口边界**
  - per-key: k2 8×200; k3 1×200; 空 key 5×429 (hermes 绑定 key2 cooling 时拿不到 key → KeyManager 层 ABORT)
  - per-egress: 203.10.96.139 8 req (100%) + 134.195.101.194 1 req (100%) + 空 5 req (0%)
  - finish_reason: tool_calls×7 + stop×2 (健康, 无 zombie)
  - fallback_occurred=f ×14 (cc4101 层 ms_gw glm5_2_ms 兜底, 预期)
- 错误分类 1 类 (非新错误):
  - `all_tiers_exhausted` ×5 (avg_dur 2024ms, all_tiers_failed_in_mapped_tier, ABORT-NO-FALLBACK)
    - 全部 nv_key_idx 为空 + nv_tier_attempts 0 行 → abort 在拿到 key 之前 (KeyManager 层)
    → all_tiers_exhausted 趋势: R613×1 → R614×2 → R615×3 → R616×4 → R617×4 → R618×4 → R619×5 → R620×6 → R621×6 → **R622×5 持平/略降**
- 6h stream_total_deadline: 0 次 (deadline 链对齐健康)
- 30min nv_tier_attempts: 0 行 (hermes caller 不走 buffer, 全挂 KeyManager 层 ABORT)

## 根因分析 (与 R621 一致, 日志铁证)
日志铁证 (30min):
- 13:01:14 / 13:06:05 / 13:11:05 / 13:16:05 / 13:21:06 五次
  `NV-GLOBAL-COOLDOWN tier=dsv4p_nv all keys 429. Marking all cooling 180s (TIER_COOLDOWN)`
- 13:26:08-13:27:52 一波 7× `NV-SUCCESS tier=dsv4p_nv k3 succeeded on first attempt`
→ NVCF 配额是周期性间歇 (~5min 周期, 5 个 key 同账户同配额池同时 429),
  全挂 180s 后 key3 先恢复, 配额自动恢复.
→ NVCF 响应头 `ratelimit/retry-after=(none)` — 未给恢复提示, KeyManager 只能盲退避 180s.
→ nv_gw 侧行为正确: 5key 全挂 → ABORT-NO-FALLBACK (dsv4p skip peer fb) →
  cc4101 fallback ms_gw(glm5_2_ms).
→ 改 KeyManager cooldown 会更糟: 缩短冷却会在 NVCF 仍配额耗尽时再撞 429, 浪费 egress 流量;
  延长冷却无意义 (180s 后已自动恢复).
→ **根因是 NVCF 上游账户级配额耗尽, 非 nv_gw 侧可改.**

## 本轮改动
- 无 (NOP). 根因是 NVCF 上游配额型故障, 非 nv_gw 侧可改.

## 依据
- cc2 (cc4101-primary) 0 流量 → 无评估样本, 铁律1 cc2 视角不满足
- dsv4p_nv SR=64.3% (vs R621 57.1% 反弹, 仍处波动区间 57-91%, 非线性恶化)
- all_tiers_exhausted ×5 vs R621×6 略降, 升级阈值 (SR<55% 或 exhausted>=8) **未触发**
- 日志铁证 GLOBAL-COOLDOWN (5min 周期) + retry-after 缺失 = NVCF 账户级配额耗尽
- 全挂 180s 后 k3 自动恢复 (13:26-13:27 一波 7×200) = 周期性, 非永久挂
- KeyManager 指数退避正确, ABORT 路径快速 (avg 2024ms vs R621 7404ms 反而更快, 无退化)
- all_tiers_exhausted 全部 nv_key_idx 空 + tier_attempts 0 行 = KeyManager 层 ABORT, 非 buffer/tier 路径
- 容器健康, 配置无漂移
- 6h 0 stream_total_deadline (deadline 链对齐健康)
- 无介入必要 (码改)

## 验证
- 0 restart → 无需 py_compile / curl 复测
- 容器状态 (docker ps + /health):
  - nv_gw: Up 23 hours (health ok, 5 keys, pexec_models=[kimi_nv, dsv4p_nv, glm5_2_nv])
  - cc4101: Up 13 hours
  - nv_gw_stable/ms_gw/logs_db: 长稳
- 配置无漂移 (与 R621 快照一致)

## 下一步 (维持观察)
- dsv4p_nv 配额耗尽趋势连续多轮在 R612-R622 波动区间 (57-91%) 内, 本轮反弹到 64.3%,
  all_tiers_exhausted ×5 略降, **未触发升级阈值 (SR<55% 或 exhausted>=8)**
- **建议维持: 联系 NVCF 侧评估 dsv4p_nv 账户配额扩容 / 提供配额恢复提示 (retry-after 头)**.
  - 当前 5key 同账户同配额池, 任一 key 429 = 全 key 429, 无差异化.
  - 若 NVCF 侧能提供 retry-after 头, KeyManager 可精准退避而非盲退 180s, 单次 ABORT 后下个请求即恢复.
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为 (cc4101-primary 走 buffer 5key 轮转)
- 若下轮 SR<55% 或 all_tiers_exhausted>=8 → 三次升级标注 (考虑切换 PRIMARY_UPSTREAM_MODEL 回 glm5_2_nv 评估)

## 参数快照 (R622 未改)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_MS_FALLBACK_MODELS=glm5_2_nv,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450,
  NVU_BUFFER_PING_INTERVAL_S=30
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, PRIMARY_UPSTREAM_MODEL=dsv4p_nv,
  PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150

## Fallback 配置实测
- nv_gw: NVU_DISABLE_MS_FALLBACK=0 (ms fallback 启用, 仅覆盖 glm5_2_nv)
- NVU_MS_FALLBACK_MODELS=glm5_2_nv (不含 dsv4p_nv)
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (dsv4p_nv 跳过 peer fallback)
- → dsv4p_nv 全挂时 nv_gw 裸返 429/502, cc4101 层 ms_gw(glm5_2_ms) 兜底
