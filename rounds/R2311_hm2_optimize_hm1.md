# R2311 (HM2→HM1): NVU_PEER_FB_SKIP_MODELS +dsv4p_nv

## 日期
2026-07-24

## 链路
HM2 (100.109.57.26) → SSH → HM1 (100.109.153.83:222) → nv_gw container (port 40006)

## 数据采集

### 容器状态
- Container: `nv_gw` (port 40006)
- Pre-change StartedAt: 2026-07-23T22:23:44Z (R2310 deploy)
- Post-change StartedAt: 2026-07-23T23:03:30Z
- Health: healthy, RC=0, 5 keys, passthrough
- Env: NVU_PEER_FALLBACK_TIMEOUT=60 (R2308), NVU_PEER_FB_SKIP_MODELS=glm5_2_nv (R2310)
- Docker logs: no crash/restart errors

### 24h 成功率 (nv_requests)

| 模型 | 200 | 502 | 429 | 成功率 |
|------|-----|-----|-----|--------|
| dsv4p_nv | 30 | 31 | 0 | 49.2% |
| glm5_2_nv | 59 | 32 | 20 | 53.2% |
| kimi_nv | 20 | 35 | 0 | 36.4% |

### 24h 错误分类 (non-200)

| 模型 | error_type | 次数 | avg_ms | min_ms | max_ms |
|------|------------|------|--------|--------|--------|
| dsv4p_nv | all_tiers_exhausted | 26 | 17,998 | 6 | 160,041 |
| dsv4p_nv | zombie_empty_completion | 5 | 29,303 | 10,471 | 95,117 |
| glm5_2_nv | all_tiers_exhausted | 44 | 19,497 | 6 | 90,939 |
| glm5_2_nv | zombie_empty_completion | 8 | 17,555 | 6,283 | 28,985 |
| kimi_nv | all_tiers_exhausted | 26 | 193,765 | 123,628 | 370,299 |
| kimi_nv | zombie_empty_completion | 8 | 74,004 | 4,389 | 148,541 |

### dsv4p_nv 成功率延迟 (24h, status=200)

| p50 | p90 | p95 | p99 |
|-----|-----|-----|-----|
| 23,208ms | 61,631ms | 78,850ms | 90,721ms |

### dsv4p_nv Fast-fail (all_tiers_exhausted, <10s)

17 次 ATE @ avg 8ms — 冷却路径命中 (TIER_COOLDOWN=15s blocking)

### dsv4p_nv Peer-Fallback 分析 (2026-07-24 proxy log, 全量)

**成功 (1 event, 可疑):**
- 06:39:18 OK 200 bytes=2721 ttfb=13ms — 疑似错误响应 (仅 2721 字节)

**失败 (4 events, 00:00-02:09 UTC):**
- 02:02:17 FAIL 122066ms TimeoutError
- 02:05:12 FAIL 51502ms RemoteDisconnected
- 02:06:32 FAIL 111270ms peer returned 502
- 02:08:23 FAIL 122114ms TimeoutError

**Docker logs (post-R2310 restart, 06:00+):**
- 06:38:05 peer-fb attempt → 06:38:36 peer returned 502 after 31207ms
- 06:38:39 peer-fb attempt → 06:39:18 peer fallback OK 13ms/2721 bytes

**关键发现:** dsv4p_nv peer-fb 成功率 20% (1/5)，且唯一的"成功"疑似错误响应 (2721 字节/13ms)。80% 失败率，浪费 31-122s/次。失败模式包括 TimeoutError、RemoteDisconnected、peer 502。

### 新增: dsv4p_nv 404 NONCYCLE 错误模式

```log
[06:37:49.8] [NV-KEY] tier=dsv4p_nv k5 → NVCF pexec
[06:38:05.4] [NV-NONCYCLE-ERR] tier=dsv4p_nv k5 resp.status=404 non-cycling, aborting tier
  body={"type":"urn:inference-service:problem-details:not-found","title":"Not Found",
  "status":404,"detail":"Inference error"}
[06:38:05.4] [NV-ALL-TIERS-FAIL] elapsed=15556ms, ABORT-NO-FALLBACK
→ triggers peer-fb → 31s later: peer returned 502
```

404 NONCYCLE 是层级故障: NVCF pexec 函数返回 "Inference error" → 所有 key 均会返回 404 → peer-fb 注定失败（HM2 使用相同 function_id）。

## 优化决策

### 改动: `NVU_PEER_FB_SKIP_MODELS` 从 `glm5_2_nv` 改为 `glm5_2_nv,dsv4p_nv`

**理由:**
1. dsv4p_nv peer-fb 80% 失败率 (4/5)，浪费 31-122s/次 = ~326s 今日浪费
2. 404 NONCYCLE 是层级故障 — HM2 使用相同 NVCF function_id → peer 也被 404 → peer-fb 注定失败
3. 唯一的"成功"案例 (13ms/2721 字节) 高度可疑，疑似错误响应
4. Skip 后: 502 立即返回 6-8ms (cooling path) → agent ms_gw fallback (正确路径)
5. R2310 已验证 glm5_2_nv peer-fb skip 效果良好 (4 次 skip 在 docker logs 中正常运行)
6. kimi_nv 不在 skip 列表中，peer-fb 仍可用

**不影响:**
- kimi_nv: 不在 skip list，peer-fb 仍可用
- glm5_2_nv: 已在 skip list (R2310) ✓
- 429 路径: 本就跳过 peer-fb (is_429=True)
- ms_gw fallback: 不受影响

**预期效果:**
- dsv4p_nv 502 ATE: 用户等待从 ~48s (18s local + 31s peer-fb) 降至 ~18s → ms_gw fallback
- 每 24h 节省: ~26 次 ATE × 31s = 806s (13.4 分钟) 用户等待时间
- Fast-fail 502 (cooldown path): 从 8ms + 31s 降至 8ms → 立即 ms_gw
- 404 NONCYCLE: 从 15.6s + 31s 降至 15.6s → 立即 ms_gw

## 执行

```bash
# HM1: /opt/cc-infra/docker-compose.yml L483
# 旧: NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
# 新: NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
cd /opt/cc-infra && docker compose up -d nv_gw
# → Container recreated, env applied, healthy
```

验证:
```
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
Container: Up (healthy), StartedAt=2026-07-23T23:03:30Z
Health: 200 ok, 5 keys, passthrough
```

## 与之前轮次的关系

- R2308: NVU_PEER_FALLBACK_TIMEOUT 122→60 ✓
- R2309: NVU_TIER_BUDGET_KIMI_NV 200→130 ✓
- R2310: NVU_PEER_FB_SKIP_MODELS=glm5_2_nv ✓
- **R2311 (本轮): NVU_PEER_FB_SKIP_MODELS +dsv4p_nv** ← 相同域扩展，不与之前冲突

## ⏳ 轮到HM1优化HM2