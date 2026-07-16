# R1640: HM2 远程 CC 502 死循环根治 — cc4101 header_timeout 倒挂 + content_filter breaker 误计 (纯改 cc4101, 不动 nv_gw)

> 远程 HM2 CC 卡死 502 不动 (18:56-19:37 实测 9+ 次死循环). 复杂任务, 先规划(plan r1638) 再动手, 末尾端到端测试.

## 改前数据 (实测)

### 报错点 (精准)
HM2 cc4101 日志反复 (18:56-19:37, 9+ 次):
```
[PRIMARY-FAIL] primary (glm5_2_nv) timeout status=0 after ~90500ms (primary): header/ttfb timeout after 90s: timed out
[PRIMARY-FAIL-SKIP-CIRCUIT] primary timeout after 90500ms < chain budget 120s — NOT counted toward circuit
→ returning api_error, CC will retry
```
CC 立即重试同请求 → 又 90s → 无限循环. DB `cc_requests`: `status=502 error_type=upstream_error duration_ms~92000 ttfb_ms=NULL`, 全是 `cc_stream=False tools=30 total_input_chars=242-243K` 大上下文请求.

### 双死根因 (两条独立)

**死根1: cc4101 header_timeout 90s 倒挂 nv_gw chain budget 120s (BrokenPipe 死循环)**
- cc4101 `upstream.py:193-196` R1420 分档:
  ```python
  if _hdr_ic > 350000: _hdr_to = 120
  elif _hdr_ic > 200000: _hdr_to = 90   # ← 死循环卡在这档 (242K)
  elif _hdr_ic > 50000: _hdr_to = 60
  else: _hdr_to = PRIMARY_HEADER_TIMEOUT (=25)
  ```
- nv_gw first-byte deadline (`handlers.py:706-714`) **镜像分档**: 200-350K 档 `_fb_s = 90`. 加 nv_gw chain budget `NVU_TIER_BUDGET_GLM5_2_NV=120s`.
- 242K 落 200-350K 档: cc4101-header **90s** = nv_gw-first-byte **90s** 完全相等, 但 cc4101 比 nv_gw 先开始计 90s (cc4101 发 conn + nv_gw 接到再发 NVCF 都耗时) → cc4101 总是先到 90s 抢断 → `conn.close()` 同时 nv_gw 仍在等 NVCF → nv_gw 写 `BrokenPipeError: [Errno 32] Broken pipe` (实测日志).
- R1602 当时改 60→130 (UPSTREAM_TIMEOUT body 那一档) **不覆盖**这; R1420 分档阈值 200K-350K 取了 90s 假设 NVCF 大请求 TTFB<90s, 但当前 NVCF 180-240K 请求首字节经常 90-120s+ (nv_gw 日志实锤 364-383K 档 first-byte deadline 120s 都把 nv_gw 自己逼到 timeout).

**死根2: cc4101 stream.py content_filter err_chunk 误计 breaker (二次 OPEN 死循环)**
- nv_gw 在 first-byte/total/no-content-gap deadline 主动 break 时发 `finish_reason=content_filter error SSE chunk` (nv_gw 日志 `NV-UPSTREAM-ERROR-CHUNK zombie=False error_type=stream_first_byte_timeout/stream_total_deadline/stream_no_content_gap`), 设计意图 (R1408) = 让 CC 重试, **不想计 breaker**.
- cc4101 `stream.py:483-487` 收到 `finish_reason=content_filter` → `_record_primary_stream_fail("upstream_content_filter")` → `record_primary_failure()` **每次都计** breaker (R848 设计).
- 实测已 4/8 次 (日志 `CIRCUIT-STREAM-FAIL recorded to circuit breaker` 18:54/19:14/19:16/19:19), 8 次 (`CC4101_PRIMARY_FAIL_THRESHOLD=8`) 即 OPEN 503 死循环.
- **关键 polarity**: 这些主动 break **全 `stream_content_chars=0 reasoning_chars=0`** (实测 `output_tokens=0`, 8/8 req 全 0); 真僵尸 (`zombie_clean_eof` L304 / `zombie_empty_completion` L510) 往往有非零内容累积. **可用 "无内容 content_filter" 区分 nv_gw 主动快速失败 vs 真坏**.

### 方向 (用户 AskUserQuestion 两轮定)
- "仅改 cc4101 不动 nv_gw" (R1635 铁律延续 + 用户选).
- "分档+stream.py 不计误治 (推荐)": polarity 不计 breaker 的 nv_gw 主动信号, 同时破两个死循环.

## 变更 (HM2 + HM1 两边同步, 全在 cc4101)

### 改动1: `upstream.py:195` R1420 分档 90→120
两档合并 (`>200000` 也给 120s, 对齐 nv_gw chain budget 120s):
```python
if _hdr_ic > 350000:
    _hdr_to = 120
elif _hdr_ic > 200000:
    _hdr_to = 120   # R1638/R1640: 90→120. 死根1倒挂...
elif _hdr_ic > 50000:
    _hdr_to = 60
else:
    _hdr_to = PRIMARY_HEADER_TIMEOUT
```
注释记: nv_gw 200-350K 档 first-byte 90s 仍会主动 break 发 content_filter err_chunk (干净 Scenario A), cc4101 (120s 未到) 正常收到 → polarity 判定 → 干净 api_error → CC 重试. **死循环1破**: cc4101 不再抢先 kill nv_gw connection (无 BrokenPipe).

### 改动2: `stream.py:483` content_filter polarity 分流
```python
if finish_reason == "content_filter":
    stream_zombie = True
    metrics["error_type"] = "upstream_content_filter"
    # R1638/R1640: polarity 分流 (死根2). nv_gw 主动 break (first-byte/no-content-gap/total
    # deadline) 发的 content_filter err_chunk content=0 reasoning=0 (output_tokens=0 实测 8/8),
    # 设计意图=R1408 让 CC 重试, **不**计 breaker — 否则累积 8 次 → circuit OPEN 503 死循环 (已 4/8).
    if stream_content_chars == 0 and stream_reasoning_chars == 0:
        _log("ZOMBIE-CONTENT-FILTER", "...nv_gw active fail, no content yet — NOT counted to breaker...")
    else:
        _record_primary_stream_fail("upstream_content_filter")
        _log("ZOMBIE-CONTENT-FILTER", "...mid-flight zombie, counted to breaker...")
    _emit_graceful_end(zombie=True)
    return
```
**不碰**: `zombie_clean_eof` (304) / `upstream_content_filter_malformed` (353) / `zombie_empty_completion` (510) / StreamStallWatcher/SocketTimeout/UpstreamDisconnect (535/542/549) — 留观察, 不在本轮 polarity 范围.

### 附带: upstream.py L262 修预存 mojibake
R849 注释 "旧???:" (3×U+FFFD) 字节损坏, 精确按字节修为 "旧洞:". UTF-8 铁律. (R1638_pre 备份验证非本轮引入, 但既然在做规范化顺手修.)

### 不改 nv_gw
nv_gw first-byte 200-350K 档现状 90s **不动** (用户选 + 设计意图: nv_gw 先主动 break 发 err_chunk 是 Scenario A 干净路径, 比拖到 120s 更早给 CC 重试信号).

## 验证清单

| 项 | 结果 |
|---|---|
| HM1 `upstream.py` 改动1 + 语法 ast.parse | ✅ OK |
| HM1 `stream.py` 改动2 + 语法 | ✅ OK |
| HM1 `upstream.py` U+FFFD 修复 | ✅ 0 (含预存 L262 修) |
| HM2 scp 同步 + 两边 md5 一致 (upstream + stream) | ✅ |
| 两边 `docker restart cc4101` + `/health` 200 | ✅ 两边 status=ok |
| 两边启动日志无 import 错 | ✅ 干净 |
| **端到端测试**: HM2 cc4101 发 `glm5.2_cc` stream=true 请求 | ✅ HTTP 200, 完整 Anthropic SSE 流 "我是一个由Z.ai训练的GLM大语言模型..." |
| 重启后远端 CC 恢复发新请求 (msgs=26/28/43) | ✅ (死循环解除第一信号) |
| 30min Monitor: 死根1 不复发 (无 PRIMARY-FAIL ~90s, 无 BrokenPipe) | 🔄 观测中 |
| 30min Monitor: 死根2 不复发 (无 CIRCUIT-STREAM-FAIL for content_filter, 见 "NOT counted to breaker" 日志) | 🔄 观测中 |

## 参数表
无 env 改 (纯 .py 改动, 不碰 compose env).

## 回退
`upstream.py.bak.R1638_pre` + `stream.py.bak.R1638_pre` 双地备份. `docker cp 回 + restart`. (L262 mojibake 修复不可逆但无害 — 字节损坏本就该修.)

## 铁律
- 改前数据 (实测倒挂+误计) / 改后验证 (端到端+30min Monitor) / 聚焦链路 (只 cc4101 .py, 不动 nv_gw/agents/env) / 写入仓库 (本 round + commit).
- 破例改 HM2 — 治远程 HM2 CC 死循环 (用户明确 "治本机+远程两边代码同 sync"). HM1 同步是 R1635 一致的延续.
