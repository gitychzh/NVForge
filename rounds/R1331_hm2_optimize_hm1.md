# HM2 Optimize HM1 — Round R1331

## 触发分析

- 脚本检测到 R1330 自提交 (HM2→HM1 NOP, "这是我提交的, 不触发")
- cron 仍被派遣 — 误触发 (45th consecutive post-R1286)
- `.hm2_processed_head` = `f02c93c1` = git HEAD (已处理)

## 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up 42 minutes (healthy), started 2026-07-14T05:49:30Z
- Compose md5: `6e1b58bc70eca49e500e3034b08376d9` (stable, unchanged from R1286 baseline)
- NVU_PEER_FB_SKIP_MODELS: empty

### 6h 总体 (01:00–07:00 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 104 |
| 成功 (200) | 93 |
| 失败 (502) | 11 |
| 成功率 | 89.4% |
| tier_attempts | 0 |
| fallback_occurred | 0 |

### 按模型
| 模型 | 总量 | OK | 失败 | SR | avg_ms | max_ms |
|------|------|-----|------|-----|--------|--------|
| glm5_2_nv | 52 | 45 | 7 | 86.5% | 11,937 | 50,550 |
| dsv4p_nv | 52 | 48 | 4 | 92.3% | 24,867 | 72,028 |

### 错误分类
| 错误类型 | 数量 | 模型 | 可修复 |
|---------|------|------|--------|
| zombie_empty_completion | 7 | glm5_2_nv | ❌ NVCF content-filter stop, 不可配置修复 |
| all_tiers_exhausted | 4 | dsv4p_nv | ❌ ABORT-NO-FALLBACK code path, ms_gw 218-233s TimeoutError |

### Zombie 详情
| 指标 | 值 |
|------|-----|
| 模型 | glm5_2_nv integrate |
| avg duration_ms | 5,986 |
| max duration_ms | 9,914 |
| 根因 | NVCF content-filter → finish_reason=stop, content_chars<50, input ~184K |

### ATE 详情 (dsv4p_nv pexec)
| 指标 | 值 |
|------|-----|
| 数量 | 4 |
| avg duration_ms | 72,024 |
| input_chars | 240K+ |
| 失败模式 | empty_200 (k4/k5) + NVCFPexecTimeout (k1/k5) → FASTBREAK=1 → ABORT-NO-FALLBACK → ms_gw dsv4p_ms TimeoutError 218-233s |
| FASTBREAK | 1 (正确，function-level signal) |
| Peer-fb | 0 triggered (ABORT-NO-FALLBACK code path skips) |

### 每小时 SR
| 小时 | 总量 | OK | 失败 | SR |
|------|------|-----|------|-----|
| 01:00 | 29 | 28 | 1 | 96.6% |
| 02:00 | 5 | 5 | 0 | 100.0% |
| 03:00 | 5 | 3 | 2 | 60.0% |
| 04:00 | 4 | 3 | 1 | 75.0% |
| 05:00 | 4 | 2 | 2 | 50.0% |
| 06:00 | 57 | 52 | 5 | 91.2% |

### 最近 10 条请求 (延迟+状态)
| ts | model | status | ttfb_ms | dur_ms | error_type | upstream | input_chars |
|----|-------|--------|---------|--------|-----------|----------|-------------|
| 06:34:00 | glm5_2_nv | 502 | 4,762 | 4,763 | zombie | integrate | 184K |
| 06:33:20 | glm5_2_nv | 200 | 39,654 | 39,654 | - | integrate | 184K |
| 06:27:28 | dsv4p_nv | 502 | 687 | 72,021 | ATE | - | 244K |
| 06:22:22 | dsv4p_nv | 502 | 533 | 72,028 | ATE | - | 243K |
| 06:21:52 | dsv4p_nv | 200 | 29,738 | 29,739 | - | pexec | 231K |
| 06:21:43 | dsv4p_nv | 200 | 9,108 | 9,109 | - | pexec | 161K |
| 06:21:07 | dsv4p_nv | 200 | 36,402 | 36,406 | - | pexec | 156K |
| 06:20:02 | dsv4p_nv | 200 | 64,223 | 64,362 | - | pexec | 148K |
| 06:19:51 | dsv4p_nv | 200 | 10,594 | 10,595 | - | pexec | 147K |
| 06:19:30 | dsv4p_nv | 200 | 20,425 | 20,426 | - | pexec | 146K |

### ms_gw 信号
| 总请求 | OK | client_disconnect |
|--------|-----|-------------------|
| 18 | 17 | 1 |

### 参数状态
所有参数处于 floor/optimal:
- UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- TIER_TIMEOUT_BUDGET_S=205
- MIN_OUTBOUND_INTERVAL_S=0
- NVU_SSLEOF_RETRY_DELAY_S=1.0

## 决策: NOP

### 原因
1. **误触发 (45th consecutive post-R1286)**: 脚本检测到 HM2 的 R1330 自提交，非 HM1 新提交
2. **zombie_empty_completion ×7**: glm5_2_nv integrate NVCF content-filter stop (input ~184K, output 18 chars, finish_reason=stop). 网关 zombie 检测 + error-chunk 正确执行。NVCF 侧行为，不可配置修复。
3. **all_tiers_exhausted ×4**: dsv4p_nv pexec 空200+超时 → FASTBREAK=1 (正确) → ABORT-NO-FALLBACK (code path 跳过 peer-fb) → ms_gw dsv4p_ms 218-233s TimeoutError (超 NVU_MS_GW_FALLBACK_TIMEOUT=195). 大请求 (240K+ chars) 在 Modelscope 侧超时，不可配置修复。
4. **0 tier_attempts**: FASTBREAK 在两种路径 (pexec/integrate) 均正常工作，无 key cycling 浪费
5. **所有参数 floor/optimal**: 无调整空间
6. **Compose md5 稳定**: 6e1b58bc 未变
7. **容器 42min 前重启**: 05:49 UTC (HM1 内部维护)，06:00 小时 post-restart 57req/52OK 91.2% SR — 排除了配置变更

### 变更
- **零参数变更** — 不修改任何配置
- **零 compose 编辑** — 不修改 docker-compose.yml
- **零容器重启** — 不重启 nv_gw

## 铁律: 只改HM1不改HM2
本次回合未修改任何配置，铁律自然满足。

## ⏳ 轮到HM1优化HM2