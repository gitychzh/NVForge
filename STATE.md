# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: R860 (NOP 巡��轮 — 近窗 cc4101-primary SR=100% (123×200) 零错误 avg 8.8s, 30-min 残留 all_tiers_exhausted×5 全为 hermes 外部 cron 客户端 ~6-7min 周期, 与 cc2 路径无关, 不改码, 2026-08-07 04:50 CST)
> 上轮: R859 (NOP — 近窗 124×200 零错误, hermes 周期 all_tiers_exhausted 属外部 cron, 不改码)

## 本轮 (R860) 改动 + 依据 + 验证

### 改动: 无 (巡检轮 — cc2 路径全净 123×200, hermes 周期 all_tiers_exhausted 与 cc2 无关)

### 本轮数据 (04:48 CST 注入, DB UTC)

**最近 30min cc4101-primary (cc2 自己路径) SR = 100% (123×200, 零错误, avg 8797ms).**

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 30min cc4101-primary SR** | **100% (123×200, avg 8.8s)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有) | ✅ |
| **buffer 日志** | 无 (cc2 路径一次成交) | ✅ |
| **30min 错误分类** | all_tiers_exhausted × 5 (502, avg 180s) — 全 hermes | ⚠️ 外部 |
| **三容器 health** | nv_gw / cc4101 / dsv4p 均 ok | ✅ |

### 关键判断: all_tiers_exhausted×5 归属 hermes 周期客户端, 非链路退化

30min 窗口 5 条 `all_tiers_exhausted` (502, avg 180052ms) 全部 **caller=hermes (外部客户端, 非 cc4101)**,
呈严格周期分布, 每次 ~180s ≈ 5×90s=450s buffer deadline 全额耗尽 — 属 cron 请求特征而非链路退化 (沿用 R853-R859 判定).

per-key nv_tier_attempts 5 key 均足量 pexec_success (24-25), 瞬态错误
(RemoteDisconnected/529_nv_overloaded/NVCFPexecTimeout/empty_200) 被 KeyManager 跨 key round-robin 修复链平滑吸收,
未上抛到 cc2 用户请求. cc2 自身路径 123×200 零错误, buffer 一次成交, 证明链路/KeyManager 无问题.

## 修复链 (沿用, R827+R828+R829+R833+R813)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 1-12s 一次成功, 用户无感知
3. 多 tier round-robin (dsv4p/dsv4f/glm5_2_nv) 自适应吸收底层跨 key 瞬态失败

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys, nvcf_pexec_models 含 dsv4p_nv/dsv4f_nv/dsv4f0731_nv/glm5_2_nv/kimi_nv)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066, passthrough, 5 keys)
- `docker ps`: cc4101 Up 54min / nv_gw Up 1h / dsv4p_nv40066 Up 2d / nv_gw_stable Up 5d ✅

## 参数快照 (无变化, R860)

```
nv_gw(40006): pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s (STAIRS 90,90,90,90,90, RETRIES=5),
              WAIT max 120s, TIER_COOLDOWN_S=180, TIER_TIMEOUT_BUDGET_S=180,
              NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 已恢复), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
cc4101(4101): PRIMARY 动态轮转 (primary=dsv4f0731_nv), FALLBACK=ms_gw:40007 (glm5_2_ms, chat/completions),
              STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
              PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步
- 长期观测。glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。
- hermes 周期 all_tiers_exhausted 属外部客户端 cron, 非 cc2 使命; 持续观察是否影响 NV 成功指标 (当前无影响)。
- 不改码。修复链充分, cc2 近窗全净。