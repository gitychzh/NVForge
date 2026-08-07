# R915 cc2 NOP: cc2 主链路 100% 干净 (113/113), bad 全属 hermes (5 request_id JOIN 铁证), 第 24 连清轮

- 日期: 2026-08-07 (live DB 约 09:35 CST 实拉)
- 类型: NOP 巡检轮 (不改码)
- 结论: cc2 primary (nv_gw:40006) = 113/113 = 100% SR, 0 bad; bad 100% 属 hermes 线; fallback 0; 不改码

## 数据依据 (live DB 30min 实拉)

- 30min caller × status (nv_requests):
  `cc4101-primary|200|113`, `hermes|200|3`, `hermes|502|5`
- **cc4101-primary = 113/113 全 200, 0 bad (100% SR)**; `status!=200` → 0 条属 cc2。
- 30min bad (502) = `all_tiers_exhausted ×3` (avg 180045ms) + `stream_absolute_cap ×2` (avg 155678ms),
  全部 caller=hermes。
- **request_id 级 JOIN 铁证** (nv_requests ⋈ nv_tier_attempts):
  5 bad request_id = 493f9224(stream_absolute_cap,4 at)/9b4fd536(all_tiers,6)/5d3afd42(stream_cap,3)/
  056d2c5e(all_tiers,5)/bfcd651d(all_tiers,5) — **全部 caller=hermes, 0 个属 cc2 主链**。
- cc_requests 30min: total=1550, fb=**0**, global SR=83.2% (含 hermes 线 bad, 非 cc2 主链指标)。
- fid 级 (nv_tier_attempts dsv4f0731_nv): 健康 fid **281478d0**=114 attempts (主链候选池);
  坏 fid **52e1ddb6**=25 attempts, 全部 JOIN 归属 **hermes**, 0 泄漏进 cc2 候选池。
- per-key 瞬态错误 (NVCFPexecRemoteDisconnected ×20 / Timeout ×3 / 529_nv_overloaded ×2)
  分散 k0~k4, 均被 func_health + round-robin 吸收, 未达 cc2 全挂。
- 容器 health: 4101/40006/40066 全 ok; nv_gw Up 6h, cc4101 Up 6h。

## 决策

**NOP (不改码)**。cc2 主链连续第 **24** 轮 (R892-R915) 100% SR 干净;
5 bad 全属 hermes 线且 request_id 级 JOIN 铁证未进 cc2 主链; bad fid 52e1ddb6 = 0 泄漏;
fallback 0, 无新错误类; fid 健康选择 (281478d0 vs 52e1ddb6) 达稳态。铁律 1"改前有数据、
没数据不动手" 下, 主链 100% 无优化需求, 改动无依据 → 只记数据。

## 参数快照 (未变, nv_gw + cc4101)

- nv_gw: NVU_DISABLE_MS_FALLBACK=0, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_FORCE_STREAM_UPGRADE=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, 5key k0-k4.
- cc4101: PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages (primary=dsv4f0731_nv),
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (fallback=glm5_2_ms),
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3.

## 验证

- curl 4101/40006/40066 → 全 ok; cc4101 primary=dsv4f0731_nv。
- 30min nv_requests cc4101-primary 实拉 = 113/113 (0 bad)。
- 30min 所有 bad request_id 级 JOIN 铁证 → 5 条全 caller=hermes, cc2 主链 0 bad。
- 52e1ddb6 全部 attempts JOIN 归属 hermes (RemoteDisconnected/529/Timeout/empty), 0 进 cc2;
  func_health 健康选择 (281478d0) 未选中坏 fid。

## 下一步

- 继续 NOP 巡检; 若 hermes 线 all_tiers_exhausted/stream_absolute_cap 恶化或试探性侵入 cc2 主链
  (request_id JOIN 出现 cc4101-primary bad), 再处理。
- 关注 per-key NVCFPexecRemoteDisconnected/Timeout 趋势; 若持续上升威胁主链, 考虑 fid/egress 再平衡。