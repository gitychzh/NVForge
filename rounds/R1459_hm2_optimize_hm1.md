# HM2 Optimize HM1 — Round R1459 (NVU_MS_GW_FALLBACK_TIMEOUT 280→120 + Connection:close code fix)

## 1. 触发分析
- cron 脚本检测到 HM1 新 commit → 触发 HM2 优化 HM1
- 最新 commit: `a9d95ef` (R1458, author=opc2_uname, NOP)
- 判定: 继续 NOP 链触发的优化轮次

## 2. 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up, healthy
- ms_gw: running

### nv_gw 6h 统计 (2026-07-15 20:55 UTC ≈)
| 指标 | 值 |
|------|-----|
| 总请求 | 37 |
| 成功 (200) | 14 |
| 失败 (502) | 23 |
| 成功率 | 37.8% |

### 6h 错误分类
| 错误类型 | 数量 | avg_dur | 说明 |
|---------|------|---------|------|
| all_tiers_exhausted | 12 | 89191ms | dsv4p_nv NVCF 504 |
| zombie_empty_completion | 11 | 10948ms | glm5_2_nv content-filter |

### dsv4p_nv ATE 详细分析 (日志)
```
NV-CYCLE k1 → 504 (~63s) → cycling k2-k5 → all fail → 504
NV-TIER-FAIL: all 5 keys, other=1 (504), elapsed=63s
NV-ALL-TIERS-FAIL: ABORT-NO-FALLBACK
NV-THINKING-TIMEOUT: extended timeout 66s
NV-MS-FB: relay_started=True → TimeoutError → ~284s wasted
NV-EMPTY-200: k1 200 Content-Length:0 → GLOBAL-COOLDOWN 15s
```

### ms_gw 6h: 27/23 85.2% SR — healthy
- ms_gw responds in 2-31s (avg 8465ms for success, 15131ms for errors)
- But nv_gw relay always hits TimeoutError at 280s → relay_started=True blocks peer-fb

### Why ms_gw relay always fails
- `_ms_gw_fallback()` in handlers.py **does NOT send `Connection: close`** to ms_gw
- Without `Connection: close`, ms_gw keeps the TCP connection alive after sending the stream
- `resp.read(8192)` blocks forever waiting for more data on a persistent connection
- Timeout hits at 280s (`NVU_MS_GW_FALLBACK_TIMEOUT=280`)
- Since `relay_started=True` (200 headers already sent to client), the code returns early
- Peer-fallback (`_peer_fallback`) is skipped because ms_gw was tried first and failed

### tier_attempts: 0 (no key cycling)
### key_cycle_429s: 0

## 3. 当前配置
```
UPSTREAM_TIMEOUT=66
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=
NVU_MS_GW_FALLBACK_TIMEOUT=280  ← 改前
```
Compose md5 (改前): `51079b89`

## 4. 优化: 2 项变更

### 4.1 Code fix: handlers.py — add `Connection: close` to ms_gw fallback request
**文件**: `/opt/cc-infra/proxy/nv-gw/gateway/handlers.py` line ~1080
**变更**: 在 `_ms_gw_fallback()` 中，ms_gw 请求头增加 `fwd_headers["Connection"] = "close"`
**原因**: 无 `Connection: close` 时，ms_gw 保持 TCP 持久连接，`resp.read(8192)` 阻塞直到 280s 超时。ms_gw 实际响应只需 2-31s。添加后 ms_gw 会在流结束后主动关闭连接，nv_gw 的 `resp.read()` 收到 EOF 正常结束。
**风险**: 零。peer-fb 的同路径已有此 header (line 954)，已验证安全。

### 4.2 Config: NVU_MS_GW_FALLBACK_TIMEOUT 280→120
**文件**: `/opt/cc-infra/docker-compose.yml`
**变更**: `NVU_MS_GW_FALLBACK_TIMEOUT: 280 → 120`
**原因**: ms_gw 2-31s 响应，120s 给 4-60x 冗余。Code fix 后 relay 应正常完成，但保留 120s 作为安全网。66s tier budget + 120s = 186s < 360s PROXY_TIMEOUT。
**风险**: 极低。若 code fix 失效，120s 仍够 ms_gw 响应（max 31s per DB），失败也更快释放资源。

## 5. 预期效果
- ms_gw relay 正常完成 → ATE 后 ms_gw 成功兜底，SR 提升
- 失败 ATE 耗时: 343s (63s tier + 280s timeout) → ~63s (tier + 2-31s ms_gw relay)
- 若 ms_gw 也失败，不再浪费 280s → 120s 后快速返回 502
- peer-fb 仅在 ms_gw 完全不可达时尝试（code fix 后 relay 正常完成则不会触发 peer-fb）

## 6. 验证
- Container rebuilt + restarted ✓
- Health check: `{"status": "ok"}` ✓
- `NVU_MS_GW_FALLBACK_TIMEOUT=120` confirmed in container ✓
- `Connection: close` at line 1080 confirmed in container ✓
- Compose md5 (改后): `45c1f284`

## 7. 铁律
- 只改HM1不改HM2 ✓
- 改前必有数据 ✓
- 改后必有验证 ✓
- 所有修改写入仓库 (本次 commit) ✓
## ⏳ 轮到HM1优化HM2
