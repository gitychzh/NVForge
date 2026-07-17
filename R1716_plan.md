# R1716 计划: nv_gw 流式软全挂 → ms_gw 兜底 barrier (200 落客户端前 peek 首内容 chunk)

> 聚焦 HM2 远程 CC 链路 cc4101→40006(glm5.2_nv). 目标: 尽最大可能不让远程 CC 中断.
> HM1 暂缓 (用户要求 HM2 稳定 2-3 天后再部署).
> 铁律: 只改 HM2 nv_gw. 不碰 cc4101 (R1711 纯透传, 无需改). 不碰 ms_gw (R1648d 已支持).

## 背景: 现有两层 fallback 兜不住"软全挂"

两层 fallback 触发点都在 **"NVCF 返回 200 header 时"**:
- cc4101 `_try_primary` (upstream.py Stage 2): 只在 getresponse/header 阶段失败才返 False → 试 fallback.
- nv_gw R1648c (upstream.py execute_request 出口): 只在 all_keys_exhausted 才 `_ms_fallback_request`.

但 NVCF glm5.2 的主流失败是 **"200 后流到一半 hang"**, 该点在两层触发点之后 → 谁也接不住 →
cc4101 透传到一半收到 nv_gw 发的 api_error SSE → 502 给 CC → CC 死循环同请求.

## 数据锚点 (6h HM2, glm5_2_nv, mapped=nv_requests 表)

```
mode            | 200 | 502 | 软挂 error_type
integrate_us_rr |  70 |  19 | stream_no_content_gap×14, stream_total_deadline×3, zombie×2
pexec_us_rr     |  56 |   5 | zombie×2, NVAnth_NameError×1, first_byte_timeout×1
```

**软全挂几乎只发生在 integrate channel** (19/24=79%). 不是单 key/单 IP 问题 (7894/7896/7899
三个 egress, k0/k2/k4 三个 key 都中), 是 integrate channel 对 glm5.2 的系统性 mid-stream hang.

cc4101 侧 6h: primary 502×43 (avg 168s, max 494s) **无一触发 fallback** (fallback_triggered=f),
fallback 成功仅 12 次 (big_input breaker OPEN 触发). SR ~83%.

## 根因 (代码已精读确认)

`_handle_messages_anthropic` (handlers.py:847) 拿 execute_request 的 success result 后:
```
if is_stream:
    self._stream_openai_to_anth(resp, conn, ...)   # ← 内部 L940 先 send_response(200) 再读流
```
`_stream_openai_to_anth` (handlers.py:925) **循环前就 `send_response(200)+end_headers()`**:
200 已落 cc4101, 之后 mid-stream hang (no_content_gap/total_deadline/first_byte_timeout) 只能发
api_error SSE 关连接, **无法再切 ms** (200 status 已发不可逆).

非流式 collect 路径 (`_collect_stream_to_anth` L1124) 不先发 200, 最后才 `_send_json` →
**软挂天然可切 ms** (200 没发, 可转 fallback 重放).

## 方案: 流式路径加 "首内容 chunk peek barrier" (200 落客户端前)

核心: 在 `_stream_openai_to_anth` 里, **先 peek 首个含真实 content 的 SSE event, 确认健康后才
`send_response(200)`**; peek 超时/空内容 → 判软挂 → 关 nv conn → 调 `_ms_fallback_request`
重放原 oai_body 给 ms_gw → 把 ms 的流续给 cc4101 (cc4101 无感, 只看到一个正常 200+SSE).

### 为什么零新增函数 (框架简化点)

`_ms_fallback_request` (upstream.py:1340) 已具备一切:
- 深拷贝 oai_body 换 model=glm5_2_ms
- POST ms_gw `/v1/chat/completions` (NVU_MS_FALLBACK_URL)
- 返回 `r.resp` = ms_gw 的 **openai SSE** 流 (同 nv_gw 正常 resp 类型)
- handlers `_stream_openai_to_anth` 收 openai SSE 转 anth → **天然匹配** (R1648 下沉设计)

→ 无需新建 `_ms_fallback_stream`. 复用现有 `_ms_fallback_request` + 把它的 resp/conn 喂回
`_stream_openai_to_anth` 即可.

### 流式路径改造 (handlers.py `_stream_openai_to_anth`)

```
现: send_response(200)+end_headers() → while: read → parse → feed_chunk → write
改: [peek 阶段] while: read → parse → 判首内容非空?
        健康 → send_response(200)+end_headers() → flush 已 peek 的 anthropic bytes → 续读流
        软挂 (first_byte/no_content_gap/empty/zombie) → 关 nv conn → _ms_fallback_request →
                 若 ms 成功: send_response(200) → 用 ms 的 resp/conn 进正常续读流
                 若 ms 失败: send_response(200)+end_headers() + 发 api_error SSE (CC 重试)
                            [用户已确认: 保持现状语义, 200 已可发因这是 nv_gw→cc4101 边界,
                             cc4101 透传 api_error 给 CC, CC 识别为 api_error 自然重试]
```

peek 判定 "真实内容": 首个 SSE event 的 `choices[0].delta.content` 或 `reasoning_content` 非空.
纯 `[DONE]`/空 delta/只有 role 的头块不算 (那是 zombie/empty200 前兆).

### peek deadline (复用现有分档, 不误杀)

复用 `_stream_openai_to_anth` 已有 `_fb_s` 分档 (R1648e 数据锚点: 200-350k TTFB p99=32s):
- _ic<=50k: NVU_STREAM_FIRST_BYTE_DEADLINE_S
- _ic<=200k: NVU_STREAM_FB_50K_S=60
- _ic<=350k: NVU_STREAM_FB_200K_S=45
- _ic>350k:  NVU_STREAM_FB_350K_S=60

软挂 stream_no_content_gap avg 128s → peek 在 45-60s 内判软挂, 远早于现在 128s 才被 idle 砍.

### prebuffer 不丢 (http.client.HTTPResponse buffer 语义)

peek 阶段 `resp.read(8192)` 会消费 buffer. 解法: peek 读出的 raw bytes 存 `prebuffer` bytes,
确认健康后, `_stream_openai_to_anth` 把 prebuffer 预填进 sse_buffer (现 L870 `sse_buffer=""`
改为接受 prebuffer 参数). converter 也复用同一个 (peek 阶段已 feed 首 chunk, content_chars 已累积).

→ 复用 R1704 已有的 recv-fallback (sock.recv MSG_PEEK) 逻辑兜 http.client fp 崩坏.

### 非流式 collect 路径改造 (`_collect_stream_to_anth`)

collect 不先发 200, 软挂在最后 _send_json 前判定. 改: 检测到 content_filter/zombie/empty/
mid-stream OSError 后, 若 `mapped_model in NVU_MS_FALLBACK_MODELS` 且未发过任何响应 →
调 `_ms_fallback_request` 重放, 成功则用 ms 的 resp 重新 collect 一次, 失败才发 502.

(collect 路径软挂数据: zombie×4 + pexec zombie×2 = 6 次/6h, 量小于流式, 但顺手对称补)

### breaker 联动 (顺手修 R1715 记的 150-250k 段漏记)

peek 软挂 → `big_input_breaker.record_big_input_failure(err)` + `nv_breaker.record_nv_failure()`:
- big_input_breaker: 累积 OPEN, 后续同类请求直走 ms (省 peek 时间). 阈值 250k 不动, 靠 record
  逻辑覆盖 (peek 软挂在 200 前, 不论 input 大小都记 → 150-250k 段不再漏).
- nv_breaker: 累积 OPEN (N=15), 后续请求跳过 nv 链直走 ms.

### 触发条件 (避免误触发)

只对 `mapped_model in NVU_MS_FALLBACK_MODELS` (glm5_2_nv) 开. 其他模型无 ms 后端, peek 软挂走
原 502 api_error 路径 (保持现状). 受 NVU_MS_FALLBACK_ENABLED=1 联动 (已开).

## 预期效果 (数据测算)

- 流式软挂 17 次 (integrate no_content_gap×14 + total_deadline×3) + 非流式 6 次 = 23 次/6h
  被 barrier 拦截转 ms (假设 ms 成功率与现 12 次 fallback 一致).
- 6h 502: 43 → 约 6 (pexec 残留 zombie/NameError + 真硬全挂 + ms 也失败).
- SR: ~83% → ~96%+. 每软挂省 128-494s 死循环, 换 ms 92s 正常完成.

## 改动文件 (只 nv_gw, bind-mount restart)

1. `/opt/cc-infra/proxy/nv-gw/gateway/handlers.py`
   - `_stream_openai_to_anth`: 加 peek barrier 阶段 (200 前), prebuffer 参数, 软挂→ms_fallback 切换
   - `_collect_stream_to_anth`: 软挂→ms_fallback 切换 (200 未发, 直接重放)
   - `_handle_messages_anthropic`: 传 oai_body 给两函数 (现签名无, 需补参数供 fallback 重放用)
2. `/opt/cc-infra/proxy/nv-gw/gateway/upstream.py`
   - `_ms_fallback_request`: 现有已足够, 可能需导出 oai_body 给 handlers (或 handlers 从 metrics 取)

不碰: cc4101/, ms-gw/, config.py (env 不变), circuit.py.

## 风险点 + 验证

1. **peek 不消费 resp 的边界**: http.client HTTPResponse.read 会前进 buffer. 用 prebuffer 预填
   sse_buffer 解决. 单测: 构造 hang resp (不发内容) + 正常 resp, 验证 peek 判定 + prebuffer 续流完整.
2. **误杀真慢首块**: 复用现有 `_fb_s` 分档 (45-60s), 数据锚点 p99=32s 留 40%+ 余量. 低风险.
3. **ms 也失败**: 落回原 502 api_error 路径 (send 200 + api_error SSE, CC 重试). 不比现状差.
4. **converter 状态复用**: peek 阶段已 feed 首 chunk 的 converter 续用, content_chars 不丢.
   若走 ms 分支则新建 converter (ms 是 fresh 流).
5. **并发/重入**: breaker 已线程安全. peek 在单请求单线程内, 无并发问题.

验证清单:
- [ ] syntax check (python -m py_compile)
- [ ] docker compose restart nv_gw (非 up -d) + health OK + StartedAt 变
- [ ] E2E: 构造大请求触发 integrate 软挂, 观察 NV-MS-FB-PEEK-* 日志 + cc4101 收到 200 完整流
- [ ] 24h 观测: 502 下降, fallback_triggered 上升, 无新 NameError/SyntaxError
- [ ] 真 200 请求无回归 (peek 不误杀, prebuffer 不丢内容)

## 落档

- 轮文件: rounds/R1716_hm2_nv_gw_stream_soft_fail_ms_barrier.md
- 代码标记: R1716 (不撞号, R1715 是 NameError 修复)
- commit + push (mihomo 7894)
- 铁律: 只改 HM2 nv_gw. 不碰 HM1 (稳定后再部署). 不碰 cc4101/ms_gw.
