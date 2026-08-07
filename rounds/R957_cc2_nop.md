# R957 — cc2 NOP 巡检轮 (不改码)

> 结论: cc2 主链路连续第 **65** 轮 (R893-R957) 100% SR 干净; 2 个 bad 请求
> (502 all_tiers_exhausted + 502 zombie_empty_completion) caller 归属 **hermes** 非 cc2;
> fallback 0 次。

## 数据 (live DB 30min, ≈2026-08-07 12:06 CST)

### cc4101-primary (主 nv_gw:40006) — cc2 范围

| caller × status | count | avg_dur |
|---|---|---|
| cc4101-primary × 200 | **125** | 9100ms |
| **bad** | **0** | — |

- **cc4101-primary = 125/125 = 100% SR, 0 bad**。
- 总 nv_requests: 153 req, 151 ok, **cc2_bad = 0**, 全局 SR = 98.7%。

### 唯一 bad 归属判定
- `hermes × 502 × all_tiers_exhausted × 1` (avg_dur ~174163ms)
- `hermes × 502 × zombie_empty_completion × 1` (avg_dur ~39596ms)
- **caller 列双重归属 hermes**, 非 cc2 主链 → 越界, 不属 cc2 优化范围。

### fallback (cc_requests 30min)
- total=125, fallback_triggered=**0** (全 status=200, SR=100%)。

### nv_tier_attempts per-key (dsv4p, 30min)
- 每 key: NVCFPexecRemoteDisconnected 2-5 + pexec_success 23-26
  (k0:2/25, k1:3/24, k2:3/26, k3:5/25, k4:5/25)。
- 瞬态 RemoteDisconnected 被多 key round-robin + buffer 重试吸收, 全部 resolve 为 200。

### buffer 日志 (nv_gw --since 30m)
- cc4101-primary 全 attempt=1 success (elapsed 1.6-12s, verdict success_tool_call/success_text, input 68-71k)。
- 无 WAIT-/KEYMGR- 错误噪声。

## 判断
- cc2 主链 SR 100% + 专属错误 0 rows → 无优化需求, **不改码**。
- 2 个 bad 全属 hermes (caller 列归属), 越 cc2 范围, 不处理。
- 链路健康, 无 ms_gw fallback, tier 瞬态全被吸收。

## 验证
- live re-pull 30min: cc4101-primary 125/125 (0 bad, avg 9100ms)。
- bad 分组 (status!=200): hermes × 2 (all_tiers_exhausted + zombie_empty_completion), cc2 主链 0 bad。
- cc_requests fallback = 0 (125 req 全 200, SR=100%)。
- docker logs nv_gw buffer 段: cc4101-primary 全 attempt=1 success, 无错误噪音。
- health: 4101/40006/40066 全 200。

## 下轮
- 继续 NOP 巡检; 下轮重拉 30min 窗口。
- 若 cc4101-primary 专属错误 > 0 或 SR < 99%, 先找根因再小步改 (铁律 1/2)。
- 观察 hermes 线 all_tiers_exhausted/zombie 是否持续或泄漏进 cc2; hermes 线 bad 越界不属
  cc2 范围, 0 泄漏进 cc2 即无行动。