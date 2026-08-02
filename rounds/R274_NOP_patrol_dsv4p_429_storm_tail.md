# R274 — NOP 巡检轮 (dsv4p_nv primary, 一次性 429 风暴尾巴)

## 时间
2026-08-02 ~15:13 CST

## 链路状态
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, FALLBACK=ms_gw(40007) 已恢复, DEADLINE=470s.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, 5key×5IP buffer 450s, post266 DELEGATE 生效.
- 上轮容器: nv_gw 13h ago, cc4101 48min ago (本轮无 restart).

## 本轮数据 (30min 实时 DB 复查 ~15:13)
### 全 caller × model × status
| caller | model | status | count |
|---|---|---|---|
| hermes | dsv4p_nv(k3) | 200 | 27 |
| hermes | (mapped) | 429 | 1 |
| openclaw | dsv4p_nv(k4) | 200 | 1 |

- dsv4p_nv SR=28/29=96.6% (hermes+openclaw 合计).
- cc4101-primary (cc2 自己) 30min: **0 req** — cc2 session 间歇空闲, 无流量可优化.

### 唯一失败 eab966c9 (hermes caller, 非 cc2, 15:10:31)
- k3 → NVCF 429, egress=203.10.96.139/mihomo-7902, 无 retry-after 头.
- 级联 TIER_COOLDOWN 把 k1/k2/k4/k5 也标 cooling 180s (各自 count decayed>300s→reset count=1).
- 1547ms 声明 all_tiers_exhausted: 1 个真实 429 + 4 个被牵连.
- `nv_tier_attempts` 0 条 (无独立 tier attempt 记录, 走 pexec peek-retry path).
- 模式与 R269/R271 记录的"一次性 429 风暴窗口"一致, 非新错误, 非代码缺陷.

## 判稳
- cc2 primary 无流量 (0 req), 链路空闲健康.
- hermes/openclaw caller dsv4p_nv 28/29=96.6%, 唯一失败为瞬时 NVCF 429 风暴尾巴, 上轮 R273 已记录风暴窗口完全消散后偶发残留.
- 无新错误模式, 无 fallback (fallback 发生率 f=29, 全 false).
- → NOP 巡检轮, 0 改动 0 restart.

## 下一步
1. 持续观察 dsv4p_nv 在 cc2 primary 下 SR, 看是否有新风暴窗口.
2. 若 all_tiers_exhausted + TIER_COOLDOWN 牵连 4 健 key 反复出现 (>1/h), 考察
   TIER_COOLDOWN 是否对"单 key 429"过度牵连. 现状(单 429→全 cooling 180s)对
   孤立风暴可接受, 高频时再调.
3. cc2 session 恢复流量后复测自恢复闭环 (backoff 5s→attempt2).

## 参数快照 (本轮未改)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_UPSTREAM_URL=nv_gw:40006/v1/messages, FALLBACK_UPSTREAM_URL=ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150.
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s,
  TIER_COOLDOWN_S=180s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NV_GLM52_MODE_CHAIN= (空, post266).
