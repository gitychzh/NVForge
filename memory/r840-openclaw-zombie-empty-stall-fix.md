---
name: r840-openclaw-zombie-empty-stall-fix
description: "R840根因=NVCF返回200+finish_reason=stop+0~17token空僵尸响应,openclaw收到空流agent loop卡死8min触发watcher重启飞书报Gateway restarting;修复=nv_gw透传检测空僵尸(content<50c+input>5000c+fr=stop+无tool_calls)→写finish_reason=content_filter error SSE chunk→openclaw mapOpenAIStopReason判error→throw→coerceToFailoverError→fallback链生效"
metadata:
  node_type: memory
  type: project
  originSessionId: 4853a593-de20-454d-9f4d-5a9c2e88ef5a
---

# R840 openclaw空僵尸响应卡死根治 (2026-07-11)

## 真根因(铁证链)
用户报"飞书仍报 Gateway is restarting"(R839修复后复发)。深挖发现:
- nv_gw metrics `rid=e0f127e8`: status=200, **output_tokens=6**, finish_reason=stop, input_tokens=29543, dur=9979ms
- 今天5个200响应里3个(60%)是这种"假完成"空僵尸响应(out=0~17tok, fr=stop, in=29k)
- openclaw日志铁证: 00:33:44 `model-fetch response 200 elapsedMs=1891`(6token空响应)→ **00:33:44至00:42:25整整8分41秒完全空白** → 飞书用户消息到达 → 00:42:26 watcher SIGTERM
- b18915ab(heartbeat session)00:33:52正常session.ended,但openclaw主进程"1 active embedded run"挂着
- openclaw agent loop收到空model响应→无法推进/收尾embedded run→阻塞主event loop→不响应飞书→watcher SILENT_MAX=480s重启

## 为什么R835/R839修复无效
R835b idle deadline + R839 first-byte deadline管的是"流已开始但不结束"和"200头但首字节永不来"。但空僵尸响应是:**流正常开始+正常发完6token+finish_reason=stop+[DONE]正常结束**。nv_gw一切正常(ttfb=10s, finish=stop),openclaw reader收到chunk.done正常关闭,buildManagedResponse finalize()完成。问题在agent loop拿到空model输出陷入无法推进状态。deadline修复管不到这个场景。

## 修复方案(R840)
透传模式(`_stream_openai_passthrough`)下,200头已发给openclaw无法回头改502。但可利用openclaw的SSE解析+failover机制:
- openclaw `mapOpenAIStopReason(finish_reason)`: stop→stop(正常); content_filter→error; 任意未识别值→error
- openclaw line: `if (output.stopReason === "error") throw new Error(output.errorMessage)`
- throw冒泡到 `runFallbackCandidate` catch → `coerceToFailoverError` → FailoverError → **model-fallback链生效**(nv_gw/glm5_2_nv → ms_gw/glm5_2_ms → nv_gw/dsv4p_nv)

**nv_gw透传循环实时解析SSE,累积content_chars+tool_calls标记。见finish_reason=stop且content<50c且input_chars>=5000且无tool_calls→判定空僵尸→不写finish_reason=stop chunk→主动写`finish_reason=content_filter` error SSE chunk+[DONE]给openclaw→openclaw判error→throw→fallback。**

## 阈值(config.py,env可调)
- `NVU_ZOMBIE_EMPTY_CONTENT_CHARS=50`: 正常响应最少几十字符,6token≈6字远低于。短回复"OK"虽2字但配合input判定排除
- `NVU_ZOMBIE_MIN_INPUT_CHARS=5000`: 用total_input_chars(请求开始时已知),不用streaming_input_tokens(SSE usage在finish_reason之后才到,时序来不及)。僵尸in_tok~29500→chars~117000;正常"OK"in_tok~11→chars~50。5000排除小请求短回复
- 工具调用绝不判僵尸(即使content空): `passthrough_saw_tool_calls`标记

## 验证(全通过)
- 正常小请求(in_chars=135,"OK"): status=200 fr=stop 正常 ✓
- tool_calls请求(in_chars=311): status=200 fr=tool_calls 正常 ✓
- zombie请求(in_chars=15133,out=2,fr=stop): status=502,返回`finish_reason=content_filter` error chunk,日志`NV-ZOMBIE-ERROR-CHUNK sent` ✓
- 无ValueError traceback(SO_LINGER方案废弃)

## 失败方案记录(避免重复)
- **SO_LINGER RST方案无效**: BaseHTTPServer HTTP/1.0 close先发FIN,curl/node fetch收到200+空body正常结束不抛错。改用SSE error chunk走openclaw正常解析路径
- **让glm5_2_nv走accumulate模式不可行**: R577历史排除原因是_accumulate_stream_to_nonstream重组非流JSON时不提取delta.tool_calls→工具调用结构丢失。openclaw agentic loop依赖tool_calls,走accumulate会全坏
- **改openclaw dist源码不可行**: 已编译,铁律不破坏bundle

## 关键文件
- `/opt/cc-infra/proxy/nv-gw/gateway/config.py`: NVU_ZOMBIE_EMPTY_CONTENT_CHARS, NVU_ZOMBIE_MIN_INPUT_CHARS
- `/opt/cc-infra/proxy/nv-gw/gateway/handlers.py` `_stream_openai_passthrough`(line~681): passthrough_content_chars累积+zombie检测+error chunk写入
- openclaw机制: `/usr/lib/node_modules/openclaw/dist/openai-completions-DTj6G8AI.js` mapOpenAIStopReason(line340); `openai-transport-stream-Dj78Cdnf.js` buildManagedResponse(line815); `model-fallback-CKB2G2qA.js` runFallbackCandidate(line734)+coerceToFailoverError(line742)

## 待观察
未在真实飞书大context对话端到端验证fallback链实际触发(需用户发消息)。源码分析确认链路成立。后续观察openclaw日志是否出现model.fallback_step after zombie,及飞书是否不再报Gateway restarting。

关联:    [[nvcf-pexec-field-semantics]]
