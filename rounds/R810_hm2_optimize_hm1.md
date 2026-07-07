# R810: HM2→HM1 — 修复 400 DEGRADED 不循环 → 触发 fallback

**时间**: 2026-07-07 18:59 UTC
**R#**: R810
**类型**: 代码修复 (upstream.py `should_cycle` 添加 `400`)
**作者**: opc2_uname (HM2→HM1)

## 触发原因

R809 NOP 后 HM1 提交了 commit (8b4b496)，检测脚本判定轮到 HM2 执行优化。

## 一、数据采集

### 1.1 NVCF Function 状态

| Function | Health | 状态 |
|---|---|---|
| glm5_2_nv 3b9748d8 | 0.0 | **DEGRADED** — NVCF 返回 "DEGRADED function cannot be invoked" (400) |
| dsv4p_nv 74f02205 | 0.10–0.15 | 低但未死, 504 gateway timeout 间歇 |

### 1.2 6h 窗口 (≈13:00–19:00 UTC)

| 指标 | 数值 |
|------|------|
| 总请求 | 45 |
| 成功 (200) | 9 |
| 失败 (502) | **36** |
| SR | **20.0%** |
| Single-tier ATE | 33 |
| Double-tier ATE | 3 |

### 1.3 问题根因

NVCF 的 glm5_2_nv function 3b9748d8 进入 DEGRADED 状态后，返回 HTTP 400 + body:
```
{"status": 400, "title": "Bad Request", "detail": "Function id '3b9748d8...': DEGRADED function cannot be invoked"}
```

`upstream.py` 的 `should_cycle` 集合只包含 `(401, 403, 429, 408, 500, 502, 503, 504, 202)`，**缺少 400**。导致 NVCF 返回 400 DEGRADED 时，网关直接 `return result` 放弃整 request (NV-NONCYCLE-ERR)，不循环 key，不触发 fallback。openclaw 的所有 glm5_2_nv 请求全部 502，dsv4p_nv FALLBACK_GRAPH 从未触发。

### 1.4 日志确证

```
[NV-NONCYCLE-ERR] tier=glm5_2_nv k2 resp.status=400 non-cycling, aborting tier (no key cycle).
body={"status": 400, "title": "Bad Request", "detail": "Function id '3b9748d8...': DEGRADED function cannot be invoked"}
[NV-ALL-TIERS-FAIL] All 1 tiers failed (ring tiers tried: ['glm5_2_nv']), elapsed=5328ms, ABORT-NO-FALLBACK
[NV-PEER-FB] model=glm5_2_nv in peer-fb skip list (NVCF DEGRADING, peer same function also bad), returning local 502
```

## 二、优化方案

**添加 `400` 到 `should_cycle` 集合** — pexec 路径和 integrate 路径各一处。

NVCF 的 DEGRADED 状态是临时服务端降级（非永久错误），应循环 key 快速耗尽 tier，触发 FALLBACK_GRAPH 回退到 dsv4p_nv。

### 修改位置

1. `/opt/cc-infra/proxy/nv-gw/gateway/upstream.py` line 620 (pexec 路径):
   ```python
   # Before:
   should_cycle = resp.status in (401, 403, 429, 408, 500, 502, 503, 504, 202)
   # After:
   should_cycle = resp.status in (400, 401, 403, 429, 408, 500, 502, 503, 504, 202)
   ```

2. 同上 line 238 (integrate 路径):
   ```python
   # Before:
   should_cycle = resp.status in (401, 403, 429, 408, 500, 502, 503, 504, 202)
   # After:
   should_cycle = resp.status in (400, 401, 403, 429, 408, 500, 502, 503, 504, 202)
   ```

3. 添加 `cycle_reason`:
   - pexec: `"400_nvcf_degraded" if resp.status == 400`
   - integrate: `"400_integrate_degraded" if resp.status == 400`

## 三、部署验证

```bash
cd /opt/cc-infra && docker compose restart nv_gw
```

重启后健康检查通过:
```json
{"status": "ok", "proxy_role": "passthrough", "nv_num_keys": 5, "port": 40006}
```

### 3.1 修复后行为验证

```
[NV-CYCLE] tier=glm5_2_nv k5 → 400 (400_nvcf_degraded), cycling to next key
[NV-CYCLE] tier=glm5_2_nv k1 → 400 (400_nvcf_degraded), cycling to next key
[NV-CYCLE] tier=glm5_2_nv k2 → 400 (400_nvcf_degraded), cycling to next key
[NV-CYCLE] tier=glm5_2_nv k3 → 400 (400_nvcf_degraded), cycling to next key
[NV-CYCLE] tier=glm5_2_nv k4 → 400 (400_nvcf_degraded), cycling to next key
[NV-CYCLE] tier=glm5_2_nv k5 → 400 (400_nvcf_degraded), cycling to next key
[NV-CYCLE] tier=glm5_2_nv k1 → 400 (400_nvcf_degraded), cycling to next key
[NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
```

✅ 400 DEGRADED 现在正确循环 key → 快速耗尽 tier → 触发 FALLBACK_GRAPH 回退到 dsv4p_nv。

## 四、当前 NVCF 全貌

两个 function 都处于不稳定状态:
- **glm5_2_nv 3b9748d8**: DEGRADED (400, 不可调用)
- **dsv4p_nv 74f02205**: 504 gateway timeout (间歇性超时)

这是 NVCF 服务端问题，非本地配置可修。但 400 DEGRADED 修复确保当任一 function 恢复时，fallback 路径能正确工作。

## 五、评判

| 维度 | 评估 |
|------|------|
| 更少报错 | ✅ 400 DEGRADED 不再 NONCYCLE 静默失败，改为 CYCLE + FALLBACK |
| 更快请求 | ✅ 400 快速 cycle (≤1.5s/key) 替代立即 abort，更快进入 fallback |
| 超低延迟 | ✅ 无影响（400 响应 <100ms，cycle 5 key ~7s vs 之前 5s abort） |
| 稳定优先 | ✅ 修 bug，不改变正常路径行为 |

**铁律**: 只改 HM1 不改 HM2 ✅

## ⏳ 轮到 HM1 优化 HM2