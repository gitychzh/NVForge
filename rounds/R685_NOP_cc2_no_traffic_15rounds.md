# R685: NOP 巡检轮 — cc2 链路无流量 30min 0req (连续15轮)

> 日期: 2026-08-03 17:50 CST
> 上轮: R684 (NOP)

## 改动: 不改码 (NOP)

## 依据 (30min 窗口实测 + 注���快照一致)

### cc2 链路 (cc4101-primary/glm5_2_nv)
- 30min: **0 请求** (R671-R685 连续 15 轮同型态, cc2 核心正反馈循环受阻)

### 30min 全量 20 req (全非 cc2 链路)
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv | 200 | 15 |
| hermes | dsv4p_nv | 429 | 4 |
| opencode | glm5_2_nv | 200 | 1 |

- dsv4p_nv SR = 15/19 = **78.9%** (R684: 61.5% → 回升)
- glm5_2_nv: 1/1 = 100% (opencode, 样本极小)
- 30min fallback: 20 次 (全 hermes→dsv4p_nv, 非 cc2)

### 错误分类
- all_tiers_exhausted|all_tiers_failed_in_mapped_tier ×4 (avg_dur 1648ms)
  → dsv4p_nv 5key 全挂 (配额型, 非 cc2 管辖)

### per-key × status (dsv4p)
- k2: 200×15 (avg 11272ms)
- null-key: 429×4 (avg 1648ms, 全挂时无 key 分配)

### per-egress-IP (dsv4p)
- 203.10.96.139: 15 (100%)
- null: 4 (0%, 全挂时无 egress)

### dsv4p 200 延迟
- avg 11272ms, ttfb 10765ms, finish_reason: tool_calls×13, stop×2

### 30min 按分钟趋势
- 09:20 429×1, 09:25 200×2+429×1, 09:30 429×1, 09:35 429×1, 09:40 200×4, 09:41 200×2, 09:45 200×4, 09:46 200×3

### nv_tier_attempts
- 30min: 仅 1 行 (k4 pexec_success×1, opencode glm5_2_nv)
- dsv4p_nv 全挂 → 无 dsv4p tier attempt

### 日志
- 无 BUFFER/WAIT/NV-ANTH-COLLECT 日志
- R661 修复窗口 post-restart ~40h+ 仍无 NVAnthCollect_IncompleteRead 再现

## 验证: NOP 无需 restart
- `curl /health` nv_gw + cc4101 + dsv4p_nv40066 全 ok, nv_gw 5keys
- `docker ps` 容器都 Up: nv_gw 2h, cc4101 3h, dsv4p_nv40066 2h, nv_gw_stable 40h, logs_db 4d, ms_gw 4d
- 配置无漂移 (env 实测一致)

## 下一步
- cc2 连续 15 轮无流量 → 核心正反馈循环受阻, 无流量则无优化素材
- 等下一波 cc4101-primary (cc2) 流量 → 查 NV-ANTH-COLLECT-BUFRETRY 日志判断 R661 是否生效
- hermes dsv4p_nv all_tiers_exhausted 配额型持续 → 非 cc2 管辖, 关注 dsv4p_nv40066 fallback 路径可用性

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
