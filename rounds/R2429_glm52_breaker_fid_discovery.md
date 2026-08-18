# R2429 — Breaker 敏感度调整 + all_keys_exhausted 触发即时 fid 发现

**时间**: 2026-08-18
**容器**: nv_gw (40006)

## 背景

R2428 清理死 fid 后, NV 流量仅 12% — breaker 持续 OPEN (5key 全 429), MS 承担 88%。
根因: 唯一 ACTIVE fid 3b9748d8 被 NVCF 密集 429 rate-limit, 5 key 全挂 → breaker OPEN → 走 MS。
fid_discovery 仅 30min 定时运行, 不响应 all_keys_exhausted 事件。

## 改动

### 1. Breaker 敏感度 (docker-compose.yml)
- `NVU_MS_FALLBACK_FAIL_THRESHOLD`: 5→3 (更快切 MS 避免超时)
- `NVU_MS_FALLBACK_SKIP_S`: 30→15 (更快 HALF_OPEN probe)

### 2. fid_discovery.py — on-demand 触发 + add 模式
- 新增 `trigger_immediate()`: 从 upstream.py all_keys_exhausted 调用, 后台线程执行
- 新增 `_discover_cycle_on_demand()`: 查找新 ACTIVE fid, 用 `_set_current_fid(replace=False)` 添加到 function_ids 前端
- `_set_current_fid` 新增 `replace` 参数: False=添加到列表前端(保留旧 fid), True=替换 pos0(默认, 兼容)
- 30s debounce (`_trigger_min_interval`): 防止 all_keys_exhausted 连续触发时重复发现

### 3. upstream.py — all_keys_exhausted 触发 fid 发现
- glm5_2 chain 的 `all_keys_exhausted` 分支: 调用 `fid_discovery.trigger_immediate()`
- 当前请求仍走 MS fallback (不阻塞), 下一请求受益于新发现的 fid

## 语义

```
请求 → 5 key 全 429 → all_keys_exhausted
                      ├─→ trigger_immediate() (后台线程, 非阻塞)
                      │    └─→ 查找新 ACTIVE fid → 添加到 function_ids 前端
                      └─→ MS fallback (当前请求, 快速返回)
下一请求 → 新 fid 在列表前端 → 尝试新 fid (可能有不同 rate-limit pool)
```

## Key 状态更正

- 之前误判 KEY1 (NVU_KEY2, nvapi-Oi2S0DK...) 为死 key (403)
- 实测: 403 是 transient, 后续恢复, 所有 5 key 均可用
- 直接 (中国 IP 112.20.197.150) pexec 200 OK
- US 代理 IP 也 429 (NVCF 对代理 IP rate-limit 更激进)
