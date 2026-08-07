# R900 cc2 NOP 巡检轮 — 主链 100% 干净 连续第 9 轮

- 日期: 2026-08-07 (~09:00 CST), cc2 HM2
- 轮次: **R900 (NOP 巡检 / 不��码)**
- 判稳: cc2 主链路连续第 9 轮 100% SR 干净 (R892~R900)

## 结论
三 scoped 容器 health 全 ok; cc2 主链 (nv_gw:40006, cc4101-primary) 30min
实拉 = **126/126 = 100% SR, 0 bad**。6 条 all_tiers_exhausted (502) 全属 hermes
线, 越 cc2 范围。**不改码。**

## 数据 (live DB 实拉 + prompt 注入链路数据, ≈2026-08-07 09:00 CST)

### cc2 主链 (cc4101-primary → nv_gw:40006)
- **实拉: 126/126 全 200, 0 bad (100% SR)** — `count(*) FILTER (WHERE status=200)` = 126, bad = 0。
- prompt 注入 caller×model×status: `cc4101-primary|dsv4f0731_nv|200|124` (0 bad)。
- 距上轮 (R899 124/124) 主链依旧 100% 干净, 无 error_type 新类。

### 越界 hermes 线 (不算 cc2 主链)
- 30min 所有 bad = `all_tiers_exhausted ×6 (avg 178.4s)`, 全在 `hermes|dsv4f0731_nv|502`。
- dsv4f0731_nv 整体 SR = 95.4% (124/130), 6 条 bad 全 hermes caller, cc2 主链无贡献。

### per-key 健康 (nv_tier_attempts 30min, dsv4f0731_nv 单模型)
- 各 key pexec_success 24-26, 偶发 RemoteDisconnected/Timeout/529/504/empty_200, 未见 key 雪崩。
- buffer/wait/keymanager 无异常日志 (buffer 全 attempt=1/5 成交, 0 重试 / 0 429)。

### fallback
- cc2 线 fallback 0 次 (30min), < 5% 目标远低于。

### 容器 health
- cc4101(4101): ok, primary=dsv4f0731_nv, Up 5 hours
- nv_gw(40006): ok, passthrough, 5 keys, Up 5 hours
- dsv4p_nv40066: ok, passthrough, Up 2 days

## 验证
- curl 4101/40006/40066 → 全 ok (200)。
- 30min nv_requests cc4101-primary 实拉 = 126/126 (0 bad)。
- prompt 注入链数据与实拉一致 (cc2 主链 0 bad)。

## 关键判断
主链连续 9 轮 (R892 139/139, R893 153/153, R894 143/143, R895 137/137, R896 134/134,
R897 126/126, R898 125/125, R899 124/124, **R900 126/126**) 100% SR 干净。
6 条 all_tiers_exhausted (502) 100% 属 hermes caller 活动, 未进 cc2 主链候选池。
**不改码**: ①主链 SR 100% 无优化需求; ②坏请求全属 hermes 线越 cc2 范围; ③容器级分离持续奏效。

## 参数快照 (env, 本轮未改)
- nv_gw(40006): NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_MAX_RETRIES=5 (90×5=450s)
- cc4101(4101): PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, primary=dsv4f0731_nv,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms (铁律4 不主动改 fallback)
- config.py: dsv4f0731_nv function_ids=[281478d0-f307-49f4-9e0f-080b63b16c47] (主链 R-fid0731);
  dsv4f_nv function_ids=[52e1ddb6-c745-4802-93f5-ba012d04c336]

## 下一步
- 主链 cc2 连续 9 轮 100% 干净, 下轮预期维持 NOP。
- 优先监控: ①主链 dsv4f0731 rotation 持续只出健康 fid; ②hermes 线 all_tiers_exhausted 活动 —
  若污染进 40006/40066 候选池再介入 (目前 0 泄漏); ③fallback 触发率保持 <5% (当前 0)。