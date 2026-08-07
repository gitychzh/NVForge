# R1167 cc2 STATE mirror sync — 恢复闭环 NOP

> 轮类: **NOP 巡检轮 (恢复闭环)** — 实查 30min cc4101-primary 200|101 = 100% SR,
> 0 非-200; 整窗全绿跨十轮 (R1158→R1167); 总线 dsv4f0731_nv SR=99.4% (165/166)
> 唯一 502 `stream_first_byte_timeout` JOIN 归属 hermes 非 cc2、非新根因; tier 全
> pexec_success (101) 无 429/empty; fallback 0%; buffer 全 attempt-1 direct flush
> 无退避无 WAIT; fid 281478d0-f307 稳定; **NOP 不改码**

## 状态: ✅ 链上静稳, 无改码条件

## 依据 (注入链路分析 2026-08-08 03:45 CST + 实查 30min + 容器健康)

### 注入链路分析 (30min)
- **链路总览 (caller × model × status)**: `cc4101-primary|dsv4f0731_nv|200|101`,
  `hermes|dsv4f0731_nv|200|64`, `hermes|dsv4f0731_nv|502|1` → SR=99.4% (165/166)。
- **cc4101-primary 专属 (cc2 的请求)**: `200|101|12699` = 100% SR。
- **错误分类 (30min)**: 唯一 `stream_first_byte_timeout × 1` avg_dur 83.2s,
  归属 hermes 非 cc2 (同 R1162-R1166 签名: 瞬时首次包超时 first-byte, 非配置漂移)。
- **tier per-key (30min)**: 全 `pexec_success` (23/18/18/21/21), 无 429/empty/新类型。
- **fallback 发生率**: `|166` → 总线 0 触发 = 0%。
- **buffer 日志**: 无 buffer/wait/keymanager 异常日志 (仅正常 attempt-1 flush 记录)。

### 实查确认
- **cc4101-primary 30min**: `200|101` 直查 = 100% SR, 0 非-200, 0 错误行。
- **fallback 直查**: 102 total, 0 fallback_triggered = 0%。
- **buffer 日志 (30min)**: 全部 attempt=1 success flush (e.g. req fa921c27 attempt 1/5
  verdict=success_tool_call elapsed 8s), 无退避、无 WAIT、无 buffer_exhausted。
- **容器健康**: nv_gw /health {"status":"ok", nv_num_keys:5, pexec models 含 dsv4f0731_nv};
  cc4101 /health {"status":"ok", primary:dsv4f0731_nv}。未重启。

## 改动: 无 (NOP)

## 验证
实查 cc4101-primary 101/101 = 100% SR, 0 非-200; update fallback 直查 0%;
buffer 全 attempt-1 direct flush 无退避无 WAIT; tier 全 pexec_success 无新类型;
容器全健康。根因: 链上静稳, 唯一 502 归属 hermes 非 cc2。无改码条件。

## 参数快照 (注入本轮无变更, 与 R1166 一致)

- **nv_gw**: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5
  (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90,
  TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  (全 key bind fid index 0=281478d0-f307, dsv4f0731_nv 单模式)。
- **cc4101**: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1166 (NOP — 实查 102/102 全 200) → R1167 确认: 实查 101/101 全 200, 唯一 hermes 瞬时
502 (首次包超时) 非 cc2。链路跨十轮全绿无新事件。

## 下一步
维持静稳观察。**核心监控: 是否重现独立瞬时 burst 及复发间隔**。
Burst2 后已跨 ~180+ min 无任何 cc2 异常, 穿越十轮 (R1158→R1167) 整窗全绿。
若下个窗口再现 ≥2× buffer_exhausted 且 request_id 全新 (JOIN 归属 cc2), 则为**独立新事件**,
按记忆 `ssleof-error-transient-egress-blip` 深挖 mihomo dsv4f0731_nv egress 线路 (7900-7904),
评估超 5 key 超大请求 buffer 首跳韧性。当前仍判定瞬时 egress 抖动非配置漂移, NOP。