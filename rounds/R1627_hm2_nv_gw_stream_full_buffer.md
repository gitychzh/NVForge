# R1627: HM2 nv_gw stream 全量缓冲到结束再 flush (方向 C) — 根治 CC mid-response 中断

> **破例改 HM2** (R1621/R1621b/R1621c 同链延续). CC 报错走的就是 HM2 nv_gw (trace 全从 HM2 查到).
> 铁律 "只改 HM1 不改 HM2" 本轮明确授权破例.

## 问题 (用户报错)

远程 CC 报: `API Error: Server error mid-response. The response above may be incomplete.`
CC 卡死, 需手动发"继续"才恢复. 用户首要目标: **先解决 CC 不中断的大 BUG**.

## 根因 (全程数据支撑, 非猜测)

### 16:08:16 失败请求完整 trace (req=8861e168, DB 实锤)
```
16:08:16  CC → nv_gw (glm5_2_nv, k5 integrate, stream=True, input=161K)
16:08:25  NVCF 返回 200 + 774 字节内容, nv_gw 边读边 flush 给 cc4101  ← Scenario B
          (cc4101 已向用户显示这 774 字节)
16:09:52  NVCF 停止输出, 60s 无新内容 → nv_gw stream_no_content_gap → break
16:09:52  nv_gw 发 [DONE] + conn.close() (Scenario B 路径, content>0)
16:10:32  cc4101 StreamStallWatcher (100s 无真内容) → emit api_error SSE
16:10:32  CC 收到 api_error, 但因已向用户 flush 774 字节 → "mid-response" → CC 不重试, 卡死
```

### 为什么 CC 不自动重试 (推翻先前假设)
- **Scenario A (零内容 + api_error)**: CC 自动重试 (DB 实锤: zombie 后 5-11s 重发同 input, 1-2 次后放弃)
- **Scenario B (已有内容 + api_error)**: CC **不重试** (重试会重复已显示内容) → 卡死需手动"继续"
- 旧代码 (handlers.py:948-980) 在 content>0 走 Scenario B 路径 (发 [DONE] 不发 content_filter)

### 否决两个思路 (数据否决)
1. **延长 60s gap**: 正常成功流输出阶段 (duration-ttfb) **中位 1ms, p90 95ms** — glm5.2 NVCF 是"等久首字然后瞬间吐完"模式, 正常流不会出现 60s 间隙, 60s 是真卡死, 延长只增加卡死时长.
2. **全切 integrate**: 6h 实测 integrate 9×502 (19%) vs pexec 2×502 (12.5%) — integrate 更不稳, 本次失败就是 integrate.

## 方向 C 方案: 全量缓冲到流结束再 flush

### 核心思想
nv_gw 收到 NVCF 200 后, **不立即向 cc4101 flush 内容**, 缓冲到 NVCF 流真正结束 (finish_reason/[DONE]) 再一次性 flush.
- NVCF 正常结束 → cc4101 收到完整响应, CC 不中断 ✓
- NVCF 卡死 (gap/timeout/zombie) → nv_gw 丢弃缓冲, 因从未 flush 任何字节 → **等价 Scenario A (零内容)** → 发 content_filter error chunk → cc4101 → api_error → **CC 自动重试下个 key** ✓

### 架构约束 (已验证, 不引入新超时)
1. cc4101 header_timeout 按 input 缩放 (<50K→25s, >350K→120s), 只管到 nv_gw 回 200 header.
2. nv_gw 在收到 NVCF 200 后立即回 200 header (handlers.py:751), 之后长时间不发 body — 这与当前 NVCF prefill 慢 (TTFB 实测 234s) 等价, cc4101 stall-watcher 只在 ttfb 后 arm, 首内容前不计时 → **不引入新超时** ✓

## 改动清单 (HM2)

| 文件 | 改动 |
|---|---|
| `config.py` | 新增 `NVU_STREAM_FULL_BUFFER` env (默认 "1" 开启, "0" 回旧行为) |
| `handlers.py` `_stream_openai_passthrough` | (1) `buffer_chunks = [] if NVU_STREAM_FULL_BUFFER else None` (2) flush 改写缓冲 `buffer_chunks.append(chunk)` (3) 正常结束 (无 error 且非 zombie) 一次性 `wfile.write(b"".join(buffer_chunks))` (4) 卡死/错误丢弃缓冲走 content_filter (因从未 flush, content 视为 0 → Scenario A) (5) 修正 content_filter / else 分支判定 (缓冲模式不重复走 [DONE] 分支) |

**不改**: upstream.py, cc4101 任何文件, docker-compose.yml, agents 配置.

### 关键逻辑 (改后)
- 正常结束: `buffer_chunks is not None and not error_type and not zombie` → flush 全部缓冲, `_r1627_flushed_downstream=True`, 之后 content_filter/else 分支都不进 (干净结束).
- 卡死 (gap/timeout/zombie): 不 flush 缓冲, `_r1627_flushed_downstream=False`, 走 content_filter 分支 (Scenario A), CC 自动重试.
- 旧行为 (FULL_BUFFER=0): `buffer_chunks=None`, 全程边读边 flush, content_filter 按 `passthrough_content_chars==0` 判定, else 走 [DONE] (Scenario B), 与改前完全一致.

## 内存评估
单请求完整响应缓冲: glm5.2 通常 <50KB, 大 context 长输出最大 ~数百 KB. nv_gw 单线程 (BaseHTTPRequestHandler 同时 1 请求), 内存无压力.

## 部署 + 验证 (改后必有验证)

### 部署
```
cp handlers.py handlers.py.bak.R1627  (源+容器双备份)
[3 个 patch 脚本: import + buffer init + flush 改缓冲 + 正常结束 flush + 分支判定修正 + UTF-8 修复]
docker compose up -d nv_gw   # bind-mount, 但需 docker restart 才重载进程
docker restart nv_gw
```

### 验证 (全部通过)
1. `curl /health` OK ✓
2. `docker exec nv_gw python3 -c "from gateway.config import NVU_STREAM_FULL_BUFFER"` → `True` ✓
3. 直测 nv_gw (curl → 40006): glm5_2_nv stream 请求 200 成功, 响应完整 ✓
4. **端到端 cc4101 (curl → 4101, CC 真实路径)**:
   - CC 收到完整 Anthropic SSE: `message_start → content_block_start → content_block_delta("OK") → content_block_stop → message_delta(stop_reason=end_turn)` ✓
   - nv_gw 日志: `NV-STREAM-BUFFER-FLUSH full-buffer flushed 873b to downstream (content_chars=2c, dur=5431ms)` ✓
5. UTF-8: 新增注释无 U+FFFD 乱码 ✓ (修了一处 patch 引入的 L940 乱码 "缓冲给下游"; 预存 L998 是 R1413 旧注释, 非本轮引入)

## 后续 (留作 R1628+)
- **C-robust**: 把 stream 读取搬进 key 重试循环, nv_gw 内部换 key 重试 (不依赖 CC 自身重试). 若数据发现 CC 1-2 次重试不够 (5 key 全卡死才放弃) 再升级.
- **HM1 代码同步**: HM1 nv_gw 源码版本只到 R1416 (无 R1407/R1408 stream_no_content_gap 逻辑), 与 HM2 (R1627) 已分叉. R1627 patch 结构基于 HM2 的 R1407+ 代码, 不兼容 HM1. 需单独轮次同步 HM1 nv_gw 代码到 HM2 同版本.
- `NVU_STREAM_BUFFER_MAX_KB` 上限: 超限回退边读边 flush (防超大响应内存). 数据积累后再定.

## 回退
`NVU_STREAM_FULL_BUFFER=0` (compose env 或 config.py 默认) + `docker compose up -d nv_gw && docker restart nv_gw` 立即回旧行为.

## 铁律
- 改前有数据 ✓ (全程 DB/metrics/trace 支撑)
- 改后有验证 ✓ (health + 直测 + cc4101 端到端)
- 聚焦 nv_gw ✓ (只改 40006 nv_gw handlers/config)
- 所有修改写入仓库 ✓ (本 round 文件 + commit push)
- 破例改 HM2: CC 报错走 HM2 nv_gw, 同 R1621 链授权
