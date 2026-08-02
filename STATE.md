# STATE — R497 (2026-08-03 05:12 CST)

## 当前轮基线
- 轮号: R497 (NOP 巡检轮, 连续低谷窗口延续)
- 上一轮: R496 (NOP, dsv4p_nv 30min SR=33.3%, 6h 69.6%)
- 本轮改动: 0 改动 0 restart
- 链路: cc2 → cc4101(4101) → nv_gw(40006, dsv4p_nv) → NVCF, fallback ms_gw(40007, glm5_2_ms)

## 本轮数据 (05:06 CST 实测)
### 30min 全 caller dsv4p_nv
- 10 req: 2×200 + 7×429 + 1×502 → SR=20.0% (低谷窗口 UTC 20-21h)
- 错误: all_tiers_exhausted ×7 (历史一致, R268 起 190+ 轮) + zombie_empty_completion ×1 (nv_gw 主动防御)
- cc4101-primary (cc2) 30min 0 req (session 间歇空闲)

### 6h dsv4p_nv 小时级 SR
- 15h=82% → 16h=84% → 17h=74% → 18h=69% → 19h=27% → 20h=25% → 21h=40%
- 昼夜周期性衰减, 与 R490-R496 一致

## 本轮改了什么 + 依据 + 验证
- 0 改动 0 restart.
- 依据: cc2 0 流量 → 铁律1 (改前有数据) 不满足, 不动码.
- dsv4p_nv 低谷窗口属 NVCF 侧配额/IP 漂移, 非 nv_gw 可修复.
- zombie_empty_completion ×1 是 R2311 起的 zombie 主动防御 (空响应<50字符 abort 触发 fallback), 非新故障.
- 配置无漂移, 容器健康 (nv_gw Up 15h, cc4101 Up 4h, /health ok 5 keys).

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复观察 buffer 路径.
- zombie_empty_completion >=3/h 再评估 zombie 阈值.
- dsv4p_nv 6h SR 持续 <60% + cc2 流量恢复后再评估 PRIMARY_UPSTREAM_MODEL 切换或 ring fallback.
- all_tiers_exhausted >=5/h 持续不恢复再评估 TIER_COOLDOWN_S 180s.

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
