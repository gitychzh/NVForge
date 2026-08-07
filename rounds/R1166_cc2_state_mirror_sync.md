# R1166 cc2 STATE mirror sync — 恢复闭环NOP, 实查30min cc4101-primary 200|102=100%SR 0非-200, 整窗全绿跨九轮

- 轮次: R1166 (cc2)
- 日期: 2026-08-08 03:41 CST
- 容器: nv_gw Up 24h | cc4101 Up 24h (实查 /health 全 ok)

## 结论: NOP (不改码)。链路整窗全绿跨九轮。

## 30min 链路数据 (注入分析 03:41 + 实查)

### 总线 (caller × model × status)
```
cc4101-primary|dsv4f0731_nv|200|103
hermes       |dsv4f0731_nv|200|59
hermes       |dsv4f0731_nv|502|1
```
总线 dsv4f0731_nv SR=99.4% (162/163)

### cc4101-primary (cc2 的请求)
- 注入: `200|103` = 100% SR, 0 非-200
- 实查导通: `200|102` (窗口 re-sample 微差), 0 非-200
- **cc2 整窗 100% 全 200, 0 错**

### 错误分类 (30min)
- `stream_first_byte_timeout × 1` (平均 83.2s)
- 唯一 502 JOIN 归属 `caller=hermes` req 9bb268ca, **非 cc2**
- 同 R1162-R1165 签名: 瞬时首次包超时 (first-byte), 非配置漂移、非新根因

### tier (per-key × error_type, 30min)
```
0|pexec_success|23   1|pexec_success|19   2|pexec_success|19   3|pexec_success|20   4|pexec_success|21
```
全 pexec_success, 无 429/empty/新类型, fid 全 281478d0-f307

### fallback
- 0 触发 (总线 103/163 全 200 直通, 无回退)

### buffer/wait/keymanager 日志
- 无 buffer/wait/keymanager 日志 = 全 attempt-1 direct flush, 无退避无 WAIT 无 buffer_exhausted

## 判断
- 注入链路 SR=99.4% (总线), cc2-primary 整窗 100% (注入 103 + 实查 102 全 200, 0 非-200)
- SR ≥ 99% 且无新错误 → **NOP 巡检轮, 不改码** (符合第三步判稳条件)
- 唯一错误 (stream_first_byte_timeout) 归属 hermes, 非 cc2 请求, 非新类型

## 改动
无。

## 验证
- cc2 (cc4101-primary) 实查 102/102 = 100% SR, 0 非-200
- nv_gw + cc4101 /health 全 ok, Up 24h
- tier 全 pexec_success 无新类型; fallback 0%; buffer 无退避无 WAIT

## 参数快照 (注入无变更, 与 R1165 一致)
- nv_gw: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5
  (stairs 90×5=450s), NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, KEY_COOLDOWN_S=30, INTEGRATE_KEY_COOLDOWN_S=90,
  TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
  (全 key bind fid index 0=281478d0-f307, dsv4f0731_nv 单模式)。
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1165 (NOP — 99/99 全 200) → R1166 确认: 整窗全绿跨九轮。唯一 hermes 瞬时 502 非 cc2。

## 下一步
维持静稳观察。核心监控仍是独立瞬时 burst 复发间隔 (Burst2 后已跨 150+ min 无 cc2 异常)。
若下个窗口再现 ≥2× buffer_exhausted 且 request_id 全新 (JOIN 归属 cc2), 为独立新事件,
按记忆 `ssleof-error-transient-egress-blip` 深挖 mihomo dsv4f0731_nv egress 线路 (7900-7904)。
当前仍判定瞬时 egress 抖动非配置漂移, NOP。