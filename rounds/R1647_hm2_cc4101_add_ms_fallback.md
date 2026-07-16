# R1647 (renamed from local R1643 draft to avoid repo R1643 collision)
# R1643: HM2 cc4101 加回 glm5.2_ms fallback（兜底 glm5.2_nv）

## 背景与目标

远程 HM2 上的 CC 走 `cc4101(4101) → nv_gw(40006) glm5.2_nv`。NVCF 的 glm5.2_nv 极度不稳定
（header/ttfb 60s 超时 + content_filter 空流），频繁让远程 CC 中断。用户要继续优先用
glm5.2_nv（NV 不限额），但在 nv 失败时由 ms_gw 的 glm5.2_ms（每天限额）兜底，让 CC 不中断。

R851/R854 当年按用户要求把 cc4101 的 ms_gw fallback **删干净了**（只剩 primary 一档，失败
返回 error 让 CC 重试）。现在需求反转：把 fallback 加回来。删除是干净的——`_call_upstream`
是通用函数，ms_gw 与 nv_gw 接口完全一致（同 `/v1/chat/completions` OpenAI 流式、Bearer token），
加回等于把已删的 stage-2 重新接上，非新功能。

## 核心约束（不可违背）

1. **中途流挂不能切 fallback**：cc4101 一旦 `stream_to_anth` 给 CC 发了 SSE header（200 + 
   `text/event-stream`），就无法回退换上游（stream.py:59 注释明确）。fallback **只能**在 
   header/connect 阶段失败时切——即 `execute_request` 里 `_try_primary` 抛 `_UpstreamError`、
   `result.success=False` 的时刻，此时 handlers.py:176 还没给 CC 发任何字节，可以干净切。
2. **中途流挂保持现状**：stream.py 的 zombie/content_filter 检测 → emit api_error 让 CC 重试
   整个请求（下次大概率命中已 OPEN 的 ms fallback）。不改 stream.py，复用 R848/R1640 已验证逻辑。
3. **只改 HM2**：用户明确聚焦远程。HM1 cc4101 保持现状（源码同步留待后续）。破铁律"只改HM1"，
   本轮显式豁免，仅 HM2。
4. **fallback 是末位兜底**：nv 不限额优先保，ms 每天限额省着用。触发策略 = breaker OPEN 直走 
   ms（省 nv 超时）+ 未 OPEN 时单请求 nv 失败也立即试 ms（不丢请求）。两者结合。

## 触发策略（两者结合）

- **breaker OPEN 期间**（nv 连续 ≥8 次失败，`CC4101_PRIMARY_FAIL_THRESHOLD=8`）：直接跳过 primary，
  首走 ms_gw。冷却 30s（`CC4101_PRIMARY_SKIP_S=30`）后 HALF_OPEN probe nv 一次。省 ms 配额的
  主路径——不在每条请求上等 nv 超时 60-120s。
- **breaker CLOSED/未 OPEN 时**：primary 先试；primary 失败（5xx/conn/timeout/`client_4xx` 不重试）
  → 立即试 ms 一次。成功则返回，失败则返回 ms 的错误让 CC 重试。每条失败请求消耗一次 ms 配额，
  但不丢请求、不等 nv 跑满超时。
- **ms 也失败**：返回 ms 的 error_json 给 CC，CC 自行重试（下次 nv 大概率恢复）。ms 不设 breaker
  （它每天限额自然限流，加 breaker 反而误杀）。

## 改动清单（只改 HM2，bind-mount 改源码 + 取消 env 注释）

### 文件 1: `/opt/cc-infra/proxy/cc4101/gateway/config.py`

加回 fallback 配置（env 可控，默认仍指向 ms_gw）：

```python
# ─── Upstream (R1643: 加回 ms_gw fallback，末位兜底 glm5.2_nv 失败) ──
PRIMARY_UPSTREAM_URL  = os.environ.get("PRIMARY_UPSTREAM_URL",  "http://nv_gw:40006/v1/chat/completions")
PRIMARY_UPSTREAM_MODEL = os.environ.get("PRIMARY_UPSTREAM_MODEL", "glm5_2_nv")
PRIMARY_UPSTREAM_TOKEN = os.environ.get("PRIMARY_UPSTREAM_TOKEN", "nv-gw-token")
# R1643: 恢复 R854 删除的 fallback。None = 禁用 fallback(回到 R854 行为)。
FALLBACK_UPSTREAM_URL  = os.environ.get("FALLBACK_UPSTREAM_URL",  "http://ms_gw:40007/v1/chat/completions")
FALLBACK_UPSTREAM_MODEL = os.environ.get("FALLBACK_UPSTREAM_MODEL", "glm5_2_ms")
FALLBACK_UPSTREAM_TOKEN = os.environ.get("FALLBACK_UPSTREAM_TOKEN", "ms-gw-token")
```

### 文件 2: `/opt/cc-infra/proxy/cc4101/gateway/upstream.py`

改 `execute_request`：primary 失败后加 `_try_fallback` stage。

- 导入新增 `FALLBACK_UPSTREAM_URL/MODEL/TOKEN`。
- `_call_upstream` 不动（已通用）。
- `execute_request` 流程改为：
  1. `is_primary_open()` → 真 → 直接 `_try_fallback("fallback")`（不再 fast-fail 503）。
     fallback 成功 → return；fallback 失败 → 返回 fallback 的 error（仍带 503 兜底）。
  2. 否则 `_try_primary("primary")`：True → return；`client_4xx` → return（不 fallback，4xx 是
     请求级错误，ms 也会 4xx）；retryable 失败 → 进 stage 2。
  3. **Stage 2 `_try_fallback("fallback")`**：用 ms_gw 的 URL/model/token。header_timeout 给
     `PRIMARY_HEADER_TIMEOUT` 同档缩放值（复用 _hdr_ic 分档，但用更宽松的下限——ms 不像 nv 需要等 
     chain budget，给 60/60/120 三档即可）。fallback 的成败**不**调 `record_primary_*`
     （breaker 只盯 primary）。fallback 成功 → `result.upstream_used="fallback"`、
     `metrics["fallback_triggered"]=True`。fallback 失败 → 用 fallback 的 error 返回。
- `_try_primary` 内部不动（仍按 R1602/R1638 的 should_record 逻辑计 breaker）。
- `_try_fallback` 新增：复用 `_call_upstream`，失败时分类 error_kind/status/json，不碰 breaker。
- `UpstreamResult` 不动字段（已有 error_* 全套）。

### 文件 3: `/opt/cc-infra/proxy/cc4101/gateway/handlers.py`

- `metrics["fallback_triggered"]` 默认 False 不变；fallback 成功时由 upstream.py 置 True（已支持）。
- handlers.py:176 失败分支不变——result.success=False 时返回 error（现在是 ms 也失败的情况）。
- 成功分支不变——`stream_to_anth` / `collect_stream_to_anth` 接 `result.resp/conn`，对 primary/fallback
  透明（stream.py 只看 resp/conn，不关心哪个上游；但 stream.py 的 zombie 检测要正确标记
  `upstream_used`——已在 metrics 里，R848 的 `_record_primary_stream_fail` 已守 `upstream_used=="primary"`，
  fallback 的中途挂不计 breaker，符合预期）。

### 文件 4: `/opt/cc-infra/docker-compose.yml`（HM2，cc4101 段）

取消三行注释，启用 fallback env：

```yaml
    - FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
    - FALLBACK_UPSTREAM_TOKEN=ms-gw-token
    - FALLBACK_UPSTREAM_MODEL=glm5_2_ms
```

（compose 里 `depends_on: [nv_gw, ms_gw]` 已就绪，网络 `cc-net` 通。）

## 不改的（明确边界）

- **stream.py 不动**：中途流挂的 zombie/content_filter/empty 路径复用现状，emit api_error 让 CC 重试。
- **circuit.py 不动**：breaker 逻辑、阈值 8、冷却 30s 维持。OPEN 时从 fast-fail 503 改为直走 fallback
  （这个改动在 upstream.py 的 `is_primary_open()` 分支里）。
- **HM1 不动**：源码 md5 与 HM2 当前一致，改 HM2 后两边将分歧（留待后续同步轮）。
- **nv_gw / ms_gw 不动**：只动 cc4101。

## 验证清单

1. 改完 `docker compose up -d cc4101`（bind-mount，无需 build），`curl /health` 确认 ok。
2. `docker exec cc4101 env | grep FALLBACK` 确认三行注入。
3. 源码改动 md5 记录到 round 文件。
4. 观察窗口（≥30min）：DB 查 `cc_requests`，看 `fallback_triggered=true` 是否在 nv 失败时出现、
   fallback 成功率、CC 是否不再中断。对比改动前 6h（70req/46OK/65.7%SR，18×upstream_error + 
   5×content_filter）。
5. 监控 ms_gw 日限额消耗（ms_gw health 的 `rr_counters.ms_glm5_2` 增量）——确认 fallback 没疯狂
   打 ms。
6. 写 `rounds/R1643_*.md`，commit + push。

## 风险

- ms_gw 被打爆：若 nv 持续劣化 + breaker 阈值 8 太高，前 8 条都试 ms 兜底可能耗 ms 配额。
  缓解：breaker OPEN 后直走 ms 反而省（不再每条试 nv 超时）。观测后可调阈值。
- fallback header 也超时：ms_gw 偶发慢，fallback 超时则返回 ms error 让 CC 重试。可接受。
- 两边源码分歧：HM1 仍是旧 cc4101（无 fallback）。后续同步轮处理，本轮不兼顾。
