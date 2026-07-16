# R1602: HM2 cc4101 deadline 倒挂彻底修复 (方案A, 治根)

> 承接 R1412(不完整修复) + R1420(min封顶bug). 真根因: cc4101 header timeout 与
> nv_gw mode chain budget 倒挂. 破"只改HM1"铁律, 已获用户明确批准(AskUserQuestion方案A).

## 一、真根因 (数据实证)

### 证据 (2026-07-16 01:35-01:49, HM2)

cc4101 日志: 连续 9 次 `PRIMARY-FAIL timeout after 60054ms: header/ttfb timeout after 60s`,
累计触顶 `PRIMARY-BREAKER-OPEN` → fast-fail 503 "circuit open" 死循环, 持续到 01:49+.

nv_gw 日志(同窗口): `NV-TIER-FAIL all 5 keys failed`, `NV-TIER-BUDGET budget 120s exceeded`,
`NV-GLM52-CHAIN-FAIL`, 合法耗时 215-247s 跑完 5key×mode 才返回 502.

DB (nv_requests glm5_2_nv 6h): 5条 (4×zombie_empty_completion 502 + 1×200), ttfb 3-5s
(nv_gw 自己的 NVCF 探测不慢; 慢的是 mode chain 整体 5key 轮换).

### 物理本质

NVCF glm5_2_nv 劣化时, nv_gw 的 mode chain (`pexec_us_rr`) 在 send 响应头之前完整跑完
5 key×mode 才返回结论 (chain budget `NVU_TIER_BUDGET_GLM5_2_NV=120s`, 实测 215-247s).
cc4101 的 header/ttfb timeout 被 `min(120, UPSTREAM_TIMEOUT=60)=60s` 封顶 (R1420 min()
bug + R1412 只提到60的不完整修复). 60s < 120s chain budget → cc4101 在 nv_gw 合法重试
中途就超时, 判 primary 失败, 累计 5 次 (`CC4101_PRIMARY_FAIL_THRESHOLD=5`) → breaker
OPEN 60s → fast-fail 503. OPEN 60s 后 HALF_OPEN, CC 重试 → 又 60s 超时 → re-OPEN. 死循环.

### R1412 注释自证

compose line 166 (R1412) 自己写了 "nv_gw需轮换2-3 key(chain budget 120s)才成功, 总恢复
~160s ... 5次失败熔断OPEN 60s -> CC持续503卡住(2026-07-15 17:58-18:02实锤). 提至60s".
但 60s 仍 < 120s, 2026-07-16 01:35 同故障复发. 注释写了"总恢复~160s"却只提到 60 — 不完整.

### R1420 min() 封顶 bug

`upstream.py:95 header_timeout = min(header_timeout, timeout)` 用 body timeout
(UPSTREAM_TIMEOUT=60) 封顶 header_timeout. R1420 注释(line 182-186)说"header 阶段不受
body timeout 限制, 故用 120", 但 line 95 恰恰封顶了 — 自相矛盾, 120s 从未生效.

## 二、4 个改动 (全部 HM2 cc4101)

### 改动 1: 删 R1420 min() 封顶 (upstream.py:95)

`_call_upstream` 删 `header_timeout = min(header_timeout, timeout)`. header(getresponse 等首
字节) 与 body(流式 read poll, CC4101_STREAM_POLL_S) 超时解耦. header 给到 R1420 缩放值
(≤120s), body 由 stream poll + idle-watcher 兜底.

### 改动 2: UPSTREAM_TIMEOUT 60→130 (compose cc4101)

130s = 120s chain budget + 10s 余量. 让 nv_gw 有合法时间跑完 chain.

### 改动 3: breaker 阈值放宽 (compose cc4101 新增 env)

- `CC4101_PRIMARY_FAIL_THRESHOLD=8` (config默认5→8): 5 太敏感, NVCF 偶发抖动连续5次就 OPEN 误杀.
- `CC4101_PRIMARY_SKIP_S=30` (config默认60→30): OPEN 了也更快 HALF_OPEN probe.

### 改动 4: breaker 只记"真坏" (upstream.py `_try_primary` except 块)

区分 "cc4101 自抢超时" vs "nv_gw 真坏":
- `server_5xx` (nv_gw 明确返回 5xx) → 计数
- `timeout` 且耗时 > 120s (nv_gw 跑完 chain 仍没好) → 计数
- `conn` / `unexpected` → 计数
- `timeout` 且耗时 < 120s (大概率 cc4101 抢断) → **不计数**, 记 `PRIMARY-FAIL-SKIP-CIRCUIT` 日志

## 三、验证 (改后有验证)

| 项 | 结果 |
|---|---|
| health | `{"status":"ok"}` |
| env | UPSTREAM_TIMEOUT=130, FAIL_THRESHOLD=8, SKIP_S=30 ✓ |
| upstream.py | 2 处 R1602 标记, min 封顶已删 ✓ |
| 小请求(非流式) | 200 "Hello there friend!" ~10s ✓ |
| 大context流式(120K, input_tokens=40007) | 200 message_start+DONE, 无 PRIMARY-FAIL 无 BREAKER-OPEN ✓ |
| 重启后残留 BREAKER | 0 (改前每分钟都有) ✓ |
| 后台 monitor | 已起, 持续观测生产流量 |

## 四、不做的 (边界)

- 不改 nv_gw (budget 120s 是设计意图, 让它跑完才返回 502 是对的)
- 不改 HM1 (本次只治 HM2; HM1 R1601 移植未受影响, 本地 CC 仍走 40001)
- 不切本地 CC 到 4101 (仍等用户单独批准)
- 不动 agent 配置 (model/thinking/tool_calls 不碰)

## 五、铁律符合性

1. 改前有数据 ✓ (cc4101日志+nv_gw日志+DB+代码行号+R1412注释自证)
2. 改后有验证 ✓ (7项验证+后台monitor)
3. 聚焦 cc4101→nv_gw 链 ✓
4. 网络用 mihomo ✓ (不涉及, NVCF 劣化是上游)
5. 写入仓库 ✓ (本文件)
- 铁律"只改HM1不改HM2": **本次破例改 HM2**, 用户明确要求"彻底解决远程CC"+AskUserQuestion批准方案A. 记录在案.
