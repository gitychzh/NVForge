# R1776 — HM2 巡检轮:R1774 burn-in 观察,趋势强正 (不改代码)

> cc2 跨 session 接力。STATE.md (R1775) 指示本轮"拉 2-4h 长窗看 R1774 修复 B(breaker 时间窗)
> 是否真收敛 + SR 是否爬 95%+ + STREAM-STALL/UPSTREAM-ERROR 是否触发"。本轮按铁律"改前必有数据"
> 拉了 30min/2h/分桶数据。结论:**R1774 三层修复持续有效,趋势强正,真实干净窗 12min SR 100%**,
> 但样本太薄(9 req)不能算定论。**R1774 仍在 burn-in,叠加新改动违反小步快走 → 本轮巡检不改代码**, HM2 only。

## 链路
```
cc2 → cc4101(4101, 透传 /v1/messages) → nv_gw(40006, glm5_2_nv) → NVCF
                                  ↘ ms_gw(40007, glm5_2_ms) [breaker OPEN 后兜底]
```
settings.json: `ANTHROPIC_BASE_URL=http://127.0.0.1:4101` (cc4101→nv_gw, 正反馈模式)。
本轮 cc2 走 cc4101→nv_gw 稳定跑完全程(多轮工具调用不崩) = R1774 修复 A 持续有效。

## 时间线 (本轮拉数据时刻 15:46 CST)
- 15:30:12  nv_gw restart (R1774 bind-mount 源码生效)
- 15:33:20  R1774 commit e11e080
- 15:38:22  cc4101 restart (R1774 cc4101 circuit.py 生效)
- 15:38:33  cc4101 primary-fail breaker OPEN → 1 次 fallback 到 ms_gw (R1774 修复 B 首次真触发)
- 15:46:02  本轮拉数据 — R1774 部署 ~13min, burn-in 后真实干净窗 ~12min

## 改前数据 (15:46 拉取)

### 30min 窗 (15:16-15:46, R1774 部署前后混合)
| status | count | error_type 明细 |
|---|---|---|
| 200 | 47 | (success) |
| 502 | 6  | stream_first_byte_timeout×3, stream_no_content_gap×2, zombie_empty_completion×1 |

SR = 47/53 = **88.7%**, fallback 30min = 1 次 (15:38, 大小写敏感 grep 修正后)。

### 30min 分桶趋势 (request 级, 按分钟)
- 15:12-15:16: 全 200 (14 success)
- 15:17-15:29: 200 为主, 零星 502 (15:17/15:18/15:23/15:26/15:29 各 1)
- 15:30-15:33: 502@15:33 (最后失败), 之后 15:34-15:38 全 200
- **15:34 起 (近 12min) 零请求级失败**

### 最近 12min 纯净窗 (R1774 完全生效后, 真实 burn-in 态)
| status | count |
|---|---|
| 200 | 9 |

**请求级 SR = 9/9 = 100%**。样本 9 req, 统计薄但趋势干净。

### 2h 长窗 (R1774 部署前后混合, 看整体)
| status | count | error_type 明细 |
|---|---|---|
| 200 | 157 | (success) |
| 502 | 21  | stream_first_byte_timeout×8, stream_no_content_gap×7, zombie_empty_completion×4, all_tiers_exhausted×2 |

SR = 157/178 = **88.2%**。失败模式稳定: first_byte_timeout + no_content_gap 占主 (15/21=71%), 全上游 NVCF 偶发, 非 nv_gw 代码 bug。

### tier_attempts (连接级证据)
- 30min: integrate_success×26, pexec_success×9, **integrate_SSLEOFError×8, pexec_SSLEOFError×4** (共 12 SSLEOFError)
- **SSLEOFError 时间分布 (UTC→CST)**: 05:55/06:24 单点; **07:34-07:38 (=15:34-15:38 CST) 集中 burst**, 15:38 后零 → 全部集中在 R1774 重启 churn 窗口, 非稳态
- 最近 12min tier 级仍有 4 SSLEOFError (3 integrate + 1 pexec), **但请求级全 200** = tier failover 成功吸收, 按设计工作
- 结论: 上游 NVCF 连接偶发 SSL EOF, 被 tier/key failover 兜住, 不影响请求成功

### R1774 三层修复持续有效性核查
| 修复 | 观测点 | 本轮证据 |
|---|---|---|
| A: wire graceful end (治当前请求崩) | SSE malformed 零复现 + cc2 不崩 | 2h grep `content_block.*(stop\|delta).*repeat\|malformed\|parse.*json.*sse` = **0**; cc2 本轮多轮工具调用全程不崩 ✓ |
| B: breaker 时间窗语义 (治永 CLOSED) | cc4101 breaker 真 OPEN 过 | 15:38:33 `breaker-OPEN triggered → fallback ms_gw` — **真 OPEN, 非永 CLOSED, 修复 B 工作** ✓; nv_gw 自身 breaker 30min 仅 1 条 state=('CLOSED',1,0), 失败密度不够 5/300s 未 OPEN (正常) |
| C: cc4101 stall 观测 | STREAM-STALL-FAIL / UPSTREAM-ERROR-SEEN | 2h grep 全空 — 失败密度低观测点未触发, 正常 (不能据此判失效) |

### nv_gw 健康
- `curl /health`: `{"status":"ok", "nv_num_keys":5, ...}` ✓
- `docker logs nv_gw --tail 5`: NV-GLM52-SUCCESS + NV-PEEK-OK (健康首字节 peek; 一条 37s 首字节但 prebuffer 1191b 仍成功)
- 无活跃流卡死, 无异常堆栈

## 决策: 本轮不改代码 (巡检轮)

**STATE 决策分支命中: SR 趋势强正 + R1774 修复 B 真 OPEN 过 → 接近"R1774 成功"分支, 但样本太薄需继续观测。** 不改理由:

1. **R1774 仍在 burn-in**: 部署 ~13min, 真实干净窗仅 12min/9 req。SR 30min 88.7% 全是 15:34 前失败 + 重启 churn 拖低, 真实 burn-in 态 100% 但统计薄。叠加新改动违反小步快走 + 会污染 R1774 效果观测。
2. **R1774 修复 B 已被实测验证工作**: cc4101 breaker 15:38 真 OPEN (非永 CLOSED) → 证明时间窗语义落地。但只触发 1 次, 需更长窗口看它是否在失败密度够时正确 OPEN、密度降时正确恢复。
3. **fallback 近零**: 30min 仅 1 次 (15:38 breaker 事件), 近 8min 零。负向核心指标健康。STATE 铁律"让 breaker 几乎不 OPEN 而非调高阈值假装不 OPEN" → 当前无需动 breaker 阈值。
4. **失败全上游 NVCF 偶发**: first_byte_timeout/no_content_gap/zombie = NVCF 连接级 (SSLEOFError 已证) 或空完成, 非 nv_gw 代码 bug。R1770 已巡检否决微调 timeout, 本轮无新数据推翻该否决。
5. **SSE 病根持续零复现**: R1774 修复 A 持续有效, 无数据动 handlers.py 拼接逻辑。

## 下一轮建议 (R1777)
1. **继续观测长窗** (目标再 30-60min 干净 nv 流量, 凑够 ≥30 req 真实 burn-in 态):
   - 确认请求级 SR 持续 ≥95% (当前 12min 100% 但仅 9 req)
   - 看 cc4101 breaker 是否在失败密度够时正确 OPEN、降时正确恢复 (R1774 修复 B 收敛性)
   - 看 tier 级 SSLEOFError 是否仍被 failover 全吸收 (请求级不挂)
2. **决策分支**:
   - 若 30-60min 后 SR 持续 ≥95% + breaker 行为正常 → **R1774 宣告成功**, 转纯巡检或找下一个优化点
   - 若 SR 回落 <93% 且失败模式仍是 first_byte_timeout/no_content_gap → 确认上游 NVCF 偶发, 考虑 tier 调度策略或连接复用层 (但需先定位 SSLEOFError 是否与连接池/keepalive 相关, 查 upstream.py 连接处理)
   - 若 breaker 异常 (永 OPEN 或永 CLOSED) → 才考虑动 breaker 阈值/窗口
3. **不预先改**: 铁律"改前必有数据", 当前无新失败模式要求立即动代码。

## 不改的东西
- 不改 handlers.py SSE 拼接 (R1774 已治, 持续零复现)
- 不改 nv_breaker/circuit (R1774 刚改, 修复 B 已验证工作, 需更长窗口看收敛)
- 不调 TIER_TIMEOUT_BUDGET_S/UPSTREAM_TIMEOUT (R1770 否决, 无新数据推翻)
- 不改 ms_gw (铁律: 40007 是重启窗口热备)
- 不改 HM1 (铁律)

## 当前 nv_gw 参数快照 (R1774 部署后, R1776 确认无漂移)
```
TIER_TIMEOUT_BUDGET_S=180  UPSTREAM_TIMEOUT=66  MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25  TIER_COOLDOWN_S=25  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180  NVU_BIG_INPUT_THRESHOLD=250000
NVU_MS_FALLBACK_ENABLED=1  NVU_MS_FALLBACK_FAIL_THRESHOLD=5  (R1774: 15→5)
NVU_MS_FALLBACK_SKIP_S=30  NVU_MS_FALLBACK_MODEL=glm5_2_ms
NVU_BREAKER_WINDOW_S=300  (源码默认, env 未覆盖)
CC4101_PRIMARY_FAIL_THRESHOLD=3  (R1774: 8→3)
CC4101_PRIMARY_SKIP_S=30
CC4101_BREAKER_WINDOW_S=300  (源码默认)
```
注: R1774 wire graceful end 在 oai_to_anth.py finish() + handlers.py 调用处;
breaker 时间窗在 nv_breaker.py + cc4101/circuit.py。下轮重点观测这俩在长窗的收敛性。
