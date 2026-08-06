# R878 — cc2 NOP 巡检轮 (HM2 nv_gw)

- 日期: 2026-08-07 ~06:10 CST (DB UTC)
- 上轮: R877 (NOP, 近窗 112×200 零错误, all_tiers_exhausted 全 hermes)
- 上轮健康: nv_gw Up 7h, cc4101 Up 2h, dsv4p Up 2d, nv_gw_stable Up 5d 对照
- 判定: **NOP 巡检轮 — 只记数据不改码**

## 结论 (一句话)

cc2 自身路径 30min **100% (104×200) 零错误**, 残留 all_tiers_exhausted×5 经 DB 独立核验全部 caller=hermes 外部 cron (~179s buffer deadline 全额耗尽签名), 不改码.

## 本轮数据 (轮前链路分析注入 + 独立 DB 复核)

**最近 30min cc4101-primary (cc2 路径) SR = 100% (104×200, 零错误)**

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 30min cc4101-primary SR** | **100% (104×200)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有, cc4101 /health 确认) | ✅ |
| **30min caller×status (独立 DB)** | cc4101-primary 104×200; hermes 1×200 + 5×502 | cc2 路径全净 |
| **error 归属** | all_tiers_exhausted×5 全 caller=hermes, avg 179448ms ≈ buffer deadline 全额耗尽 | ✅ 与 cc2 无关 |
| **fallback 触发率** | 0 (全新请求 0 fallback) | ✅ |
| **buffer** | cc4101-primary 全 attempt=1/5 一次成交 (9~13s each, success_tool_call), 无 buffer/wait 退化 | ✅ |
| **per-key nv_tier_attempts** | dsv4f0731_nv 5key pexec_success ~20~22/key, NVCFPexecRemoteDisconnected 瞬态 + Timeout + 529_nv_overloaded 全被跨 key 吸收 | ✅ |
| **三容器 health** | nv_gw(40006)/cc4101(4101)/dsv4p(40066) 均 ok, primary=dsv4f0731_nv, 5 keys | ✅ |

### 注: 轮前链路分析标注 "上轮 R876", 但 repo HEAD 已至 R877 (05:53:29 提交). 本轮独立 DB 复核 data 与本窗一致, 判定为 R878.

### 关键判断: cc2 路径全净, hermes 周期 all_tiers_exhausted 非本链路问题

30min 窗口独立 DB 复核: cc4101-primary **104×200 零错误**; 非 200 (502×5) 全部 caller=hermes
(外部客户端, 非 cc4101): all_tiers_exhausted×5, avg 179448ms ≈ buffer deadline /单 tier budget
全额耗尽签名 —— 属 hermes 外部 cron 周期性请求(沿用 R853-R877 判定), 而非本链路退化.

buffer 日近窗 cc4101-primary 全 attempt1 一次成交(9~13s, success_tool_call), 无 multi-attempt
退化, 证明 KeyManager/跨 key round-robin 修复链健康. cc2 自身路径 104×200 零错误, fallback 0%,
无 buffer/wait 退化, 链路/KeyManager 无退化. 不改码.

## 修复链 (沿用, R827+R828+R829+R833+R813)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 1-14s 一次成功, 用户无感知
3. 多 tier round-robin (dsv4p/dsv4f/glm5_2_nv) 自适应吸收底层跨 key 瞬态失败 (双 fid 现象)

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys, nvcf_pexec_models 含 kimi_nv/dsv4p_nv/dsv4f_nv/dsv4f0731_nv/glm5_2_nv)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066, passthrough, 5 keys)
- docker ps: nv_gw = Up 7h, cc4101 = Up 2h, dsv4p = Up 2d (nv_gw_stable = Up 5d 对照)

## 参数快照 (无变化, R878, 与注入配置一致)

```
nv_gw(40006): pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03 (0:0;1:0;2:0;3:0;4:0), BUFFER 5×90s=450s (STAIRS 90,90,90,90,90, RETRIES=5),
              WAIT max 120s, TIER_COOLDOWN_S=180, TIER_TIMEOUT_BUDGET_S=180, FORCE_STREAM_UPGRADE_TIMEOUT=150,
              KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90,
              MIN_OUTBOUND_INTERVAL_S=10, NVU_DISABLE_MS_FALLBACK=0,
              NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
cc4101(4101): PRIMARY 动态轮转 (primary=dsv4f0731_nv), FALLBACK=ms_gw:40007 (glm5_2_ms, chat/completions),
              STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
              UPSTREAM_IDLE_TIMEOUT=150, PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步
- 长期观测。glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。
- hermes 周期 all_tiers_exhausted (~179s avg) 属外部客户端 cron, 非 cc2 使命; 持续观察是否影响 NV 成功指标 (当前无影响)。
- 不改码。修复链充分, cc2 近窗全净 (dsv4f0731_nv primary 维持 100% 则持续 NOP; 待 cc2 路径 SR 掉 <99% 或 buffer 退化 (>1 attempt) 再动手)。