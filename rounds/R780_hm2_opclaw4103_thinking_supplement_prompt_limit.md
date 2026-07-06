# R780: HM2 opclaw4103 — thinking content=null 补 reasoning + prompt 超限预检 + k3 auth-fail cooldown 600→60

> 承接 R761–R765 系列 (5-round unattended mode 之后的用户交互轮).
> HM2-only. HM1 暂不同步 (用户指示, HM2 仍不稳定).

## 用户诉求

1. k3 用户亲自测试 OK, 要求重新核实 (我客观复测仍 403, 尊重用户判断, 缩短 cooldown 不长期隔离 k3).
2. HM1 暂不同步.
3. ms_gw 作为兜底, 确保稳定 (R765 已验证健康, 本轮未改).
4. **openclaw thinking max_tokens 不足, 放容器里处理, 不想让 openclaw 自行处理** (用户原话).

## 改前数据 (openclaw 09:15:34 报错根因)

用户以为 "thinking max_tokens 不足导致 content=null". 实测 openclaw `journalctl --user -u openclaw-gateway` 真实根因不同:

```
09:13:13 [model-fetch] response status=200 elapsedMs=45  ← NVCF 正常
09:13:34 [model-fetch] response status=200 elapsedMs=38  ← NVCF 正常
09:13:51 error=Context overflow: prompt too large for the model (mid-turn precheck)
          ↑ openclaw 自己的 precheck 判断 prompt>128K, 但没立即停止
09:13:53 → 09:14:46 继续 4 次 LLM call (每次 NVCF 200, 25-59s)
09:15:34 error=LLM request timed out. rawError=terminated durationMs=142571
          ↑ embedded_run 累积 142s, AbortController terminated
```

**关键事实**:
- 每次 single LLM call 都 status=200, opclaw4103→nv_gw→NVCF 链路本身正常.
- 142s 超时是 openclaw embedded run **累积** 7 次 call 的总时长, 不是单次 LLM 超时.
- 触发点是 "Context overflow: prompt too large" (openclaw 内部 precheck), openclaw 检测到后没立即 abort, 继续 retry 累积超时.
- 单独看 "thinking content=null" 是另一个问题 (glm5_2_nv thinking 流式只发 reasoning_content 不发 content).

用户确认 "两个都修" (既修 LLM timeout, 也修 content=null).

## 本轮修改 (HM2 only, opclaw4103 容器内, bind-mount 共享 forwarder.py)

### 改动 1: prompt 超限预检 (避免 Context overflow 后 retry 累积 142s 超时)

**文件**: `proxy/cc-adapter/gateway/app.py` + `forwarder.py` + `config.py`

`_handle_chat` 入口加预检: 估算请求 token 数 (chars/4 粗估), 超 `PROMPT_TOKEN_LIMIT` 直接返回 400 `context_length_exceeded`, 不转发 NVCF. 让 openclaw 立即收到明确错误, 不再 retry 累积.

- `config.py`: `PROMPT_TOKEN_LIMIT = int(os.environ.get("PROMPT_TOKEN_LIMIT", "0"))` (0=禁用, 默认禁用)
- `forwarder.py`: `_estimate_tokens(oai_body)` + `_prompt_too_large(oai_body)` 函数
- `app.py`: `_handle_chat` 在 `_log REQ` 后调 `_prompt_too_large`, 超限直接 400
- compose: `opclaw4103` env `PROMPT_TOKEN_LIMIT=120000` (glm5_2_nv context 128K, 留 8K 给 output)

400 响应体:
```json
{"error": {"type": "invalid_request_error", "code": "context_length_exceeded",
           "message": "This model's maximum context length is 120000 tokens. However, your messages resulted in {est_tokens} tokens. Please reduce context (e.g. /reset or /new).",
           "est_tokens": 150001, "limit": 120000}}
```

### 改动 2: 流式 content=null 补 reasoning_content (thinking 模式 content 缺失)

**文件**: `proxy/cc-adapter/gateway/forwarder.py` `_stream_from_upstream`

glm5_2_nv thinking 流式: NVCF/ModelScope 只发 `reasoning_content` delta, `content=""` (空字符串), 思考用完 max_tokens 时 `finish_reason=length`, content 全程为空. openclaw 等不到 content → 后续可能超时/空响应.

修复: 流式透传时累积 reasoning_content, 跟踪是否发过非空 content. 流正常结束前 (yield done 之前), 若 `not content_seen and reasoning_buf`, 补发一个 content chunk = reasoning 全文, `finish_reason=stop`.

- `config.py`: `SUPPLEMENT_REASONING_AS_CONTENT = os.environ.get("SUPPLEMENT_REASONING_AS_CONTENT", "0") == "1"` (默认禁用)
- `forwarder.py` `_stream_from_upstream`: 加 `reasoning_buf` / `content_seen` / `last_chunk_template`, 流末补 content
- compose: `opclaw4103` env `SUPPLEMENT_REASONING_AS_CONTENT=1`

**R766c 修正**: content_seen 判定从 `content is not None` 改为 `isinstance(c_val, str) and c_val`. 因为 ms_gw 返回 `content=""` (空字符串), `is not None` 误判为有 content, supplement 不触发.

**R766d 修正**: fallback notice 插入条件同步对齐 — 只在 content 非空字符串时插 notice, 避免 ms_gw `content=""` 触发误插.

### 改动 3: k3 auth-fail cooldown 600→60 (尊重用户判断)

**文件**: `docker-compose.yml` nv_gw env

R764 引入 `KEY_AUTHFAIL_COOLDOWN_S` (per-key cross-tier auth-fail), 默认 600s. 用户坚持 k3 亲自测试 OK, 我客观复测 (HM1+HM2+容器+宿主, pexec+integrate) 仍 403 Forbidden, k1 同环境 200 OK. 无法解释差异, 尊重用户判断, 缩短到 60s — 既给短暂保护 (避免单次 403 立即重试), 又不长期隔离 k3.

- compose: `nv_gw` env `KEY_AUTHFAIL_COOLDOWN_S=60` (新增, 之前是代码默认 600)

## 影响范围 (共享 forwarder.py 的影响控制)

`forwarder.py` 被 hm4104 / opclaw4103 / oc4105 三个容器共享 (bind-mount). 三个改动全部 env 开关, 默认禁用:
- `PROMPT_TOKEN_LIMIT=0` (禁用) — 仅 opclaw4103 设 120000
- `SUPPLEMENT_REASONING_AS_CONTENT=0` (禁用) — 仅 opclaw4103 设 1
- hm4104 / oc4105 不受影响 (env 未设, 走默认禁用)

## 验证

### 验证 1: prompt 超限预检
```
构造 150001 token prompt → POST opclaw4103/v1/chat/completions
HTTP 400, error.code=context_length_exceeded, est_tokens=150001, limit=120000
opclaw4103 日志: PROMPT-TOO-LARGE est_tokens=150001 > limit, 直接 400 不转发
✓ 不转发 NVCF, 避免 retry 累积
```

### 验证 2: content=null 补 reasoning (max_tokens=200 触发)
```
POST glm5_2_nv stream=true max_tokens=200 "详细解释量子纠缠" (thinking on)
93 reasoning chunks (412 chars), 0 真实 content chunk, finish_reason=length
opclaw4103 日志: SUPPLEMENT-CONTENT 流末补 content: 整流无 content delta, reasoning 412 chars, finish=length
客户端收到: 1 个 supplement content chunk = 412 chars (reasoning 全文), finish=stop
✓ thinking 用完 token content 未发时, 流末补 reasoning 作为 content
```

### 验证 3: 正常短请求不误触发
```
POST glm5_2_nv stream=true max_tokens=500 "1+1=?" (thinking on)
49 reasoning + 3 content chunks, real content="1 + 1 = 2", [DONE] 出现
SUPPLEMENT 未触发 (content_seen=True, 有真实 content)
✓ 正常路径不受影响
```

### 验证 4: k3 cooldown 60s
```
docker exec nv_gw env | grep KEY_AUTHFAIL → KEY_AUTHFAIL_COOLDOWN_S=60
k3 403 后 60s 即可重新尝试 (而非 600s 长期隔离)
```

### 验证 5: 健康检查 + 语法
```
opclaw4103 /health = ok, env 加载正确
forwarder.py / app.py / config.py ast.parse 全 OK
```

## 预期效果

1. openclaw Context overflow 场景: 立即收到 400, 不再 retry 累积 142s 超时.
2. openclaw thinking 流式 content=null 场景: 流末收到 reasoning 作为 content, 不再空响应.
3. k3 403 后 60s 恢复 (不再 600s 长期隔离), 尊重用户"k3 没问题"的判断.

## 未解决 / 后续

- **k3 403 差异**: 用户坚持 OK, 我复测 403. 无法解释. 60s cooldown 是折中. 若用户后续仍坚持, 可考虑完全移除 k3 的 auth-fail cooldown (但这会让真 403 key 反复重试浪费 tier budget).
- **HM1 同步**: 用户明确 "HM1 暂不考虑同步, HM2 还不稳定". 本轮所有改动仅在 HM2.
- **ms_gw 稳定性**: R765 已验证健康 (29 cycles/30min, 0 EXHAUSTED), 本轮未改. R766c/d 修正了 ms_gw `content=""` 的判定, 反而让 ms_gw fallback 路径更准.
- **glm5_2_nv HM2 整体不稳**: 测试中观察到 "all 5 keys failed: empty200=1, timeout=1, other=1" + PEER-FB 到 HM1. 这是 NVCF 平台侧/HM2 网络问题, 不是 R766 能修的. fallback 到 ms_gw 兜底正确.

## 参数表

| 参数 | 旧值 | 新值 | 位置 |
|---|---|---|---|
| PROMPT_TOKEN_LIMIT | (无, 禁用) | 120000 | opclaw4103 env (新) |
| SUPPLEMENT_REASONING_AS_CONTENT | (无, 禁用) | 1 | opclaw4103 env (新) |
| KEY_AUTHFAIL_COOLDOWN_S | 600 (代码默认) | 60 | nv_gw env (新) |
| content_seen 判定 | `content is not None` | `isinstance(c,str) and c` | forwarder.py R766c |
| notice 插入条件 | `content is not None` | `isinstance(c,str) and c` | forwarder.py R766d |

## 提交

- 源码: `proxy/cc-adapter/gateway/{forwarder,app,config}.py` (HM2 bind-mount, 已备份 .bak.R766)
- compose: `docker-compose.yml` (HM2, opclaw4103 + nv_gw env, 已备份 .bak.R766 / .bak.R766b)
- 本 round file: `rounds/R780_hm2_opclaw4103_thinking_supplement_prompt_limit.md`
