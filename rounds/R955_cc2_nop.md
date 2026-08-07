# R955 — cc2 NOP 巡检轮 (不改码)

> 结论: cc2 主链路连续第 **63** 轮 (R893-R955) 100% SR 干净; 唯一 bad 请求
> (502 all_tiers_exhausted) caller 归属 **hermes** 非 cc2; fallback 0 次。

## 数据 (live DB 30min, ≈2026-08-07 12:00 CST)

### cc4101-primary (主 nv_gw:40006) — cc2 范围

| caller × status × error | count |
|---|---|
| cc4101-primary × 200 × (空) | **122** |
| **bad** | **0** |

- **cc4101-primary = 122/122 = 100% SR, 0 bad**。
- 总 nv_requests: 152 req, 151 ok, **cc2_bad = 0**, 全局 SR = 99.3%。

### 唯一 bad 归属判定
- `hermes × 502 × all_tiers_exhausted × 1` (avg_dur 174163ms)。
- **caller 列归属 hermes**, 非 cc2 主链 → 越界, 不属 cc2 优化范围。

### fallback (cc_requests 30min)
- total=121, fallback_triggered=**0** (全 status=200, SR=100%)。

### nv_tier_attempts per-key (dsv4p, 30min)
- 每 key: NVCFPexecRemoteDisconnected 2-5 + pexec_success 23-25。
- 瞬态 RemoteDisconnected 被多 key round-robin + buffer 重试吸收, 全部 resolve 为 200。

### buffer 日志 (nv_gw --since 30m)
- cc4101-primary 全 attempt=1 success (elapsed 2-12s, verdict success_text/success_tool_call)。
- 无 WAIT-/KEYMGR- 错误噪声。

## 判断
- cc2 主链 SR 100% + 专属错误 0 rows → 无优化需求, **不改码**。
- 唯一 bad 全属 hermes (caller 列归属), 越 cc2 范围, 不处理。
- 链路健康, 无 ms_gw fallback, tier 瞬态全被吸收。

## 验证
- live re-pull 30min: cc4101-primary 122/122 (0 bad)。
- 唯一 bad 分组 caller=hermes (all_tiers_exhausted ×1), cc2 主链 0 条。
- cc_requests fallback = 0 (121 req 全 200)。
- docker logs nv_gw buffer 段全 attempt=1 success, 无噪声。

## 下一步
- 保持 NOP 观察。若 hermes 线 all_tiers_exhausted 增加或泄漏入 cc2, 再查 KeyManager cooldown/429。