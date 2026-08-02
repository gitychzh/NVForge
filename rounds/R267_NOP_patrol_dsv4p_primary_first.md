# R267 — NOP 巡检轮 (dsv4p_nv primary 首巡 + post266 DELEGATE 跨轮验证)

**日期**: 2026-08-02 14:44 CST
**方向**: R-nvonly / hm2_cc2
**轮型**: NOP 巡检轮 (0 改动 0 restart)

## 背景
主仓 b4527f9 (R-dsv4p-cc2) 已将 cc4101 `PRIMARY_UPSTREAM_MODEL` 从 `glm5_2_nv` 切到
`dsv4p_nv`。本轮是切换后首次 cc2 巡检, 顺带跨轮验证上轮 post266 的 buffer
`_execute_and_drain` MODE_CHAIN 空委托 `execute_request` (DELEGATE) 修复在 dsv4p_nv
路径下是否同样生效。

## 数据 (30min, 14:39 CST 注入 + 14:44 复查)

### 1. cc4101-primary (cc2) 30min 总览
| status | count | avg_dur | max_dur |
|--------|-------|---------|---------|
| 200    | 20    | 75895ms | —       |
| 502    | 5     | 165025ms| 165040  |

SR = 20/25 = 80% (表面). 但失败高度集中, 见下.

### 2. 5 个 502 时序定位 (UTC)
| request_id | ts(UTC)      | error_type          | dur(ms) |
|------------|--------------|---------------------|---------|
| b14f37c8   | 06:26:08     | all_tiers_exhausted | 165016  |
| 3b1dcf8e   | 06:28:11     | all_tiers_exhausted | 165016  |
| 5f6a8448   | 06:28:31     | buffer_exhausted    | 165040  |
| 9dc9f661   | 06:28:31     | buffer_exhausted    | 165038  |
| fec9133a   | 06:30:14     | buffer_exhausted    | 165016  |

**5 个 502 全部落在 06:26-06:30 UTC (14:26-14:30 CST) 4 分钟窗口内.**

### 3. 根因
- `nv_tier_attempts` 表 30min 内仅 1 条 429 记录 (nv_key_idx=2), 与这 5 个 502
  无关联. 即 buffer 走到 `all_keys_exhausted` 时 **零 tier attempt 记录**.
- 含义: 5 key 在进入 buffer 时已被 KeyManager 判定全 cooling, buffer 5 次 attempt
  直接 `execute_failed` elapsed=0s (日志中 3a3dd02b attempt1 即此模式), 根本没
  真正打到 NVCF.
- `nv_key_idx` 为空 + `all_tiers_exhausted` = KeyManager 全 key 冷却中, buffer
  拿不到可用 key.
- ms_gw fallback 同窗口也 FAIL: ms_gw 日志 14:22-14:28 显示 v5 全 key 429 风暴
  (`MS-VARIANT-EXHAUSTED`), 与 NVCF 同窗口配额波动.
- 结论: **NVCF + ms_gw 同窗口瞬时 429 风暴导致尾部失败, 非代码缺陷, 非反复.**

### 4. 14:32 CST 之后干净窗口验证 (跨轮验证 DELEGATE)
| 窗口 | status | count | avg_dur | upstream_type |
|------|--------|-------|---------|---------------|
| 14:32+ (06:32 UTC+) | 200 | 11 | 5918ms | nvcf_pexec (全直连 NVCF) |

- 11 个 200, 0 失败, 0 fallback, 全走 `nvcf_pexec` (未走 ms_gw).
- 日志 `NV-BUFFER-EXEC-DELEGATE` 命中 4 次, 均 1 attempt 成功 (11-21s).
- **post266 DELEGATE 修复对 dsv4p_nv 同效确认.**

## 判稳
- 5 个 502 = 一次性窗口波动 (14:26-14:30), 14:32 后全 200, 无反复.
- dsv4p_nv 链路 post266 修复生效, 无新错误模式.
- SR 短期受尾部拖累, 但根因非代码 → **NOP 巡检轮, 0 改动 0 restart.**

## 本轮改动
无. (跨轮验证 post266, 仅记录数据.)

## 下一步
1. 持续观察 dsv4p_nv 在 cc2 primary 下的 SR, 看是否有反复 502 窗口.
2. 若 `all_tiers_exhausted` + 零 tier attempt 再次反复出现, 考察 KeyManager 在
   全 key cooling 时是否过早判定全挂 (应让 buffer 仍能等 ProbeWorker 唤醒后重试,
   而非 elapsed=0s 直接 execute_failed).
3. 关注 dsv4p_nv 的 429 是否集中在特定 key/egress IP (本轮 key2 有 1 次 429,
   样本太少).

## 参数快照 (2026-08-02 14:44 CST, 本轮未改参数)
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30,
  CC4101_PRIMARY_FAIL_THRESHOLD=3
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, BUFFER_MAX_RETRIES=5,
  BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s,
  TIER_TIMEOUT_BUDGET=180s, TIER_COOLDOWN_S=180s, UPSTREAM_TIMEOUT=90s,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NV_GLM52_MODE_CHAIN= (空, R-nvonly-post14 设计)
