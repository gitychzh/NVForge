# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1151 (恢复延续 NOP/不改码 — R1148/49 那场瞬时 (DEGRADED-fid + egress RemoteDisconnected)
> 风暴尾窗已几乎完全滚出 30min 窗口: 风暴段 17:58-18:02 UTC 结束后所有请求 74/74 = 100% SR, 最新 5min
> 21/21 = 100% SR; 30min surface 余下的 3× 502 (all_tiers_exhausted) 全落 17:58-18:02 = 风暴带尾窗
> (注入时计 4× 已有 1× 自然滚出); 错误签名与 R1148/49 完全一致, 无新类型; 无配置漂移 → 无码可改;
> R1148/49 风暴正式闭环)**
> 主链 fid: **281478d0-f307** 稳定 (全 5 key pexec), 旧 52e1ddb6 已完全消失
> 错误分类 (surface, 30min): all_tiers_exhausted × 3 (全 17:58-18:02 UTC 风暴带尾窗)
> 根因: **R1148 瞬时过境事件的残余尾窗, 已 100% 自愈**
> 最新 5min: **cc2-primary 200|21 = 0 非-200, 100% SR**
> 风暴后连续: **200|74 = 100% SR** (18:03:00 → 18:24:16)

## 本轮 (R1151) 改动 + 依据 + 验证

### 改动: 无 (恢复延续 NOP。30min surface 窗口余下 3× 502 全属 R1148/49 风暴带尾窗 (17:58-18:02 UTC),
### 风暴结束后 74/74 = 100% SR, 最新 5min 21/21。无新错误类型、无配置漂移 → NOP 不改码)

### 依据 (live 实查 2026-08-08 02:24 CST)

- **30min cc2-primary (实查)**: 3 个失败全落 **17:58:38 / 18:01:11 / 18:02:45 UTC** = R1149 记录风暴带
  (17:47-18:02) 的**尾窗**。末次失败 18:02:45, 之后 18:03:00 → 18:24:16 连续 74 个 200。(注入时计 4×,
  实查窗口已 1× 自然滚出 → 3×)
- **风暴后 18:03 起 (实查)**: **74/74 = 100% SR, 0 失败** — 较 R1150 的 55 又延伸, R1148/49 风暴完全
  过境, 恢复闭环延续。
- **最新 5min (实查)**: 21/21 = **100% SR**。
- **错误分类 (surface)**: `all_tiers_exhausted` × 3, avg_dur ~273s — 与 R1148/49 同签名, **无新类型**。
- **Tier 层 (实查)**: 主链 dsv4f0731_nv 全 5 key → **281478d0-f307**, 73× `pexec_success`; 错误仅
  `NVCFPexecRemoteDisconnected` × 1, **429=0, empty200=0** → 非 key-cooldown/非空响应根因。
- **nv_gw 日志 (实查)**: 全 `attempt=1/5 → success_tool_call → direct flush` (7-14s/req), 比 R1150 更干净
  (连那次 attempt-2 瞬时自愈都没有了)。无 WAIT/DEGRADED/exhaust。
- **fallback**: cc_requests f|178, ms_gw 未走。✅
- **容器**: nv_gw 40006 ok (28h), dsv4p_nv40066 40066 ok (3d), cc4101 4101 ok (22h), 全稳定未重启。

### 验证
风暴后连续 74× 200 = 100% SR; 最新 5min 21/21; buffer 全 attempt-1 direct flush; 容器全稳定。
下轮 4× (现 3×) 502 全部滚出 30min 窗口后整窗 SR 将稳回 99%+ → R1148/49 风暴正式闭环。

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
R1150 (恢复闭环 NOP — 30min surface 仍计 4× 502 全 17:54-18:02 = R1148 风暴尾窗, 风暴后 55/55=100%)。
R1151 确认该尾窗已基本滚出 (窗口内现 3×), 风暴后 streak 延伸至 74/74 → R1148/49 正式闭环。

## 下一步
维持静稳观察。下轮 4× (现 3×) 502 将全部滚出 30min 窗口, 整窗 SR 应稳回 99%+。
若再出现全 5 key 连败或新错误类型, 再深挖 egress 线路 (mihomo) / KeyManager cooldown。