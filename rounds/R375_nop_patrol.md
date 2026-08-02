# R375: NOP 巡检轮 (cc2 0req, dsv4p_nv SR=27.3% 3/11, all_tiers_exhausted×8[5×429+3×NV-TIER-SKIP 1ms] + stream_first_byte_timeout×1, 九十八轮一致)

## 轮前链路分析 (2026-08-02 21:57 CST, 接棒 R374)

### 当前配置 (未变)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  MIN_OUTBOUND_INTERVAL_S=10, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
  UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3

### 30min 链路总览 (caller × model × status)
| caller | model | status | count | avg_dur |
|---|---|---|---|---|
| hermes | dsv4p_nv | 200 | 3 | 9700 |
| hermes | dsv4p_nv | 429 | 5 | 1766 |
| other | dsv4p_nv | 502 | 3 | 1 |
| other | glm5_2_nv | 200 | 2 | — |
| other | glm5_2_nv | 502 | 1 | 29952 |

### 30min 按模型成功率
- dsv4p_nv: SR=27.3% (3/11)
- glm5_2_nv: SR=66.7% (2/3)

### 30min cc4101-primary 专属 (cc2 的请求)
- 0 req (session 间歇空闲, 链路空闲健康).

### 30min 错误分类 (type × sub × count × avg_dur)
- all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 8 | 1104ms
- stream_first_byte_timeout | (空) | 1 | 29952ms

### 30min per-key × status (dsv4p)
- key2 → 3×200 (avg 9700)
- 空 key → 5×429 (1766ms) + 3×502 (1ms)

### 30min per-egress-IP (dsv4p)
- 203.10.96.139 → 3× (100 avg)
- 空 → 8× (0)

### 30min dsv4p 200 延迟/Token
- avg_dur=9700, max=11546, min=7774, avg_ttfb=8289, avg_in=0, avg_out=0

### 30min dsv4p 200 finish_reason 分布 (zombie 诊断)
- tool_calls×2, stop×1 (无 zombie)

### 30min fallback 发生率
- f×14 (全部 false, 0 fallback)

### 30min dsv4p 按分钟趋势
- 13:30 429×1, 13:33 502×3 (NV-TIER-SKIP 1ms), 13:35 429×1, 13:40 200×1,
  13:41 200×2, 13:45 429×1, 13:50 429×1, 13:55 429×1

### buffer/wait/keymanager 日志摘要
- (无 buffer/wait/keymanager 日志, cc2 无 buffer 流量)

## 根因 (沿用 R353-R374 分析, 非代码缺陷)

### 结论
- **非 nv_gw 代码缺陷, 无需本轮改码**.
- all_tiers_exhausted (8): 细分 5×429 (1766ms, NVCF dsv4p function 配额瞬时空位) +
  3×502 (1ms, NV-TIER-SKIP 全 cooling 瞬拒). 均发生在非缓冲 caller (hermes + other),
  cc2 缓冲 caller 不受影响 (走 buffer 5key 轮转 + WaitQueue).
- NV-TIER-SKIP (upstream.py:1676-1693): 全 5 key cooling 时直接 continue 跳过 tier, 0 attempt 1ms 502,
  发生在 agent_type=_nv 非缓冲 caller, 设计如此 (不等 NVCF 恢复, 快速返 5xx 让上层决策).
- 429: NVCF dsv4p function 配额瞬时空位, 低频偶发, buffer 5key 轮转 + KeyManager 指数退避自恢复.
- stream_first_byte_timeout: glm5_2_nv other caller 单发 502 29952ms, 非 cc2 流量, 自恢复.
- dsv4p 错误类型集合 = {all_tiers_exhausted}, 与 R268-R374 一致 (九十八轮一致).
- 本轮 SR 27.3% 较 R374 27.3% 持平 (样本极小 11 req, NVCF 429 波 5× + NV-TIER-SKIP 3×,
  全部非缓冲 caller, cc2 不受影响, 自然波动).

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv SR=27.3% (3/11) 与 R374 27.3% (3/11) 完全持平.
- dsv4p 错误类型无新增, 与 R268-R374 一致 (九十八轮一致).
- 0 改动 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR (cc2 走 buffer 路径).
- 关注是否出现新错误类型 (非 all_tiers_exhausted/stream_first_byte_timeout) 或 key/IP 级故障, 再决定是否介入.
- all_tiers_exhausted 若从低频偶发转为持续 429 波 (>=5/h), 再评估 buffer 轮转/KeyManager 退避参数.
- NV-TIER-SKIP 若在 cc2 缓冲 caller 上出现 (理论上不应), 再评估 buffer 与 NV-TIER-SKIP 路径关系.
