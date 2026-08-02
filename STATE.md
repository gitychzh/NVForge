# R431 — NOP 巡检轮 (2026-08-03 01:25 CST)

## 本轮改了什么
- 0 改动 0 restart. NOP 巡检轮.

## 依据
- cc2 (cc4101-primary) 30min 0 请求 (session 间歇空闲, 与 R430 同模式), 0 错误 0 fallback.
- dsv4p_nv 全 caller 30min SR=80.0% (12/15), 3×429 all_tiers_exhausted (avg 2191ms),
  较 R430 的 63.6% 回升, 在历史波动区间内 (R420=86.4% → R429=69.2% → R430=63.6% → R431=80.0%).
- per-key (dsv4p 200): k2×11, k3×1 = 12×200; 3×429 无 key 归属 (空 IP = 全 key cooling 时进不来).
- per-egress-IP: 203.10.96.139 11/11=100%, 134.195.101.194 1/1=100%, 空 IP 3req 全 429.
- 时间分布: 16:50/16:55/17:00 三连 429, 17:05-17:16 连续 12×200 恢复.
- 200 延迟 avg 10226ms, max 16649ms, avg_ttfb 9694ms (正常波动).
- 200 finish_reason: tool_calls×8, stop×4 (无 zombie/end_turn 异常).
- 30min buffer/wait/keymanager 日志: 无 (cc4101-primary 0 req 未触发 buffer caller).
- 错误类型无新增, 与 R268-R430 一致 (一百六十余轮一致).
- glm5_2_nv 30min 0 req → 切 PRIMARY_UPSTREAM_MODEL 不满足"改前必有数据"铁律, 暂不切.

## 验证
- 容器健康: nv_gw (11h), cc4101 (33min), nv_gw_stable (23h), ms_gw/logs_db Up.
- curl /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv.
- 0 restart → 无需 py_compile / 复测.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
- dsv4p_nv 小时级 SR 持续 <70% + cc2 缓冲流量恢复后再评估是否切换 PRIMARY_UPSTREAM_MODEL.
- all_tiers_exhausted 持续 >=5/h 且后半段不恢复 再评估 buffer/KeyManager 参数.

## 参数快照 (本轮未改)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_HEADER_TIMEOUT=400, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- deadline 链: 90s/attempt × 5 = 450s buffer < 470s cc4101 < 500s SDK idle
- settings.json: contextWindow=170000, autoCompactWindow=155000, API_TIMEOUT_MS=600000
