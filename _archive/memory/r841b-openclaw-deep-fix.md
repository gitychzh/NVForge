---
name: r841b-openclaw-deep-fix
description: R841b 远程HM2 openclaw深度修复:R840空僵尸检测移植+opclaw4103 SUPPLEMENT逻辑修复;抓包+工具调用+思考模式系统性评估
metadata:
  node_type: memory
  type: project
  originSessionId: c3734594-fcf5-43ff-9b8d-e14d8c206a00
---

用户要求:远程HM2 openclaw深度修复+抓包+工具调用失败代码分析+glm5.2_nv思考模式评估。R841(config bug扫描)完成后继续。

## 模型链路确认
openclaw agent(main) → ACP(acpx) → opclaw4103:4103 → PRIMARY nv_gw:40006(glm5_2_nv) → FALLBACK ms_gw:40007(glm5_2_ms) ✓

## 四大发现

### 1. 抓包分析(SSE全链路原始字节)
- NVCF→nv_gw: 纯透传 self.wfile.write(chunk), tool_calls保留
- nv_gw→opclaw4103: 原样+R766 SUPPLEMENT
- opclaw4103→openclaw: write_sse json.dumps(ensure_ascii=False)不丢字段
- R841 timeoutMs修复铁证: 10:51前timeoutMs=undefined→10:51后timeoutMs=180000

### 2. 工具调用"失败"——实际没失败
- E2E之前测echo HELLO_TOOL_TEST成功(返回输出)
- openclaw日志零tool-call错误
- openclaw dist line 2379容错: content有toolCall+stopReason=stop→改toolUse,救回tool_calls
- 但opclaw4103 forwarder.py R766 SUPPLEMENT有3个真实Bug:
  - content_seen只查content字段不查tool_calls → GLM5.2思考模式reasoning+tool_calls+content=""时content_seen保持False
  - content=""空字符串falsy → content_seen误判False
  - SUPPLEMENT触发→reasoning塞content(污染回复)+finish_reason从tool_calls改stop(矛盾)+tool_calls重复

### 3. glm5.2_nv思考模式——是开着的
- nv_gw config.py glm5_2_nv tier: inject chat_template_kwargs.enable_thinking:True (R827重开)
- opclaw4103 SUPPLEMENT-CONTENT日志确认reasoning_content存在(61-533字)
- 旧memory glm52-thinking-toggle-truth是opencode+nvidia链路的,不适用openclaw链路
- 生产72请求指标: stop30(42%)/tool_calls26(36%)/length14(19%), 200:70/502:2(97%), 空输出35(48%其中stop+空25=空僵尸input22649/22682超大context), 慢思考ttfb>30s仅1(1%), duration p50=3.6s p95=28s max=140s
- 思考本身不慢,但放大超大context下的空僵尸响应

### 4. 🔴 R840空僵尸检测从未落地HM2(卡死根因)
- HM2 handlers.py(44049字节)==R814备份, grep content_filter|空僵尸|R840全无
- HM1 handlers.py(60859字节)有完整R840逻辑(688-855行)
- HM2 _stream_openai_passthrough是裸透传, 25个stop+空响应原样喂openclaw→agent loop卡死8min→飞书报Gateway restarting
- HM2缺: config.py 4常量 + handlers.py import + R840僵尸检测+R835 idle deadline+R839 first-byte deadline
- total_input_chars落库HM2已有✓

## 修复(R841b,全部已应用,用户确认"全部应用")

### 修复1: HM2 nv_gw R840/deadline移植
- config.py加4常量: NVU_STREAM_TOTAL_DEADLINE_S=90, NVU_STREAM_FIRST_BYTE_DEADLINE_S=20, NVU_ZOMBIE_EMPTY_CONTENT_CHARS=50, NVU_ZOMBIE_MIN_INPUT_CHARS=5000
- handlers.py import加4常量 + _stream_openai_passthrough加R840僵尸检测+R835 idle deadline+R839 first-byte deadline
- 僵尸命中: 不写终末chunk+写content_filter error SSE chunk→openclaw mapOpenAIStopReason→stopReason=error→throw→empty-error-retry 3次
- 备份: handlers.py.bak.preR840, config.py.bak.preR840

### 修复2: opclaw4103 forwarder.py SUPPLEMENT逻辑修复
- 加tool_calls_seen标记: 见tool_calls就不触发SUPPLEMENT(工具调用响应绝不把reasoning塞content)
- SUPPLEMENT触发条件加not tool_calls_seen(两处:正常流末+流中途异常)
- finish_reason不强制stop: 保留last_finish_reason(若tool_calls则保持,避免矛盾),仅None时默认stop
- 备份: forwarder.py.bak.preR841b

### 容器重建
- docker compose build nv_gw opclaw4103 + docker compose up -d --force-recreate nv_gw opclaw4103
- 容器内验证: R840逻辑9处/config常量2处/forwarder tool_calls_seen 4处 ✓

## 修复效果验证
- R840僵尸检测工作: 12:39:25捕获空僵尸(content_chars=20,input_chars=91956)写content_filter chunk
- openclaw empty-error-retry生效: stopReason=error→resubmitting attempt=2/3→3/3
- 修复前: 空僵尸8分钟卡死; 修复后: 快速error+retry3次(~10秒失败)
- 小context流式正常: 1+1→content="2" finish_reason=stop ✓
- SUPPLEMENT修复后无污染日志

## 关键洞察:main agent context固有88k+
- main agent加载workspace记忆+IDENTITY+25工具schema+openclaw system prompt → input_chars=88609-106532 (p50=90k chars≈22k tokens)
- 这不是会话历史累积(fresh session msgs=2仍88k),是agent启动时固有context
- GLM-5.2在88k+ context下持续返回空僵尸(content_chars=19, NVCF后端大context限制)
- 60%请求input_chars>20k
- 根本治本需减小context或换模型, R840只治"卡死8min"→"快速失败"

## 未做(用户豁免)
- 安全裸奔(0.0.0.0:18789+disableDeviceAuth+origins:*) r835豁免延续
- CLI单次agent run对content_filter不重试(throw冒泡LLM request failed), 飞书/webchat场景runFallbackCandidate会接管

关联: [[r840-openclaw-zombie-empty-stall-fix]] [[glm52-thinking-toggle-truth]]
