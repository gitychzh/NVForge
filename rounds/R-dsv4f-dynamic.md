# R-dsv4f-dynamic: dsv4f_nv per-key pexec↔integrate 动态切换 + FID 自动发现

**Date:** 2026-08-04
**Container:** dsvf0731_nv40666 (port 40666, HM2)
**Commit:** (this round)

## 背景

R-dsv4f-newfid 发现新 FID 52e1ddb6 后, pexec 恢复可用 (SR 27% > integrate 10%)。但当前配置 NV_INTEGRATE_MODELS 为空, dsv4f_nv 只走 pexec, 从不尝试 integrate。用户要求: pexec 失败 → 下一个 key 切 integrate; integrate 失败 → 切 pexec。并新增 FID 自动发现功能。

## 变更 1: _try_dsv4f_dynamic_keys() — per-key pexec↔integrate 交替

### 设计
- 新增 `_try_dsv4f_dynamic_keys()` 函数 (upstream.py, ~280 行)
- 5 key 轮转中, **交替** 选择路径:
  - attempt 0: key_start → pexec
  - attempt 1: key_next → integrate
  - attempt 2: key_next → pexec
  - attempt 3: key_next → integrate
  - ...
- 每次失败后自动换 key + 换路径
- 529 cycling 仍工作 (should_cycle 包含 529)
- 5 key 全失败 → all_keys_exhausted → fallback 逻辑不变

### execute_request 分支
- 在 dsv4p channel 分支之前, 新增 dsv4f_nv 专属分支
- 命中 `_dsv4f_dynamic_done = True`, 跳过后续 R838b/R572/pexec 分支
- 成功 → return; 失败 → tier_result = dynamic_result, 走 all-tiers-exhausted → ms_fb

### 日志验证 (E2E 10 次, 80% SR)
交替模式清晰可见:
```
attempt 1: k1 pexec → 529
attempt 2: k2 integrate → 529
attempt 3: k3 pexec → SUCCESS (529 cycling 后命中)
```
失败案例: 7 次 attempt (k1pexec→k2integrate→k3pexec→k4integrate→k5pexec→k1integrate→k2pexec), 全 529 → all_keys_exhausted

## 变更 2: fid_discovery.py — FID 自动发现后台线程

### 设计
- 新文件 `gateway/fid_discovery.py` (~220 行)
- 后台线程每 `NVU_FID_DISCOVERY_INTERVAL_S` (默认 1800s=30min) 执行一次
- 流程:
  1. 调用 `GET /v2/nvcf/functions` 获取全量 function list (已验证可用, 178 functions)
  2. 过滤: name 包含 `deepseek-v4-flash` 且 status=ACTIVE
  3. 检查当前 FID 是否仍 ACTIVE
  4. 若当前 FID 仍 ACTIVE 且健康 → 保持, 探活新候选但不切换
  5. 若当前 FID 不再 ACTIVE → 对所有候选做 pexec 探活, 首个成功者替换
- 替换: 只改内存中 `NVCF_PEXEC_MODELS["dsv4f_nv"]["function_ids"][0]`, 不改文件
- 线程安全: threading.Lock 保护替换操作
- 不影响请求路径: 后台线程, 失败静默

### 启动
- `gateway/app.py` 新增 5 行: 启动 fid_discovery 线程
- 环境变量 (40666 容器):
  - `NVU_FID_DISCOVERY_ENABLED=1`
  - `NVU_FID_DISCOVERY_INTERVAL_S=1800`
  - `NVU_FID_DISCOVERY_MODEL=dsv4f_nv`
  - `NVU_FID_DISCOVERY_NAME_MATCH=deepseek-v4-flash`

### 启动日志验证
```
[NV-FID-DISCOVERY-START] FID discovery thread started: interval=1800s model=dsv4f_nv match=deepseek-v4-flash
[NV-FID-DISCOVERY] Starting discovery cycle: model=dsv4f_nv current_fid=52e1ddb6-c74...
[NV-FID-DISCOVERY] Functions list returned 178 functions
[NV-FID-DISCOVERY-CANDIDATE] Found ACTIVE candidate: 52e1ddb6-c74... name=ai-deepseek-v4-flash
[NV-FID-DISCOVERY-CANDIDATE] Found ACTIVE candidate: cbde15a8-be7... name=kvlab-deepseek-v4-flash
[NV-FID-DISCOVERY] Current FID 52e1ddb6-c74... still ACTIVE
[NV-FID-DISCOVERY-PROBE-FAIL] FID cbde15a8-be7... probe 404
[NV-FID-DISCOVERY] No new candidates passed probe. Keeping current.
```

## 文件改动

| 文件 | 改动 | 说明 |
|------|------|------|
| `gateway/upstream.py` | +1 函数 +1 分支 +3 guard | `_try_dsv4f_dynamic_keys()` + execute_request 分支 + R838b/R572/pexec guard |
| `gateway/fid_discovery.py` | 新文件 | FID 自动发现后台线程 |
| `gateway/app.py` | +5 行 | 启动 fid_discovery 线程 |
| `docker-compose.yml` (40666) | +4 env | FID discovery 配置 |

## E2E 验证

### 40666 dsv4f_nv 动态切换 (10 次)
```
#1 OK 200 3.6s Hello.
#2 OK 200 6.1s Hello
#3 OK 200 2.8s Hello
#4 OK 200 3.8s Hello!
#5 OK 200 5.7s Hello
#6 OK 200 5.0s Hello
#7 ERR 502 19.7s (全 529, all_keys_exhausted)
#8 OK 200 9.9s Hello
#9 OK 200 2.9s Hello.
#10 ERR 502 17.4s (全 529, all_keys_exhausted)
```
**SR: 8/10 = 80%** (vs 之前 70%, 529 cycling + 动态切换提升)

## 参数表

| 参数 | 值 | 说明 |
|------|-----|------|
| 交替模式 | attempt_idx % 2 | 0=pexec, 1=integrate |
| _max_attempts | NVU_NUM_KEYS + 2 = 7 | 5 key + 2 wrap |
| TIER_TIMEOUT_BUDGET_S | 180 (env) | 同主 nv_gw |
| FID discovery interval | 1800s (30min) | 首次启动立即执行 |
| FID probe | key1 + direct | 不走代理, 减少干扰 |
