# R816: HM2 ms_gw MS-STREAM-SETTO-ERR NameError 修复 (R813 回归)

> 承接 R815 (dsv4p empty-200 NOP). 远程 HM2 8轮定时优化 R3.
> 铁律: 改前有数据, 改后有验证, 改动 ≤5 处.
> 角色: HM2-only. ms_gw 源码是 HM1+HM2 共享 ([[shared-source-cross-host]]), 外科 patch 单行 import.

## 候选筛选 (改前数据 2026-07-08 01:30 UTC)

### 候选3: glm5_2_nv 恢复? → 否, 仍 DEGRADED
NVCF 直连 5 key 全 400 "Function 3b9748d8: DEGRADED function cannot be invoked".
R814 短路仍生效 (30min 22 个 502 全快速失败, NV-TIER-DEGRADED-SKIP 命中). 无需改.

### 候选1: kimi_nv 可用? → 是, 健康
经 nv_gw 探测 kimi_nv: HTTP 200 / 3.07s, function f966661c ACTIVE.
oc4105 primary 可用, 仅流量低. 无需改.

### 候选2: ms_gw 流式稳定性 → 发现 R813 回归 bug ★
ms_gw err log: `[MS-STREAM-SETTO-ERR] req=b02ab917 name 'UPSTREAM_TIMEOUT' is not defined`
ms_gw stream duration p95=161s / max=171s (流式大输出, 但 settimeout 兜底失效).

## 根因 (数据支撑)

R813 修 ms_gw [DONE] 关连接时, handlers.py:279 加了:
```python
resp.fp.raw._sock.settimeout(UPSTREAM_TIMEOUT)   # line 279
```
但 handlers.py:18-22 的 config import 列表未含 UPSTREAM_TIMEOUT:
```
from .config import (
    LISTEN_HOST, LISTEN_PORT, PROXY_ROLE,
    MS_KEYS, NUM_KEYS, NUM_VARIANTS, MODEL_REGISTRY, DEFAULT_MODEL,
    MS_BASEURL, MSU_GATEWAY_API_KEY, AUTH_ENABLED,
)   # ← 缺 UPSTREAM_TIMEOUT
```
config.py:22 本定义了 `UPSTREAM_TIMEOUT = float(os.environ.get("UPSTREAM_TIMEOUT","300"))`,
但未 import → 运行时 NameError → 被 except 吞 → 记 MS-STREAM-SETTO-ERR → settimeout 失效.

影响: relay loop resp.read1(8192) 无 socket 级超时兜底. 若 ModelScope [DONE] 后挂连接
(正是 R813 要修的场景), read1 可能阻塞到默认超时. R813 的 [DONE] 关连接修复依赖
settimeout 先兜底, 兜底失效 = R813 修复在异常路径上部分失效.

## 改动 (1 文件, 1 行, 编辑点 1 处)

handlers.py:18-22 import 列表加 UPSTREAM_TIMEOUT:
```
    MS_BASEURL, MSU_GATEWAY_API_KEY, AUTH_ENABLED,
+   UPSTREAM_TIMEOUT,
)
```
备份: handlers.py.bak.R816.

## 改后验证 (端到端 2026-07-08 01:35 UTC)

1. python import 检查: `from gateway.handlers import UPSTREAM_TIMEOUT` → 300.0 ✅
2. docker compose up -d --no-deps ms_gw → 重建成功 (新容器 ecc2ff...)
3. 流式请求 ms_gw glm5_2_ms stream: HTTP 200 / 18s / 正常 [DONE] ✅
4. 部署后 MS-STREAM-SETTO-ERR 计数 = 0 (之前每次流式都报) ✅

## 回滚
`cp handlers.py.bak.R816 handlers.py && docker compose up -d --no-deps ms_gw`.

## 下轮候选 (R817)
- 观察 R816 修复后 ms_gw stream duration p95 是否下降 (settimeout 兜底恢复后)
- ms_gw cycle/stream_no_data 是否仍出现 ([DONE] 关连接 R813 修的真实效果回归)
- dsv4p_nv ttfb 是否仍偶发 65s empty-200 (持续观测)
