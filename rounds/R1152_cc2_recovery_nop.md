# R1152 — cc2 恢复闭环 NOP (R1148/49 风暴尾窗再滚出 1×, 风暴后 92/92=100% SR)

- 轮次: R1152
- 时间: 2026-08-08 02:30 CST
- 类型: **恢复延续 NOP (不改码)**
- 容器: nv_gw 28h / cc4101 23h / dsv4p_nv40066 3d — 全部稳定未重启

## 结论一句话

R1148/49 那场瞬时风暴尾窗继续自然滚出: 65min 内 cc2 全部 6× 502 逐点落在风暴带 **17:47→18:02 UTC**
(17:47/17:49/17:54/17:58/18:01/18:02), 末次失败 18:02:45, 之后 **18:03 起连续 92/92 = 100% SR**
(较 R1151 的 74 又延伸)。30min 活跃窗口内现仅剩 **2× 502** (注入时 3× 又 1× 滚出), 最新 5min
18/18。无新错误类型、无配置漂移 → NOP 不改码。R1148/49 风暴**彻底过境**。

## 本轮数据 (live 实查 2026-08-08 02:29 CST)

### 30min 主链 (cc2-primary)
- **200 | 89** (注入 86 + 滚入)
- **502 | 2** — 实查时间戳: **18:01:11 / 18:02:45 UTC** = R1148/49 风暴带**尾窗**
  (注入时计 3×, 已 1× 自然滚出 30min 窗口; 上轮 R1151 的 3× 这轮剩 2×)
- **末次失败 18:02:45, 之后全是 200**

### 65min (实查, 风暴过境铁证)
- cc2 全部 6× 502: 17:47 / 17:49 / 17:54 / 17:58 / 18:01 / 18:02 — 与 R1149 记录风暴带 (17:47-18:02) 逐点吻合
- **成年 23 min 无失败** (18:03 → 18:29)

### 风暴后 18:03 → 现在 (决定性)
- cc2-primary: **92/92 = 100% SR, 连续 92 个 200, 0 失败** (18:03 → 18:29)

### 最新 5min
- 18/18 = **100% SR, 0 非-200**

### 错误分类 (30min surface)
- `all_tiers_exhausted` × 2 (实查; 注入 3× 又滚出 1×), 全在风暴带 18:01-18:02, **与 R1148/49 同签名, 无新类型**

### tier 层 (nv_tier_attempts, 实查)
- 91 × `pexec_success` (全 5 key), fid **281478d0-f307** 稳定, 全 5 key 分散无集中热点
- 错误仅 `NVCFPexecRemoteDisconnected` × 1 — 瞬时 egress, 已知自愈签名, **429=0, empty200=0** → 非 key-cooldown/非空响应

### buffer 日志 (实查)
- 全 `attempt=1/5 → success → direct flush` 干净稳态; 无 WAIT / DEGRADED / buffer_exhausted / 无 attempt-2+

### fallback
- f|192 (注入), ms_gw 未走。✅

## 本轮改动 + 依据 + 验证

### 改动: 无 (恢复延续 NOP。30min surface 余下 2× 502 全属 R1148/49 风暴带尾窗 18:01-18:02,
### 风暴后 92/92 = 100% SR, 最新 5min 18/18。无新错误类型、无配置漂移 → NOP 不改码)

### 验证
风暴后连续 92× 200 = 100% SR; 最新 5min 18/18; buffer 全 attempt-1 direct flush; tier 无 429/empty;
fid 稳定; fallback 0; 三容器全稳定。65min 全量 502 逐点匹配风暴带 → R1148/49 风暴**彻底过境**。

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
R1151 (恢复延续 NOP — 风暴带尾窗基本滚出, 窗口内 3×, 风暴后 74/74=100% SR)。
R1152 确认尾窗再滚出 1× (窗口内 剩 2×), 65min 全量 502 逐点匹配风暴带, 风暴后 streak 延伸至 92/92 → 彻底过境。

## 下一步
维持静稳观察。下轮 2× 502 (18:01/18:02) 将全部滚出 30min 窗口, 整窗 SR 应稳回 100%。若再出现
全 5 key 连败或新错误类型, 再深挖 egress 线路 (mihomo) / KeyManager cooldown。