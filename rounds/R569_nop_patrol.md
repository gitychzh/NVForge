# R569 (HM2 自改) 优化报告 — NOP 巡检轮

## 📅 执行时间
2026-08-03 09:20 CST (轮前数据 09:18:32)

## 🎯 本轮目标
延续 R545-R568 巡检链, 判稳 → 无介入.

## 📊 轮前链路数据 (30min)
- **cc2 (cc4101-primary)**: 0 req (session 间歇空闲, 无 cc2 评估样本)
- **dsv4p_nv 全 caller**: 17 req, 12×200 + 5×429 (SR≈70.6%, 全 hermes caller)
  - per-key: k2=10×200, k3=2×200, (空)=5×429
  - per-egress-IP: 203.10.96.139=10×200(100%), 134.195.101.194=2×200(100%), (空)=5×429
  - 200 avg_dur=9175ms, max=25392ms, ttfb=8611ms
  - finish_reason: tool_calls×10, stop×2 (无 zombie)
- **唯一错误**: `all_tiers_exhausted` × 5 (avg_dur=3036ms, NVCF 配额型 429 累积)
- **nv_tier_attempts**: 0 行 (KeyManager 全局冷却在 tier 层前拦截)
- **buffer/wait 日志**: 无 (cc2 0 流量 → 无 buffer 触发)
- **fallback 发生率**: 0/17 (f=17, 全部不走 fallback)
- **2h SR 趋势**: 空 (无 10min 桶数据)

## 🧪 本轮改动
- **无 (NOP)**. 铁律1 cc2 视角不满足 (0 req) → 不动码.

## 📌 依据
1. cc2 0 流量 → 无 cc2 评估样本, 铁律1 "改前必有数据" 不满足
2. dsv4p_nv 17 req 12×200+5×429 = NVCF 配额波动区间, 与 R545-R568 完全一致模式
3. 唯一错误 `all_tiers_exhausted` 是 5key 全 429 后的预期路径 (NVCF 配额型, 非 nv_gw 故障)
4. 无新错误类型, 无参数漂移, 无 stream_total_deadline, 无 zombie → 无介入必要
5. 容器健康: nv_gw Up 19h, cc4101 Up 9h, health=ok, 5 key, default=glm5_2_nv

## ✅ 验证
- 0 restart → 无需 py_compile / curl 复测
- curl /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv
- docker ps: nv_gw Up 19h, cc4101 Up 9h, ms_gw Up 3 days, logs_db Up 3 days

## 🔮 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为
- 关注新错误类型或 key/IP 级故障再决定介入
- dsv4p_nv 小时级 SR <60% + cc2 流量恢复 → 评估 TIER_COOLDOWN_S 180s 是否过激
- all_tiers_exhausted 中段不恢复再评估 (当前 ~10/h 全 NVCF 配额型)
- 502 (peer-fb-skip) >=6/h + cc2 流量恢复 → 评估 dsv4p_nv fallback 策略

## 📋 参数快照 (R569 未改)
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

## 📡 Fallback 配置实测
- nv_gw: NVU_DISABLE_MS_FALLBACK=0 (ms fallback 启用, 仅覆盖 glm5_2_nv)
- NVU_MS_FALLBACK_MODELS=glm5_2_nv (不含 dsv4p_nv)
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (dsv4p_nv 跳过 peer fallback)
- → dsv4p_nv 全挂时 nv_gw 裸返 429/502, cc4101 层 ms_gw(glm5_2_ms) 兜底
