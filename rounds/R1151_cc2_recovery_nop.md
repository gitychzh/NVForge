# R1151 — cc2 恢复延续 NOP (R1148/49 风暴尾窗已基本滚出, 风暴后 74/74=100% SR)

- 轮次: R1151
- 时间: 2026-08-08 02:25 CST
- 类型: **恢复延续 NOP (不改码)**
- 容器: nv_gw 28h / cc4101 22h / dsv4p_nv40066 3d — 全部稳定未重启

## 结论一句话

R1150 记录的那场 R1148/49 瞬时风暴 (风暴带 17:47-18:02 UTC) 尾窗已**几乎完全滚出 30min 活跃窗口**:
风暴段结束后的所有请求 **74/74 = 100% SR** (较 R1150 的 55 又延伸), 最新 5min 21/21, 30min 窗口内
仅剩 3× 502 全落在 17:58-18:02 风暴带 (原 4× 已有 1× 自然滚出)。无新错误类型、无配置漂移 → NOP 不改码。
R1148/R1149 风暴**正式闭环**。

## 本轮数据 (live 实查 2026-08-08 02:24 CST)

### 30min 主链 (cc2-primary)
- **200 | 68** (注入段; 实查窗口现 200|69+)
- **502 | 3** — 实查时间戳全在 **17:58:38 / 18:01:11 / 18:02:45 UTC** = R1148/49 风暴带**尾窗**
  (注入时计 4×, 已 1× 自然滚出 30min 窗口)
- **末次失败 18:02:45 之后全是 200**

### 风暴后 18:03 → 现在 (决定性)
- cc2-primary: **74/74 = 100% SR, 连续 74 个 200, 0 失败** (18:03 → 18:24:16)

### 最新 5min
- 21/21 = **100% SR, 0 非-200**

### 错误分类 (30min surface)
- `all_tiers_exhausted` × 3 (实查), avg_dur ~273s — 全落在风暴带 17:58-18:02, **与 R1148/49 同签名, 无新类型**

### tier 层 (nv_tier_attempts, 实查)
- 73 × `pexec_success` (全 5 key), fid 281478d0-f307 稳定
- 错误仅 `NVCFPexecRemoteDisconnected` × 1 (k0?/k1) — 瞬时 egress, 已知自愈签名, 无 429/empty200

### buffer 日志 (实查)
- 全 `attempt=1/5 → success_tool_call → direct flush` 干净稳态 (7-14s/req, content 275b-21385b)
- 无 WAIT / DEGRADED / buffer_exhausted / 无 attempt-2+ (较 R1150 连那个瞬时 execute_failed 都没有了)

### fallback
- f|178 (注入), ms_gw 未走。✅

## 本轮改动 + 依据 + 验证

### 改动: 无 (恢复延续 NOP。30min surface 余下 3× 502 全属 R1148/49 风暴带尾窗 17:58-18:02, 风暴后
### 74/74=100% SR, 最新 5min 21/21。无新错误类型、无配置漂移 → NOP 不改码)

### 验证
风暴后连续 74× 200 = 100% SR; 最新 5min 21/21; buffer 全 attempt-1 direct flush 比 R1150 更干净
(无 execute_failed); tier 无 429/empty; fid 稳定; fallback 0; 三容器全稳定。R1148/R1149 风暴**正式闭环**。

## 参数快照 (nv_gw + cc4101, 注入)

- **nv_gw**: UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5 (stairs 90×5=450s),
  NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_COOLDOWN_S=180, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
  (NV_GLM52_MODE_CHAIN=pexec_us_rr, 全 5 key bind fid index 0=281478d0-f307)。
- **cc4101**: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。

## 上轮
R1150 (恢复闭环 NOP — 风暴后 55/55=100% SR, 30min surface 仍计 4× 502 全 17:54-18:02 风暴尾窗)。
R1151 确认该尾窗已基本滚出 (窗口内现 3×), 风暴后 streak 延伸至 74/74 → 正式闭环。

## 下一步
维持静稳观察。下轮 4× 502 将全部滚出 30min 窗口, 整窗 SR 应稳回 99%+。若再出现全 5 key 连败或
新错误类型, 再深挖 egress 线路 (mihomo) / KeyManager cooldown。