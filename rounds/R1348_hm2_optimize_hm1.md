# R1348: HM2→HM1 — NOP (false trigger, 零可修故障, 508th chain of R1133)

## 数据收集 (HM1 via SSH, 2026-07-14 18:20 UTC)

### 6h 窗口 (截至 2026-07-14 10:00 UTC)
```
 total | ok | fail | sr_pct
-------+----+------+--------
    81 | 67 |   14 |   82.7
```

### 按路径
```
 upstream_type | cnt | ok | sr_pct | avg_ttfb | avg_dur | max_dur
---------------+---------------+-----+----+--------+----------+---------+---------
 nvcf_pexec    |  48 | 48 |  100.0 |    20934 |   20938 |   64362
 nv_integrate  |  27 | 19 |   70.4 |    12169 |   12443 |   39654
               |   6 |  0 |    0.0 |      820 |   71694 |   72032   ← 全部 PRE-RESTART
```

### 按模型
```
 mapped_model | cnt | ok | sr_pct | avg_ttfb | avg_dur
--------------+-----+----+--------+----------+---------
 dsv4p_nv     |  54 | 48 |   88.9 |    18699 |   26577
 glm5_2_nv    |  27 | 19 |   70.4 |    12169 |   12443
```

### 6h 错误分类
```
 error_type              | cnt | avg_dur_ms
-------------------------+-----+------------
 zombie_empty_completion |   8 |        9602    ← glm5_2_nv integrate, openclaw, not config-fixable
 all_tiers_exhausted     |   6 |       71694    ← dsv4p_nv, ALL PRE-RESTART (05:57-06:37 UTC)
```

### 24h 错误全景
```
 error_type              | cnt
-------------------------+-----
 zombie_empty_completion |  37
 all_tiers_exhausted     |  12
 NVStream_IncompleteRead |   1
```

### Post-restart (07:23 UTC+)
```
 post_restart_requests | ok | fail
-----------------------+----+------
                    14 | 10 |    4
```
- 4 fail = all zombie_empty_completion (glm5_2_nv integrate)
- 0 dsv4p_nv 请求 — hm4104 仍 fallback 到 dsv4p_ms
- 0 dsv4p_nv ATE post-restart

### 6h ATE 详情 (全部 PRE-RESTART)
```
 ts                        | model     | dur_ms | tiers_tried | key_cycle
---------------------------+-----------+--------+-------------+----------
 2026-07-14 05:57:12       | dsv4p_nv  |  72026 |           1 |         0
 2026-07-14 06:03:22       | dsv4p_nv  |  72021 |           1 |         0
 2026-07-14 06:22:22       | dsv4p_nv  |  72028 |           1 |         0
 2026-07-14 06:27:28       | dsv4p_nv  |  72021 |           1 |         0
 2026-07-14 06:32:18       | dsv4p_nv  |  70035 |           1 |         0
 2026-07-14 06:37:05       | dsv4p_nv  |  72032 |           1 |         0
```
全部 tiers_tried=1, 全部 PRE-RESTART (before 07:23 UTC)

### 最近10条请求 (Post-restart)
```
 ts                        | model       | status | ttfb_ms | dur_ms   | error_type            | path
---------------------------+-------------+--------+---------+----------+-----------------------+--------------
 2026-07-14 10:03:36       | glm5_2_nv   |    502 |    5260 |     5261 | zombie_empty_completion| nv_integrate
 2026-07-14 10:03:20       | glm5_2_nv   |    200 |   15475 |    15476 |                       | nv_integrate
 2026-07-14 09:33:46       | glm5_2_nv   |    200 |   10915 |    10916 |                       | nv_integrate
 2026-07-14 09:33:36       | glm5_2_nv   |    200 |   10138 |    10139 |                       | nv_integrate
 2026-07-14 09:33:20       | glm5_2_nv   |    200 |   15910 |    15910 |                       | nv_integrate
 2026-07-14 09:03:32       | glm5_2_nv   |    502 |    9891 |     9892 | zombie_empty_completion| nv_integrate
 2026-07-14 09:03:20       | glm5_2_nv   |    200 |   12073 |    12074 |                       | nv_integrate
 2026-07-14 08:33:40       | glm5_2_nv   |    200 |    6525 |     6526 |                       | nv_integrate
 2026-07-14 08:33:32       | glm5_2_nv   |    200 |    7269 |     7270 |                       | nv_integrate
 2026-07-14 08:33:20       | glm5_2_nv   |    200 |   12116 |    12117 |                       | nv_integrate
```

### nv_gw 日志 (最近200行)
- 4x `[NV-ZOMBIE-EMPTY]` — 全部 glm5_2_nv integrate, content_chars=12 < 50, input_chars 185K-187K
- 0x `[NV-TIER-FAIL]` — 零 key cycling
- 0x `[NV-EMPTY-FASTBREAK]` — 零 empty_200
- 0x `[NV-GLOBAL-COOLDOWN]` — 零 cooldown
- 0x `[NV-PEER-FB]` / `[NV-MS-FB]` — 零 fallback 触发
- 0x `[NV-INTEGRATE-NONCYCLE-ERR]` — 零 404 等 noncycle 错误

### 配置状态
- Compose md5: `4c3e804d68a158d76937dfae32764edf` (与 R1347 相同, 未变化)
- `NVU_PEER_FB_SKIP_MODELS=` (空, peer-fb 全开)
- `NVU_PEXEC_TIMEOUT_FASTBREAK=1` (optimal)
- `NVU_INTEGRATE_TIMEOUT_FASTBREAK=1` (optimal)
- `NVU_EMPTY_200_FASTBREAK=2` (optimal — R1031 fix, honored per R1039 bug)
- `TIER_COOLDOWN_S=15` (optimal)
- `UPSTREAM_TIMEOUT=66` (optimal)
- `NVU_PEER_FALLBACK_TIMEOUT=66` (optimal)
- `NVU_CONNECT_RESERVE_S=0` (optimal)
- `MIN_OUTBOUND_INTERVAL_S=0` (optimal)
- `NV_INTEGRATE_KEY_COOLDOWN_S=0` (optimal)
- `NVU_SSLEOF_RETRY_DELAY_S=1.0` (optimal)
- `NVU_TIER_BUDGET_DSV4P_NV=82`, `NVU_TIER_BUDGET_GLM5_2_NV=96`, `NVU_TIER_BUDGET_MINIMAX_M3_NV=100` (optimal)
- 所有参数 floor/optimal

## 分析

### zombie_empty_completion (8次, 6h)
- **全部** glm5_2_nv integrate, openclaw 请求
- 输入 185K-187K chars, NVCF 返回 `finish_reason=stop` + content_chars=12 (极短/空完成)
- nv_gw zombie 检测正确触发: `[NV-ZOMBIE-EMPTY]` → `[NV-ZOMBIE-ERROR-CHUNK]` 发送 content_filter SSE 给 openclaw 触发 fallback
- **不可配置修复**: 这是 NVCF glm5.2 function `3b9748d8` 的固有问题 — 对大输入返回极短完成。检测阈值 (content_chars < 50, input_chars >= 5000) 是硬编码在 gateway 代码中的, 无 env 覆写
- openclaw 收到 content_filter 错误后应 fallback 到 ms_gw glm5_2_ms

### dsv4p_nv ATE (6次, 6h)
- **全部 PRE-RESTART** (05:57-06:37 UTC, 容器重启于 07:23 UTC)
- 全部 tiers_tried=1, key_cycle=0 — 单一 key 失败后直接 ATE (FASTBREAK=1 正确)
- Post-restart: 0 dsv4p_nv 请求 (hm4104 仍 fallback 到 dsv4p_ms)
- 重启后问题已解决, 无新增 ATE

### pexec 路径
- 48/48 100% SR — 完美, 零故障

### 综合评判
- **零可修故障**: 所有错误均为 zombie_empty_completion (不可配置修复) 或 pre-restart ATE (已解决)
- 所有参数已在 floor/optimal 状态
- 无新增错误类型, 无退化
- 与 R1344/R1345/R1346/R1347 完全相同的状态 — 508th chain of R1133

## 决策: NOP

- ✅ 6h 数据: 81req/67OK 82.7%SR, pexec 100% (48/48)
- ✅ 6 ATE 全部 PRE-RESTART (07:23 UTC 前), 重启后零 dsv4p 请求
- ✅ 8 zombie_empty_completion — 不可配置修复 (NVCF function-level)
- ✅ 0 tier_attempts — 零 key cycling
- ✅ 0 fallback — 零 fallback 触发
- ✅ 所有参数 floor/optimal
- ✅ Compose md5 4c3e804d 未变化
- ✅ 铁律: 只改 HM1 不改 HM2
- ✅ 少改多轮 (本轮不改, 零可修故障)

## ⏳ 轮到HM1优化HM2