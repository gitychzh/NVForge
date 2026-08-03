# R570 NOP 巡检轮 — HM2 nv_gw 自优化

**轮次**: R570
**方向**: R-nvonly (HM2 nv_gw 自优化)
**角色**: cc2 (HM2, opc2_uname)
**日期**: 2026-08-03 09:22 CST

## 数据 (改前必有数据 — 已注入轮前链路分析)

### 容器状态
- nv_gw: Up 19h, nv_gw_stable: Up 31h, cc4101: Up 9h, ms_gw: Up 4d, logs_db: Up 4d
- /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv]

### 30min 链路总览
- cc2 (cc4101-primary): **0 req** (session 间歇空闲, 无 cc2 评估样本)
- dsv4p_nv: 10 req, 4×200 + 6×429 (SR=40.0%, 全 hermes caller)
- 200 延迟: avg 5293ms, max 7073ms, min 4094ms (在 90s budget 内)
- finish_reason: tool_calls×3, stop×1 (无 zombie)
- fallback 发生率: f×10 (= 0 fallback)

### 30min 错误分类
- `all_tiers_exhausted|all_tiers_failed_in_mapped_tier` × 6 (avg_dur=2746ms)
  → 5key 全挂, NVCF 配额型, 非 nv_gw 故障

### 30min per-key × status (dsv4p)
- key2: 200×2 (4897ms, 5689ms)
- key3: 200×2
- 空 key (NVCF 侧拒绝): 429×6

### 30min per-egress-IP (dsv4p)
- 134.195.101.194: 2 req, 100% SR
- 203.10.96.139: 2 req, 100% SR
- 空 IP: 6 req, 0% SR (429, 全在 NVCF 配额侧拦截)

### 30min 按分钟趋势
- 00:55 429×1, 01:01 200×1+429×1, 01:05 200×2, 01:06 200×1+429×1,
  01:10 429×1, 01:15 429×1, 01:20 429×1

### 30min nv_tier_attempts
- 0 行 = KeyManager 全局冷却在 tier 层前拦截 (与 R545-R569 一致)

### 30min buffer/wait/keymanager 日志
- (无 buffer/wait/keymanager 日志)

## 判稳 + 行动

**NOP 巡检轮** — 不动码.

### 依据
1. **cc2 (cc4101-primary) 30min 0 req** → 铁律1 cc2 视角不满足, 不动码.
2. dsv4p_nv 10 req 4×200+6×429 = SR=40%, 看似低但本质是 NVCF 配额波动:
   - 6×429 全在"空 key/空 IP"= NVCF 侧配额拒绝, 非 nv_gw tier 故障
   - 命中 key2/key3 + 命中 134.195/203.10 IP 的请求 100% 200
   - avg_dur 200 = 5293ms (健康), 无 stream_total_deadline, 无 zombie
3. `all_tiers_exhausted` × 6 = 5key 全挂的 NVCF 配额型, 与 R545-R569 一致模式
4. nv_tier_attempts 0 行 = KeyManager 在 tier 层前拦截 (周期性 GLOBAL-COOLDOWN 180s/5min)
5. 无新错误类型, 无参数漂移 → 无介入必要

## 本轮改动
- 无 (NOP). 铁律1 cc2 视角不满足 → 不动码.

## 验证
- 0 restart → 无需 py_compile / curl 复测
- curl /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv
- docker ps: nv_gw Up 19h, nv_gw_stable Up 31h, cc4101 Up 9h, ms_gw Up 4d, logs_db Up 4d

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为
- 关注新错误类型或 key/IP 级故障再决定介入
- dsv4p_nv 小时级 SR <60% + cc2 流量恢复 → 评估 TIER_COOLDOWN_S 180s 是否过激
- all_tiers_exhausted 中段不恢复再评估 (当前 ~12/h 全 NVCF 配额型)
- 502 (peer-fb-skip) >=6/h + cc2 流量恢复 → 评估 dsv4p_nv fallback 策略

## 参数快照 (R570 未改)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_MS_FALLBACK_MODELS=glm5_2_nv,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450,
  NVU_BUFFER_PING_INTERVAL_S=30
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, PRIMARY_UPSTREAM_MODEL=dsv4p_nv,
  PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150

## Fallback 配置实测
- nv_gw: NVU_DISABLE_MS_FALLBACK=0 (ms fallback 启用, 仅覆盖 glm5_2_nv)
- NVU_MS_FALLBACK_MODELS=glm5_2_nv (不含 dsv4p_nv)
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (dsv4p_nv 跳过 peer fallback)
- → dsv4p_nv 全挂时 nv_gw 裸返 429/502, cc4101 层 ms_gw(glm5_2_ms) 兜底
