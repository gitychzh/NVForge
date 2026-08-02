# STATE — R505 (2026-08-03 05:35 CST)

## 当前轮基线
- 轮号: R505 | 类型: NOP 巡检 (0 改动 0 restart) | 上轮: R504
- 链路: cc2 → cc4101(PRIMARY=dsv4p_nv) → nv_gw(40006) → NVCF, fallback=ms_gw glm5_2_ms
- 窗口: 05:32 CST 注入 (21:04-21:30 UTC), 低谷窗口延续 (R502/R503/R504 同窗口)

## 本轮改了什么
- 无. NOP 巡检轮.
- cc2 (cc4101-primary) 30min 0 req (session 间歇空闲, 铁律1 不满足 → 不动码).

## 依据
- 30min 全 caller dsv4p_nv: 6×200 + 5×429 + 1×502 → SR=50.0% (12 req)
- 错误: all_tiers_exhausted ×5 (R268 起 192+ 轮历史一致) + zombie_empty_completion ×1 (R231 主动防御)
- nv_tier_attempts 30min 0 行 (429 在 tier 层前被 KeyManager 全局冷却拦截, tier=dsv4p_nv 只 1 tier 无 ring fallback)
- 模式与 R268-R503 一致, 无新错误, dsv4p_nv SR=50% 是 19-21点 NVCF 配额耗尽周期性行为, 非 nv_gw 侧可修复
- fallback 兜底正常 (cc4101 走 ms_gw glm5_2_ms, 12/12 fallback)
- 配置实测与 R475-R503 完全一致, 无漂移

## 验证
- 0 restart → 无需 py_compile / curl 复测
- curl /health: status=ok, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv]
- docker ps: nv_gw Up 15h, cc4101 Up 5h, nv_gw_stable Up 28h, ms_gw/logs_db Up 3 days

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为 (当前 0 buffer 样本)
- 关注新错误类型 (非 all_tiers_exhausted/zombie) 或 key/IP 级故障再决定介入
- dsv4p_nv 小时级 SR 持续 <60% + cc2 缓冲流量恢复后再评估切换 PRIMARY_UPSTREAM_MODEL 或 ring fallback
- all_tiers_exhausted 持续 >=5/h 且中段不恢复 再评估 TIER_COOLDOWN_S 180s 是否过激
- 502 再现 >=3/h 才介入 zombie 阈值 (当前 6h 低频, R476/R480-R503 一致)
- zombie_empty_completion >=3/h 再评估 zombie 阈值 (当前 content+reasoning<50)

## 参数快照 (本轮未改)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90,
  NVU_BUFFER_TOTAL_DEADLINE_S=450, NVU_BUFFER_PING_INTERVAL_S=30, NVU_STREAM_FULL_BUFFER=0,
  NVU_KEYMGR_429_BASE_COOLDOWN=120, NVU_KEYMGR_429_MAX_COOLDOWN=600,
  NVU_KEYMGR_CONN_BASE_COOLDOWN=30, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3,
  NVU_KEYMGR_CONN_LONG_COOLDOWN=120, NVU_KEYMGR_CONN_MAX_COOLDOWN=60
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_HEADER_TIMEOUT=400, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- deadline 链: 90s/attempt × 5 = 450s buffer < 470s cc4101 < 500s SDK idle
- settings.json: contextWindow=170000, autoCompactWindow=155000, API_TIMEOUT_MS=600000
