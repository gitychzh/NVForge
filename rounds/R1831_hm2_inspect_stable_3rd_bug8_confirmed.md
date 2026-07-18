# R1831 (HM2 cc2): 巡检轮 — bug8 普通流量连续第 3 轮零真畸形 (确认不活跃); SR 93.3% 破线但根因全 cc4101 侧 bug3 不可控

## 性质
**巡检轮 (不改代码/不改 env/不 restart)**。本轮是 STATE R1830 "下一轮"指示的第 3 个稳定
观察点: 拉 30min 数据确认 SR/fallback/error 是否仍稳 + grep `NV-TOOLCALL-JSON-BAD` 排除
自反馈看真畸形。结果: bug8 普通流量连续第 3 轮零真畸形 → **确认 bug8 不活跃**; 但 SR
93.3% 破 95% 安全线 + fallback 涨到 4, 触发 STATE R1830 "下一轮"第 4 条 "若 SR 破 95% 或
fallback >3 → 重新评估" 路径。经根因分析: 全部恶化信号根因都在 cc4101 侧 bug3 (75s 抢断
甩 ms) + NVCF pexec 首字节系统性慢 (max ttfb 288s/avg 38s), **不在 nv_gw config 可控
范围**, 改 nv_gw 不影响 (4 次 fallback 请求全部 nv_requests 0 rows = 未到 nv_gw)。
决策不改: 无 nv_gw 侧可改依据, 硬改违反"改前必有数据"铁律。

## 改前数据 (30min 窗, StartedAt 仍 2026-07-18T19:33:40Z = R1827 restart 后, 本轮未动)

### SR
- **30min SR = 56/60 = 93.3%** (200:56, 502:4)
- 对比 R1830 = 95.8% (68/71), **掉 2.5pp, 破 95% 安全线** (R1829/R1830 连续 2 轮 95.8%)
- 4 条 502 全 pexec 偶发合法 error (见下)

### error_type (status!=200)
| error_type | count |
|---|---|
| stream_first_byte_timeout | 3 |
| zombie_empty_completion | 1 |

- 全 pexec 偶发合法: stream_first_byte_timeout 走 peek path 重放 ms 用户拿内容 (设计内);
  zombie_empty_completion 是 pexec 空完成 502 (非 ms_fallback path)
- **无 NV-ANTH-BREAKER-FAIL / 无 all_tiers_exhausted / 无 content_filter / 无 timeout(网关层)**

### nv_tier_attempts error_type
| error_type | count |
|---|---|
| pexec_success | 38 |
| IntegrateTimeout | 1 |
| **pexec_SSLEOFError** | **1 (新增, R1830 无)** |
| pexec_empty_200 | 1 |

- pexec_SSLEOFError: nv_key_idx=1, created_at 20:06:07 UTC, **单次样本, 不可凭单样本改**
  (SSL 连接被对端 NVCF 关闭, 偶发, 非系统性)
- IntegrateTimeout: integrate_us_rr 兜底链触发, 设计内故障递进

### fallback (cc4101 PRIMARY-FAIL-SKIP-CIRCUIT, 30min) = **4 次** (R1830=2, 涨)
| req | 时间(CST) | ttfb | FALLBACK-OK | 到 nv_gw? |
|---|---|---|---|---|
| bfdd6036 | 03:54:14 | 75080ms | 3469ms | ❌ nv_requests 0 rows |
| 0b62e8f0 | 03:56:42 | 75032ms | 2050ms | ❌ nv_requests 0 rows |
| a2208a03 | 04:03:35 | 75081ms | 33991ms | ❌ nv_requests 0 rows |
| 7cdea1ae | 04:07:30 | 75072ms | 48746ms | ❌ nv_requests 0 rows |

- 4 请求**全部 nv_requests 0 rows + nv_tier_attempts 0 rows** = cc4101 75s 抢断后**从未
  到达 nv_gw 写库** → **全是 cc4101 侧 bug3, 改 nv_gw config 不影响**
- bug3 通道: R1829=16→R1830=4→2→1→2 → 本轮=4, 低位抖动非恶化趋势 (R1830 是 2, 本轮 4,
  在 1-4 低位区间内抖, 非系统性飙升)
- 4 次 fallback 全部 FALLBACK-OK (100% 兜底成功), **0 中断**

### pexec ttfb 分布 (status=200, 30min)
| bucket | count |
|---|---|
| <5s | 5 |
| 5-15s | 18 |
| 15-30s | 19 |
| 30-60s | 8 |
| >=60s | 6 |

- **max ttfb = 287738ms (~288s!), avg = 38171ms (~38s)**
- 6 条 ≥60s, 8 条 30-60s → **大量请求 pexec 首字节 30s+, 部分 60s+**
- 这是 bug3 的根因: NVCF pexec 首字节系统性偏慢 → cc4101 在 75s 抢断 → fallback
- **根因在 NVCF 侧 (pexec 首字节慢), 非 nv_gw config 可修**

### bug8 观测层命中 (40m) = 2 条 NV-TOOLCALL-JSON-BAD, **全自反馈假阳性**
| rid | tid | len | frag 内容 |
|---|---|---|---|
| 9885ad97 | call_2913aad6c4e94cdea7ac848e | 183 | `{"content": "# R1829 (HM2 cc2): 巡检轮 — bug8 观测层假阳性定性..."` (= R1829 round 文件全文) |
| 791d66bf | call_e0cbb3c621c544e1a95641bc | 623 | `{"content": "# cc2 自优化交接棒 STATE..."` (= STATE.md 全文) |

- 2 条均 cc2 自反馈 (读 STATE/round 文件时模型生成嵌长 markdown tool_call, content 字段
  未闭合), 走正常完成路径 (R1827 去噪没屏蔽), 真畸形但**非普通用户流量**
- **非截断假阳性**: `_tc_json_bad_check` 用完整 raw 做 json.loads, len 均 <500, frag 是
  完整 raw, 截断不是失败因
- → **bug8 在普通流量连续第 3 轮 (R1829+R1830+R1831) 零真畸形, 确认不活跃**

## 决策: 不改代码
- **SR 93.3% 破线 + fallback 4 涨** 触发 STATE R1830 "下一轮"第 4 条 "重新评估" 路径,
  但根因分析全部指向 nv_gw 不可控侧:
  1. 4 次 fallback 全未到 nv_gw (nv_requests 0 rows) = cc4101 75s 抢断 = cc4101 侧 bug3
  2. error 4 全 pexec 偶发合法 (stream_first_byte_timeout/zombie), 设计内
  3. pexec_SSLEOFError 单次样本, 不可凭单样本改
  4. pexec ttfb 系统性慢 (max 288s/avg 38s) 根因在 NVCF 侧, 非 nv_gw config 可修
- **nv_gw config 侧无可改依据**: UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 /
  NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_MS_FALLBACK_TIMEOUT=120 都已在合理值, 改它们
  不会让 NVCF pexec 首字节变快 (根因不在网关超时配置)
- **硬改违反铁律**: "改前必有数据" — 数据证明恶化根因不在 nv_gw, 改 nv_gw = 无效动作
- bug8 普通流量连续 3 轮零真畸形 → **确认不活跃**, 不需动观测层
- 0 中断 (用户诉求 "可以报错但不能让 cc2 中断" 仍达成)

## 验证 (巡检轮无 restart)
- nv_gw StartedAt 仍 `2026-07-18T19:33:40Z` (R1827 restart 后, 本轮未动)
- docker ps: nv_gw Up 40 minutes
- /health: ok (passthrough/5 keys/pexec_models 齐全: kimi_nv/dsv4p_nv/glm5_2_nv)
- env 无漂移: NVU_TIER_BUDGET_GLM5_2_NV=120 (HM2 未被 peer 改), 与 R1830 一致
- 4 fallback 全 FALLBACK-OK, 0 中断

## 下一轮该做什么
1. **读本 STATE** (R1831 巡检轮未改代码, StartedAt 仍 19:33:40 UTC)
2. **拉 30min 数据** 看 SR 是否回升 ≥95% 还是继续在 93% 附近 / fallback 是否回落到 1-2
   还是持续 4+:
   - 若 SR 回升 + fallback 回落 → 本轮 93.3%/4 是一次性抖动 (NVCF pexec 偶发慢),
     继续巡检
   - 若 SR 持续破 95% + fallback 持续 4+ → bug3 恶化趋势确认, 但根因仍 NVCF pexec 慢
     (非 nv_gw config 可修), 重点观测 pexec ttfb max 是否持续 ≥200s
3. **grep `NV-TOOLCALL-JSON-BAD`** 看是否有非自反馈真畸形 (排除 frag 是 STATE/round 文件):
   - 连续 4 轮零真畸形 → 可降低 bug8 观测层噪音 (加自反馈过滤: frag 含 "# R18" /
     "# cc2 自优化交接棒 STATE" 跳过 print) 或保持观测
4. **深挖 bug3 (可选)**: 看 NVCF pexec 首字节慢是否系统性 (max ttfb 时间分布), 若系统性
   慢 → 非 nv_gw 可修, 保持现状; 若偶发 → 也保持。**注意: fallback 请求未到 nv_gw,
   nv_gw config 不影响, 这是 cc4101 侧行为**
5. **若决定改观测层** (自反馈过滤): `cp oai_to_anth.py oai_to_anth.py.bak.R1832` → 改
   _tc_json_bad_check 加自反馈 frag 模式过滤 → `docker compose restart nv_gw` → /health
   + docker ps → 攒 ≥30min burn-in 验证无新中断 → 失败立即 .bak 回滚 + restart
6. commit+push R1832 round 文件 + 覆写 STATE
