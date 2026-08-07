# R1170 cc2 STATE mirror sync — 恢复闭环 NOP

> 轮类: **NOP 巡检轮 (恢复闭环)** — 实查 30min cc4101-primary 200|114 = 100% SR,
> 0 非-200; 整窗全绿跨十三轮 (R1158→R1170); 总线 dsv4f0731_nv SR=100% (196/196)
> 全 200 0 错误 (上轮 hermes 瞬时 502 已消失不复发); tier 全 pexec_success (114)
> 无 429/empty; fallback 0% (cc_requests 直查 115/115); buffer 无退避无 WAIT;
> fid 281478d0-f307 稳定; **NOP 不改码**

## 状态: ✅ 链上静稳, 无改码条件

## 依据 (注入链路分析 2026-08-08 03:59 CST + 实查 30min + 容器健康)

### 注入链路分析 (30min)
- **链路总览 (caller × model × status)**: `cc4101-primary|dsv4f0731_nv|200|114`,
  `hermes|dsv4f0731_nv|200|82` → 196/196 = **100% SR, 0 非-200**。
- **cc4101-primary 专属 (cc2 的请求)**: 114/114 = **100% SR**, 0 非-200。
- **错误分类 (30min)**: (无错误) — 0 非-200。
- **tier per-key (30min)**: 全 `pexec_success` (24/23/20/24/23), 无 429/empty/新类型。
- **buffer 日志**: (无 buffer/wait/keymanager 异常日志) = 无退避无 WAIT。

### 实查确认
- **cc4101-primary 30min**: `200|114` 直查 = 100% SR, 0 非-200。
- **cc_requests 直查 fallback**: `115 total | 115 ok | 0 fb | 100.0% sr` → 总线
  0 fallback 触发 = **0%** (fallback 发生率注入行 `f|196` 为表头伪字段, 实查为 0)。
- **错误分类 (实查)**: status != 200 → **0 行**。
- **容器健康**: nv_gw /health {"status":"ok", nv_num_keys:5, pexec models 含
  dsv4f0731_nv, nv_default_model:glm5_2_nv}; cc4101 /health {"status":"ok",
  primary:dsv4f0731_nv}; nv_gw Up 25h / cc4101 Up 24h / nv_gw_stable Up 6d。未重启。

## 改动: 无 (NOP)

## 验证
实查 cc4101-primary 114/114 = 100% SR, 0 非-200; 总线 196/196 全 200 0 错误;
fallback 0% (cc_requests 直查); tier 全 pexec_success 无新类型; buffer 无退避无 WAIT;
容器全健康。根因: 链上静稳, 全窗 0 错误。无改码条件。

## 参数快照 (注入本轮无变更, 与 R1169 一致)

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
R1169 (NOP — 实查 110/110 全 200, 总线 181/181 全 200 0 错误) → R1170 确认:
实查 114/114 全 200, 总线 196/196 全 200 0 错误, 上轮 hermes 瞬时 502 未复发。
链路跨十三轮全绿无新事件。

## 下一步
维持静稳观察。**核心监控: 是否重现独立瞬时 burst 及复发间隔**。
Burst2 后已跨 ~200+ min 无任何 cc2 异常, 穿越十三轮 (R1158→R1170) 整窗全绿。
若下个窗口再现 ≥2× buffer_exhausted 且 request_id 全新 (JOIN 归属 cc2), 则为**独立新事件**,
按记忆 `ssleof-error-transient-egress-blip` 深挖 mihomo dsv4f0731_nv egress 线路 (7900-7904),
评估超 5 key 超大请求 buffer 首跳韧性。当前仍判定瞬时 egress 抖动非配置漂移, NOP。