# R-nvonly-post137 — NOP 巡检轮 (2026-08-02 08:11 CST)

## 本轮判定
- **NOP 巡检轮**. cc2 (cc4101-primary) 30min 0 req 无流量, 无数据可判 SR, 链路健康无故障.
- 0 改动, 0 重启, 0 commit (仅本轮文档 + STATE).

## 轮前链路分析 (08:10:32 CST, 注入数据)
### 30min 链路总览 (caller × model × status)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 5 |
| hermes | dsv4p_nv | 429 | 5 |

### 30min 按模型 SR
- dsv4p_nv SR=50.0% (5/10) — hermes caller, 非 cc2 链路

### 30min cc4101-primary (cc2 的请求)
- 0 req (session 轮前无流量产生)

### 30min 错误分类
- all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 5 | avg 1323s

### 30min dsv4p 按分钟趋势 (UTC)
- 23:45-50: 429 × 1 (周期性 5min 一发)
- 23:55-56: 200 × 5 (恢复)

## 判稳依据
1. cc2 (cc4101-primary) 30min 0 req — 无流量 = 无数据 = 无故障, 链路健康.
2. dsv4p_nv SR=50% 是 NVCF 侧 dsv4p 周期性限流 (5min 一发 429 all_tiers_exhausted),
   hermes caller 打的, **非 cc2 链路** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
3. glm5_2_nv 连续 post100-post137 (38 轮) 无故障扩散.
4. fallback 发生率 f=10 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).

## 健康验证 (08:11 CST)
| 项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d ✓ |
| nv_gw env | DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, STAIRS=90×5, DEADLINE=450s, UPSTREAM_TIMEOUT=90s ✓ |
| cc4101 env | DEADLINE=470, HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK=ms_gw:40007 ✓ |

## 参数快照
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, STAIRS=90,90,90,90,90, TOTAL_DEADLINE=450s, UPSTREAM_TIMEOUT=90s, TIER_TIMEOUT_BUDGET=180s
- cc4101: STREAM_TOTAL_DEADLINE=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 属 NVCF 侧 + hermes caller, 非本轮职责 (只改 HM2 nv_gw).
- glm5_2_nv 链路连续 38 轮稳定, 无需调整.
