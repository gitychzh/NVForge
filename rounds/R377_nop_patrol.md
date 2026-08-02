# R377: NOP 巡检轮 (cc2 0req, dsv4p_nv SR=60.0% 6/10, all_tiers_exhausted×4[4×429 1895ms], 一百轮一致)

## 轮前链路分析 (2026-08-02 22:05 CST, 接棒 R376)

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
| hermes | dsv4p_nv | 200 | 6 | 10133 |
| hermes | dsv4p_nv | 429 | 4 | 1895 |

### 30min 按模型成功率
- dsv4p_nv: SR=60.0% (6/10)

### 30min cc4101-primary 专属 (cc2 的请求)
- 0 req (session 间歇空闲, 链路空闲健康).

### 30min 错误分类 (type × sub × count × avg_dur)
- all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 4 | 1895ms

### 30min per-key × status (dsv4p)
- key2 → 6×200 (avg 10133)
- 空 key → 4×429 (1895ms)

### 30min per-egress-IP (dsv4p)
- 203.10.96.139 → 6× (100 avg)
- 空 → 4× (0)

### 30min dsv4p 200 延迟/Token
- avg_dur=10133, max=13595, min=5680, avg_ttfb=9087, avg_in=0, avg_out=0

### 30min dsv4p 200 finish_reason 分布 (zombie 诊断)
- tool_calls×4, stop×2 (无 zombie)

### 30min fallback 发生率
- f×10 (全部 false, 0 fallback)

### 30min dsv4p 按分钟趋势
- 13:35 429×1, 13:40 200×1, 13:41 200×2, 13:45 429×1, 13:50 429×1, 13:55 429×1,
  14:00 200×1, 14:01 200×2

### buffer/wait/keymanager 日志摘要
- (无 BUFFER-/WAIT- 日志, cc2 无 buffer 流量, 30min 无 keymanager 事件)

## 根因 (沿用 R353-R376 分析, 非代码缺陷)

### 结论
- **非 nv_gw 代码缺陷, 无需本轮改码**.
- all_tiers_exhausted (4): 全部 4×429 (avg 1895ms, NVCF dsv4p function 配额瞬时空位),
  发生在非缓冲 caller (hermes), cc2 缓冲 caller 不受影响 (走 buffer 5key 轮转 + WaitQueue).
- 本轮无 NV-TIER-SKIP 502 (R376 有 3×), 说明本轮无全 key cooling 瞬拒, 仅 function 级 429 波.
- 429: NVCF dsv4p function 配额瞬时空位, 低频偶发, buffer 5key 轮转 + KeyManager 指数退避
  + ProbeWorker + decayed reset 自恢复 (R268-R376 验证有效).
- dsv4p 错误类型集合 = {all_tiers_exhausted}, 与 R268-R376 一致 (一百轮一致).
- 本轮 SR 60.0% (6/10) 较 R376 41.7% (5/12) 上升, 样本极小自然波动 (成功 6 vs 5,
  失败 4 vs 7, 均 NVCF 429 波, 无 NV-TIER-SKIP, cc2 不受影响).

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv SR=60.0% (6/10) 较 R376 41.7% (5/12) 上升, 样本极小自然波动.
- dsv4p 错误类型无新增, 与 R268-R376 一致 (一百轮一致).
- 0 改动 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR (cc2 走 buffer 路径).
- 关注是否出现新错误类型 (非 all_tiers_exhausted/stream_first_byte_timeout) 或 key/IP 级故障, 再决定是否介入.
- all_tiers_exhausted 若从低频偶发转为持续 429 波 (>=5/h), 再评估 buffer 轮转/KeyManager 退避参数.
- NV-TIER-SKIP 若在 cc2 缓冲 caller 上出现 (理论上不应), 再评估 buffer 与 NV-TIER-SKIP 路径关系.

## 参数快照 (本轮未改, 实测注入)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
  UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3
