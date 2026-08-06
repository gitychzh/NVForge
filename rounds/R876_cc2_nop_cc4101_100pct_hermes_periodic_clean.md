# R876 — cc2 NOP 巡检轮 (HM2 nv_gw)

- 日期: 2026-08-07 ~05:55 CST (DB UTC)
- 上轮: R875 (NOP, 近窗 114×200 零错误, all_tiers_exhausted 全 hermes)
- 上轮健康: nv_gw Up 2h, cc4101 Up 2h, dsv4p Up 2d, nv_gw_stable Up 5d 对照
- 判定: **NOP 巡检轮 — 只记数据不改码**

## 结论 (一句话)

cc2 自身路径 30min **100% (114×200) 零错误**, 残留 all_tiers_exhausted×6 经 DB 独立核验全部 caller=hermes 外部 cron, 不改码.

## 本轮数据 (轮前链路分析注入 + 独立 DB 复核)

**最近 30min cc4101-primary (cc2 路径) SR = 100% (114×200, 零错误)**

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 30min cc4101-primary SR** | **100% (114×200)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有, cc4101 /health 确认) | ✅ |
| **30min 按模型 SR** | dsv4f0731_nv = 95.8% (114/119, 注入快照); DB 复核 cc4101-primary 114×200 | 与 cc2 路径 100% 一致 |
| **error 归属** | all_tiers_exhausted×6 (注入 5) 全为 caller=hermes (外部 cron), DB 独立 caller 核验 | ✅ 与 cc2 无关 |
| **非 200 归属** | 仅 `hermes/502/all_tiers_exhausted×6` (DB 独立复核), cc4101-primary 0 错误 | ✅ |
| **fallback** | 0 触发 (119 请求) | ✅ |
| **buffer** | cc2 全 "after 1 attempt" 一次成交 (3975/11732/16468ms), 无 multi-attempt 退化 | ✅ |
| **per-key nv_tier_attempts** | dsv4f0731_nv 5key 均 22-23 次 pexec_success, 瞬态错误 (RemoteDisconnected/Timeout) 被跨 key 吸收 | ✅ |
| **三容器 health** | nv_gw / cc4101 / dsv4p 均 ok, primary=dsv4f0731_nv, 5 keys | ✅ |

## 关键判断: cc2 路径全净, hermes 周期 all_tiers_exhausted 非本链路问题

30min 链路总览: cc4101-primary **114×200 零错误**; 非 200 (all_tiers_exhausted×6, 502) 经
**DB 独立 caller 核验全部 caller=hermes** (外部客户端, 非 cc4101). avg ~180s ≈ buffer deadline
特征 → hermes 严格 ~6min 周期 cron 请求, 沿用 R853-R876 一致判定: 外部客户端周期性全键耗尽/超时,
非本链路退化. 不改码, 不加探针.

buffer 全 attempt=1 一次成交, 无 multi-attempt 退化, KeyManager/跨 key round-robin 健康.
cc2 自身 114×200 零错误, fallback 0%, 无 buffer/wait 退化. 不改码.

## 修复链 (沿用, R827+R828+R829+R833+R813)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 3-16s 一次成功, 用户无感知
3. 多 tier round-robin (dsv4p/dsv4f/glm5_2_nv) 自适应吸收底层跨 key 瞬态失败 (双 fid 现象)

## 健康检查 (本轮实测)
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys, nvcf_pexec_models 含 kimi_nv/dsv4p_nv/dsv4f_nv/dsv4f0731_nv/glm5_2_nv)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066, passthrough, 5 keys)
- docker ps: nv_gw = Up 2h, cc4101 = Up 2h, dsv4p = Up 2d (nv_gw_stable = Up 5d 对照)

## 参数快照 (无变化, R876)

```
nv_gw(40006): pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03 (0:0;1:0;2:0;3:0;4:0), BUFFER 5×90s=450s (STAIRS 90,90,90,90,90, RETRIES=5),
              WAIT max 120s, TIER_COOLDOWN_S=180, TIER_TIMEOUT_BUDGET_S=180,
              KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90,
              MIN_OUTBOUND_INTERVAL_S=10, NVU_DISABLE_MS_FALLBACK=0,
              NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
cc4101(4101): PRIMARY 动态轮转 (primary=dsv4f0731_nv), FALLBACK=ms_gw:40007 (glm5_2_ms, chat/completions),
              STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
              PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
DB tz: UTC (STATE 时间为 CST = UTC+8)
```