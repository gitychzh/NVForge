# R916 cc2 NOP: cc2 主链路 100% 干净 (117/117), bad 全属 hermes (5 request_id JOIN 铁证), 第 25 连清轮

- 日期: 2026-08-07 (live DB 约 09:38 CST 实拉)
- 类型: NOP 巡检轮 (不改码)
- 结论: cc2 primary (nv_gw:40006) = 117/117 = 100% SR, 0 bad; bad 100% 属 hermes 线; fallback 0; 不改码

## 数据依据 (live DB 30min 实拉)

- 30min caller × status (nv_requests):
  `cc4101-primary|200|117`, `hermes|200|2`, `hermes|502|5`
- **cc4101-primary = 117/117 全 200, 0 bad (100% SR)**; `status!=200` → **0 条属 cc2**。
- 30min bad (502) = `all_tiers_exhausted ×3` (avg 180045ms) + `stream_absolute_cap ×2` (avg 155678ms),
  全部 caller=hermes。
- **request_id 级 JOIN 铁证** (nv_requests ⋈ nv_tier_attempts):
  5 bad request_id = 493f9224(stream_absolute_cap,4 at)/9b4fd536(all_tiers,6)/5d3afd42(stream_cap,3)/
  056d2c5e(all_tiers,5)/bfcd651d(all_tiers,5) — **全部 caller=hermes, 0 个属 cc2 主链**。
- cc_requests 30min: total=118, fb=**0**。
- per-key 瞬态错误 (NVCFPexecRemoteDisconnected / Timeout / 529_nv_overloaded) 分散 k0~k4,
  被 multi-tier round-robin + func_health 吸收, pexec_success 稳定, 未达 cc2 全挂。
- 容器 health: 4101/40006 全 ok; nv_gw Up 6h, cc4101 Up 6h, dsv4p_nv40066 Up 2d。

## 决策

**NOP (不改码)**。cc2 主链连续第 **25** 轮 (R892-R916) 100% SR 干净;
5 bad 全属 hermes 线且 request_id 级 JOIN 铁证未进 cc2 主链; fallback 0, 无新错误类。
铁律 1"改前有数据、没数据不动手" 下, 主链 100% 无优化需求, 改动无依据 → 只记数据。

## 参数快照 (未变, nv_gw + cc4101)

- nv_gw: NVU_DISABLE_MS_FALLBACK=0, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, 5key k0-k4.
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages (primary=dsv4f0731_nv),
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (fallback=glm5_2_ms),
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3.

## 验证

- curl 4101/40006 → 全 ok; cc4101 primary=dsv4f0731_nv, nv_gw passthrough 5 keys。
- 30min nv_requests cc4101-primary 实拉 = 117/117 (0 bad)。
- 30min 所有 bad request_id 级 JOIN 铁证 → 5 条全 caller=hermes, cc2 主链 0 bad。
- cc_requests fallback = 0 次 (0/118)。

## 下一步

- 继续 NOP 巡检; 若 hermes 线 all_tiers_exhausted/stream_absolute_cap 恶化或试探性侵入 cc2 主链
  (request_id JOIN 出现 cc4101-primary bad), 再处理。
- 关注 per-key NVCFPexecRemoteDisconnected/Timeout 趋势; 若持续上升威胁主链, 考虑 fid/egress 再平衡。