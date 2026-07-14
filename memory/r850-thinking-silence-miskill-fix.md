---
name: r850-thinking-silence-miskill-fix
description: "R850 Server error mid-response 真根因=GLM5.2 thinking经NVCF integrate通道首块reasoning后上游长时间静默思考(实测>120s不发chunk),nv_gw idle deadline ttfb后固定90s不刷新+cc4101 IDLE_GAP 100s都不识别思考静默,误切断还在思考的流; 修nv_gw deadline改真内容刷新+thinking翻倍180s,cc4101动态IDLE_GAP见过reasoning用200s"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

# R850: Server error mid-response 真根因 = thinking 静默被误切

## 用户报错
`API Error: Server error mid-response. The response above may be incomplete.` 反复中断.

## 真根因 (实测铁证)
GLM5.2 thinking 请求经 NVCF integrate 通道, 上游在 ttfb 首块 reasoning 后会**长时间静默思考**, 实测 >120s 不发任何 SSE chunk (探针: [0s] chunk#1 reasoning=130c, [10s-120s] 再无chunk).

但 nv_gw 的 `stream_idle_deadline = ttfb + 90s` **固定不刷新** (R835 设计, 防 drip keep-alive 绕过 per-read timeout), cc4101 的 `IDLE_GAP=100s` 也是 ttfb 后固定. 两层都在 ttfb 后固定时间兜底, **不识别"上游在思考中的长静默" vs "真断流"**, 把还在思考的流误切 → nv_gw 发 content_filter → cc4101 emit api_error → CC 报 "Server error mid-response".

### 时序铁证 (req=3f659ccf, 重启前)
```
19:41:22  nv_gw NV-REQ (thinking, chat_template_kwargs.enable_thinking)
19:41:24  nv_gw ttfb (NV-GLM52-SUCCESS), thinking timeout 150s
          ↑ 上游首块 reasoning 到达
19:41:56  nv_gw STREAM-DEADLINE 触发 (ttfb+90s 固定, 不刷新) → 发 content_filter
19:41:56  cc4101 ZOMBIE-CONTENT-FILTER → emit api_error → CC 报 "Server error mid-response"
```
注意: nv_gw 自己给了 thinking 上游 timeout 150s, 但自己 idle deadline 90s < 150s, **自己先把自己切了** — 设计矛盾.

## 为什么我自己 (HM1) 不卡
走 legacy_cc_1(40001)→legacy_ms_litellm(41001, glm5.1 纯 MS), 不经 nv_gw integrate 通道, 无 thinking 长静默问题.

## 修复 R850 (已应用, bind mount 宿主源码, 重启验证)

### Patch A: nv_gw `/opt/cc-infra/proxy/nv-gw/gateway/handlers.py` (治本)
`_stream_openai_passthrough` 流式循环:
1. 新增 `_idle_s = NVU_STREAM_TOTAL_DEADLINE_S` (默认90), thinking 请求 (`metrics["thinking_type"]` 非空) `_idle_s *= 2` → 180s.
2. `stream_idle_deadline` ttfb 时设一次, **之后每收到真内容(content/reasoning_content/tool_calls)刷新 = now + _idle_s**.
3. deadline 检查改用刷新后的值, log 标 "after last-real-content".
4. 关键: thinking 静默期上游不发 chunk → nv_gw 的 read 阻塞 → deadline 不检查也不误切 (只在收到 chunk 时检查). 真断流 = read 返回空或抛异常, 仍能兜底.

### Patch B: cc4101 `/opt/cc-infra/proxy/cc4101/gateway/stream.py`
stall-watcher IDLE_GAP 检查点改动态:
- `_idle_gap = 200.0 if stream_reasoning_chars > 0 else CC4101_STREAM_IDLE_GAP_S` (100s)
- 见过 reasoning_content (thinking 流) 用 200s 容纳长思考静默, 非 thinking 用 100s 快速兜底.
- 200s > nv_gw thinking 180s, 让 nv_gw 先发 content_filter, cc4101 后兜底.

## 验证 (重启后)
- 探针1 (简单 thinking "100字解释量子纠缠"): **39s 正常完成** r=1372c c=228c, 未被切断 ✅
- 探针2 (复杂多步推理): **63s 正常完成** EOF, 未被切断 ✅
- 重启后 nv_gw STREAM-DEADLINE 计数 = **0** (重启前每90s必触发) ✅
- 生产: 待真实 CC 流量验证, 但机制上 thinking 静默不再被误切.

## 与 R847/R848/R849 关系
- R847: IDLE_GAP 60→100s (数值, 治标, 不够)
- R848: 流式失败记 circuit (7失败点)
- R849: record_primary_success 改流式真正完成才记 (不重置)
- **R850: 治本 — deadline 按真内容刷新 + thinking 翻倍, 根除"思考静默被误切"**
- R847 的 100s 固定值被 R850 的动态值取代 (非 thinking 仍100s, thinking 200s).

## 关联
- [[r847-deadline-inversion-root-cause]] — R847 数值倒挂, R850 改为动态刷新取代.
- [[r848-stream-circuit-breaker-fix]] — circuit 累积, R849 修盲区, R850 修误切源头.
- [[r846-stream-interrupted-fix]] — 三层根因 (OSError+total_deadline+malformed).
- [[cc-chain-layout-hm2]] — HM2 链路.
EOF