# R1716: nv_gw 流式软全挂 → ms_gw 兜底 barrier (200 落 cc4101 前 peek 首内容 chunk)

> 聚焦 HM2 远程 CC 链路 cc4101→40006(glm5.2_nv). 目标: 尽最大可能不让远程 CC 中断.
> 铁律: 只改 HM2 nv_gw. 不碰 cc4101 (R1711 纯透传). 不碰 ms_gw (R1648d 已支持). 不碰 HM1.

## 背景

R1715 修完 R1704 的 request_id NameError 后, 框架审视发现: 两层 fallback (cc4101 R1643 Stage2 +
nv_gw R1648c execute_request 出口) 触发点都在 "NVCF 返回 200 header 时", 但 NVCF glm5.2 主流
失败是 "200 后流到一半 hang" — 这个点在两层触发点之后, 谁也接不住 → cc4101 透传到一半收到
nv_gw 的 api_error SSE → 502 给 CC → CC 死循环同请求.

## 数据锚点 (6h HM2, glm5_2_nv, nv_requests 表)

```
mode            | 200 | 502 | 软挂 error_type
integrate_us_rr |  70 |  19 | stream_no_content_gap×14, stream_total_deadline×3, zombie×2
pexec_us_rr     |  56 |   5 | zombie×2, NVAnth_NameError×1, first_byte_timeout×1
```

软全挂几乎只发生在 integrate channel (19/24=79%). 不是单 key/单 IP (7894/7896/7899 三个 egress,
k0/k2/k4 三个 key 都中), 是 integrate channel 对 glm5.2 系统性 mid-stream hang.

cc4101 6h: primary 502×43 (avg 168s max 494s) 无一触发 fallback. SR ~83%.

## 根因 (代码精读确认)

`_handle_messages_anthropic` (handlers.py:847) 拿 execute_request success result 后:
`_stream_openai_to_anth` (handlers.py:925) **循环前就 `send_response(200)+end_headers()`**,
200 已落 cc4101, 之后 mid-stream hang 只能发 api_error SSE 关连接, 无法再切 ms.
非流式 collect (`_collect_stream_to_anth`) 不先发 200, 最后才 `_send_json` → 软挂天然可切 ms.

## 方案

### 流式: peek barrier (200 落 cc4101 前)

`_stream_openai_to_anth` 循环前加 peek 阶段:
- while read → parse SSE → 判首内容非空 (content/reasoning/tool_calls)?
- 健康 → 预填 prebuffer (已转 anthropic 的首 chunk bytes) + 预 feed converter →
  send_response(200) → flush prebuffer → 续读流
- 软挂 (first_byte/no_content_gap/empty/zombie) → 关 nv conn → `_ms_fallback_request`
  重放原 oai_body 给 ms_gw → 用 ms 的流续给 cc4101 (cc4101 无感, 只见一个正常 200+SSE)
- ms 也失败 → send_response(200) + api_error SSE 让 CC 重试 (用户确认保持现状语义)

peek deadline 复用已有 `_fb_s` 分档 (50k/200k/350k → 60/45/60s), 数据锚点 p99=32s 留 40%+ 余量.
软挂 no_content_gap avg 128s → peek 在 45-60s 内判软挂, 远早于现状.

prebuffer 不丢: peek 阶段 read 消费 buffer, 读出存 prebuffer bytes, send_response 后 flush,
converter 状态复用 (peek 已 feed 首 chunk, content_chars 已累积). 走 ms 分支则新建 converter.

### 非流式: collect 软挂 → ms 重放

collect 不先发 200, 检测到 content_filter/zombie/empty/mid-stream OSError 后, 在发 502 前:
若 mapped_model in NVU_MS_FALLBACK_MODELS → `_ms_fallback_request` 重放, 成功则递归 collect
(传 `_collect_ms_retried=True` 防死循环), 失败则发 502.

### 零新增函数 (框架简化)

`_ms_fallback_request` (upstream.py:1340) 已具备一切: 深拷贝 oai_body 换 model=glm5_2_ms,
POST ms_gw `/v1/chat/completions`, 返回 r.resp = ms_gw 的 **openai SSE** 流 (同 nv_gw 正常 resp
类型) → handlers `_stream_openai_to_anth` 收 openai SSE 转 anth 天然匹配 (R1648 下沉设计).
无需新建 `_ms_fallback_stream`.

## 改动 (只 nv_gw handlers.py, bind-mount restart)

`/opt/cc-infra/proxy/nv-gw/gateway/handlers.py`:
- 顶部 import 加 `_sse_bytes` (api_error SSE emit), `_ms_fallback_request` (from upstream),
  `NVU_MS_FALLBACK_ENABLED/URL/MODELS` (from config)
- `_handle_messages_anthropic` 两处调用点传 `oai_body` 给 stream/collect 函数
- `_stream_openai_to_anth` 签名加 `oai_body=None`, 加 `mapped_model_pre_fallback` 局部,
  循环前插入 peek barrier (NV-PEEK-OK / NV-PEEK-SOFTFAIL / NV-PEEK-MS-OK / NV-PEEK-MS-FAIL 日志)
- `_collect_stream_to_anth` 签名加 `oai_body=None, _collect_ms_retried=False`,
  发 502 前插 ms 兜底重放 (NV-ANTH-COLLECT-SOFTFAIL / -MS-OK / -MS-FAIL 日志)

不碰: cc4101/, ms-gw/, config.py (env 不变), circuit.py, upstream.py.

## breaker 联动 (顺手)

peek 软挂 → `big_input_breaker.record_big_input_failure` (仅 >250k, 语义=OPEN 后跳过 nv 链,
150-250k 段靠 peek barrier 每请求级捕获, 不靠 breaker 预跳). nv_breaker 由 `_ms_fallback_request`
调用路径内 R1648c 逻辑记录 (execute_request 出口那条; peek 走的是 handlers 层, 不走 execute_request
出口的 R1648c 块 — 但 breaker 累积仍由 peek 软挂+ms 失败路径触发 record_nv_failure? 见验证项).

## 验证

- [x] patch 脚本 syntax OK (python -m py_compile)
- [x] 容器内 syntax OK (docker exec python3 -m py_compile)
- [x] `docker compose restart nv_gw` (非 up -d) + health OK + StartedAt/RunningFor 变
- [x] E2E 非流式: cc4101→nv_gw 请求 200 完整 (collect path 不被 peek 干扰)
- [x] E2E 流式: cc4101→nv_gw stream 200 完整 (content_block_delta 全 + message_stop)
- [x] peek barrier 实际触发: 日志 `NV-PEEK-OK (glm5_2_nv) anth peek healthy first content
      after 5244ms, prebuffer=1037b` — 确认 peek 逻辑跑通, 健康 200 正常续流
- [ ] 24h 观测: 502 下降, NV-PEEK-MS-OK 上升 (软挂转 ms 成功), 无新 NameError/SyntaxError
- [ ] 真 200 无回归 (peek 不误杀, prebuffer 不丢内容, content 完整)

## 预期效果

- 流式软挂 17 次 (integrate no_content_gap×14 + total_deadline×3) + 非流式 6 次 = 23 次/6h
  被 barrier 拦截转 ms (假设 ms 成功率与现 12 次 fallback 一致).
- 6h 502: 43 → 约 6 (pexec 残留 + 真硬全挂 + ms 也失败).
- SR: ~83% → ~96%+. 每软挂省 128-494s 死循环, 换 ms 92s 正常完成.

## 风险

1. peek 不消费 resp 边界: prebuffer 预填解决. E2E 已验 prebuffer=1037b 正常 flush.
2. 误杀真慢首块: 复用 `_fb_s` 分档, p99=32s 留 40%+ 余量. E2E 5.2s 健康确认.
3. ms 也失败: 落 api_error SSE (CC 重试), 不比现状差.
4. converter 状态: 健康→复用 (content_chars 已累积); ms 分支→新建. 已处理.
5. 并发/重入: breaker 线程安全; collect 递归有 `_collect_ms_retried` 防死循环.

## 坑

- patch 脚本 f-string 嵌套引号: 用 python 字符串拼接 (`"\\n\\n"` 转义) 而非 heredoc, 避开
  R1715 的 f-string `{}` 内 `\"` 非法 SyntaxError. 多个 replace_once 用函数封装, 唯一性检查.
- `interrupted` 变量初始化顺序: peek barrier 的 prebuffer flush except 引用 `interrupted`,
  必须在 flush 前 `interrupted = False`. patch 脚本里 ANCHOR 含到 `return` 后的 `interrupted = False`,
  PEEK 末尾再补一次, 保证顺序.

## 落档

- 本轮文件: rounds/R1716_hm2_nv_gw_stream_soft_fail_ms_barrier.md
- 代码标记: R1716 (不撞号)
- 备份: handlers.py.bak.R1716_pre
- commit + push (mihomo 7894)
- 铁律: 只改 HM2 nv_gw. 不碰 HM1 (稳定后再部署). 不碰 cc4101/ms_gw.
