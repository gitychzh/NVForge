# R903 cc2 NOP 巡检轮 — 主链 100% 干净 连续第 12 轮

- 日期: 2026-08-07 (~08:52 CST), cc2 HM2
- 轮次: **R903 (NOP 巡检 / 不改码)**
- 判稳: cc2 主链路连续第 12 轮 100% SR 干净 (R892~R903)

## 结论
三 scoped 容器 health 全 ok; cc2 主链 (nv_gw:40006, cc4101-primary) 30min
实拉 = **135/135 = 100% SR, 0 bad**。5 条 bad (502: all_tiers_exhausted ×4
+ stream_absolute_cap ×1) + 23 条 bad-fid attempt (52e1ddb6) 100% 属 hermes 线
(request_id JOIN 铁证, cc2 主链 0 参考), 越 cc2 范围。**不改码。**

## 数据 (live DB 实拉 ≈2026-08-07 08:52 CST)

### cc2 主链 (cc4101-primary → nv_gw:40006)
- **实拉: 135/135 全 200, 0 bad (100% SR)** — `count(*) WHERE status=200` = 135,
  bad = 0 (`caller='cc4101-primary' AND status!=200` → 0 条)。
- per-key (nv_tier_attempts JOIN 30min): 主链请求全走健康 fid **281478d0**,
  error_type=pexec_success (5 key × 27~28 ≈ 138 次), 0 错误。0 条 52e1ddb6 进 cc2 候选池。
- 距上轮 (R902 131/131) 主链依旧 100% 干净, 无 error_type 新类。

### 越界 hermes 线 (不算 cc2 主链)
- 30min 所有 bad = `caller=hermes`:
  - `all_tiers_exhausted ×4` (avg 178883ms ≈ 179s, 触最外层 180s budget)
  - `stream_absolute_cap ×1` (avg 177533ms)
- 坏 fid 52e1ddb6 attempts (23 条, error: NVCFPexecRemoteDisconnected ×14, NVCFPexecTimeout ×3,
  empty_200 ×2, 504/529/budget ×4) 全走 `dsv4f0731_nv` tier 但 **request_id JOIN 铁证**:
  23 条全 caller=**hermes**, cc2 主链 0 参考 (越界容器 40666 hermes 线)。

### buffer / fallback
- buffer (dsv4f0731_nv, cc4101-primary): 全 attempt=1/5 成交, success_tool_call,
  7-12s elapsed, 0 重试 / 0 429 / 0 cooldown。
- fallback (cc2 线): 0 次, < 5% 目标远低于。

### 容器 health
- cc4101(4101): ok, primary=dsv4f0731_nv, Up 5 hours
- nv_gw(40006): ok, passthrough, 5 keys, Up 5 hours
- dsv4p_nv40066: ok, passthrough, Up 5 days

## 验证
- curl 4101/40006/40066 → 全 ok (200)。
- 30min nv_requests cc4101-primary 实拉 = 135/135 (0 bad)。
- 52e1ddb6 归属 JOIN 铁证: 两路独立查询 (非-success 全量 + 52e1ddb6 精确) 均 0 条 cc2,
  23 条全 caller=hermes。
- per-key 主链全 281478d0 健康, 0 error。

## 关键判断
主链连续 12 轮 (R892 139/139, R893 153/153, R894 143/143, R895 137/137, R896 134/134,
R897 126/126, R898 125/125, R899 124/124, R900 126/126, R901 127/127, R902 131/131,
R903 135/135) 100% SR 干净。bad 请求 + bad fid 100% 属 hermes caller 活动, 容器级分离持续奏效。
**不改码**: ①主链 SR 100% 无优化需求; ②坏请求/坏 fid 全属 hermes 越 cc2 范围; ③当前机制已达稳态。

## 参数快照 (env, 本轮未改)
- nv_gw(40006): NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_MAX_RETRIES=5 (90×5=450s), NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- cc4101(4101): PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, primary=dsv4f0731_nv,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms (铁律4 不主动改 fallback)
- config.py: dsv4f0731_nv function_ids=[281478d0-f307-49f4-9e0f-080b63b16c47] (主链 R-fid0731);
  dsv4f_nv function_ids=[52e1ddb6-c745-4802-93f5-ba012d04c336]

## 下一步
- 主链 cc2 连续 12 轮 100% 干净, 下轮预期维持 NOP。
- 优先监控: ①主链 dsv4f0731 rotation 持续只出健康 fid 281478d0; ②hermes 线 all_tiers_exhausted
  + 52e1ddb6 泄漏活动 — 若污染进 40006/40066 候选池再介入 (目前 0 泄漏); ③fallback 触发率 <5% (当前 0)。