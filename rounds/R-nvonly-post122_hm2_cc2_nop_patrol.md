# R-nvonly-post122 — NOP 巡检轮 (2026-08-02 07:30 CST)

## 轮前链路分析注入数据 (07:28 CST)

### 30min 链路总览 (caller × model × status)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |
| openclaw | dsv4p_nv | 200 | 1 |

### 30min 按模型成功率
- dsv4p_nv SR=44.4% (4/9)

### 30min cc4101-primary 专属 (cc2 的请求)
- **0 req** (session 轮前无流量产生, 无数据可判 cc2 SR)

### 30min 错误分类 (type × sub × count × avg_dur)
- all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 5 | 1313ms

### 30min per-key × status (dsv4p)
- key2: 200×3 (15377ms avg)
- key3: 200×1 (2934ms)
- (空 key): 429×5 (1313ms)

### 30min per-egress-IP (dsv4p)
- (空): 5 req, 0 SR
- 203.10.96.139: 3 req, 100% SR
- 134.195.101.194: 1 req, 100% SR

### 30min fallback 发生率
- f=9 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复)

### 30min dsv4p 按分钟趋势 (UTC)
| 分钟 | status | count |
|------|--------|-------|
| 23:00 | 429 | 1 |
| 23:04 | 200 | 1 |
| 23:05 | 429 | 1 |
| 23:10 | 429 | 1 |
| 23:15 | 200 | 2 |
| 23:16 | 200 | 1 |
| 23:20 | 429 | 1 |
| 23:25 | 429 | 1 |

周期性 5min 一发 429, 间夹 200, NVCF 侧 dsv4p 限流模式.

## 判稳结论: NOP 巡检轮
- cc2 (cc4101-primary) 30min **0 req** → 无流量无数据, 链路健康无故障
- glm5_2_nv 连续 post100→post121 (22 轮) 无 dsv4p 故障扩散到 glm5_2_nv
- dsv4p_nv SR=44.4% (4/9) 是 hermes+openclaw caller 打 dsv4p 的 NVCF 侧限流, **非 cc2 链路**
  (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
- 0 cc2 tier error, 0 cc2 buffer/wait/error 日志, 0 stream_total_deadline (6h)
- 容器全 Up 5h, env 配置正确 (fallback 已恢复, buffer 5×90s=450s, cc4101 deadline 470s)
- 0 改动, 0 重启

## 健康验证 (07:30 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |
| stream_total_deadline (6h) | 0 ✓ |

## 参数快照 (2026-08-02 07:30 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), BUFFER_MAX_RETRIES=5,
  BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s,
  TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes/openclaw caller, 非本轮职责.
- glm5_2_nv 链路连续 23 轮稳定, 无需调整.
