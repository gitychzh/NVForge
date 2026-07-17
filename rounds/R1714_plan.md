# R1714 计划: 修 R1704 引入的 request_id NameError + 扩 big_input 阈值覆盖 150-250k 段

> 聚焦 HM2 cc4101→40006(glm5.2_nv) 链路. HM1 暂缓(用户要求稳定2-3天后再部署).

## 框架审视结论 (妥当性)

R1711 透传化 + R1713 删死代码后的 **cc4101→nv_gw /v1/messages 链路架构是妥当的**:
- cc4101 纯透传(只改写 model 做路由 + 透传 SSE/JSON + 连接级 breaker), 不持有转换/诊断逻辑
- 诊断责任单一在 nv_gw (R1704 补齐 recv-fallback + content_filter polarity)
- breaker 纯连接级, header 失败切 ms_gw (9 个 fallback 全 200), 流中途 zombie 透传 api_error 给 CC 重试
- 无死循环回归 (R1672 场景验证)

**但发现一个真 bug + 一个设计阈值错配**:

## Bug: R1704 引入的 request_id NameError (框架级崩溃, 必修)

### 根因
R1704 给 nv_gw `_stream_openai_to_anth` / `_collect_stream_to_anth` 补 content_filter polarity + big_input
record 时, 在 4 处 `_log` 的 f-string 里写了 `req={request_id}`. 但这两个函数签名是
`(self, resp, conn, metrics, t_start, request_model)` — **没有 request_id 参数**, 函数作用域里
request_id 未定义. 抄 cc4101 stream.py 的写法, 但 cc4101 的 stream_to_anth 签名里有 request_id,
nv_gw 这里没有 — **抄对了逻辑抄错了变量作用域**.

### 4 处位置 (ast 精确定位)
| 行 | 函数 | 触发分支 | 影响 |
|---|---|---|---|
| L1045 | _stream_openai_to_anth | content_filter + content==0 | nv_gw 主动 break 时 NameError |
| L1049 | _stream_openai_to_anth | content_filter + content>0 | mid-flight zombie 时 NameError |
| L1068 | _stream_openai_to_anth | zombie_empty_completion + big_input | >250k zombie 时 NameError (已实发 1 次) |
| L1237 | _collect_stream_to_anth | zombie_empty_completion + big_input | >250k 非流式 zombie 时 NameError |

(L483 在 _handle_openai_nv 内, 该方法 L236 定义了 request_id, **不是 bug** — agents 路径 OK)

### 实发影响 (6h, nv_gw 侧 cc4101-primary)
- 1 次 NVAnth_NameError (260k input, 8.2s) — L1068 触发, >250k zombie 走 big_input 分支
- 触发条件: input>250k 且走 zombie/content_filter 的 big_input record 分支
- NameError 从 _stream_openai_to_anth 冒泡 (调用点 L836 无 try/except) → socketserver 兜住 →
  强制关连接 → cc4101 收半截响应 → 记 502
- **L1066/L1234 的 record_big_input_failure 在 NameError 前已执行** (breaker 该记的记了),
  但 L1665 的 R1675 兜底 record 块被异常绕过 (在 _stream 函数外, 异常先冒泡了)

### 修法 (明确)
4 处 `req={request_id}` → `req={metrics.get('request_id','?')}` (对齐 L1671 已有的正确写法).
- L1045: `f"(req={request_id})")` → `f"(req={metrics.get('request_id','?')})")`
- L1049: 同上
- L1068: `f"input={_bi_input}c (req={request_id}), "` → `f"input={_bi_input}c (req={metrics.get('request_id','?')}), "`
- L1237: 同 L1068 模式

纯日志行改动, 不碰逻辑, 不碰 breaker record 顺序. bind-mount restart 即生效.

## 设计漏洞: big_input_breaker 阈值错配 (框架级, 影响大)

### 数据 (6h, nv_gw 侧 cc4101-primary)
真实 502 来源 (nv_gw 判的, 非 cc4101 重判):
| error_type | count | avg_ms | avg_input | max_input |
|---|---|---|---|---|
| stream_no_content_gap | **12** | 117s | 192k | 246k |
| stream_first_byte_timeout | 1 | 136s | 157k | 157k |
| NVAnth_NameError | 1 | 8.2s | 260k | 260k |

- **12 个 no_content_gap 全在 150-250k 段** (avg 192k, max 246k), **没有一个 >250k**
- big_input_breaker 阈值 NVU_BIG_INPUT_THRESHOLD=250000 → `is_big_input(192k)`=False →
  **12 个最大的 hang 失败全部不记 breaker** → breaker 永不到 OPEN → 永不触发 ms 直走
- R1673 设计针对 ">250k 系统性 hang", 但实际数据表明 **150-250k 段才是 no_content_gap 主战场**
- L1665 的 R1675 兜底块虽覆盖所有 error_type, 但 `is_big_input(_bi_input)` 仍要求 >250k — 同样漏

### 这是 R1673 阈值设定的历史误判
R1673 时 283k 是死循环主角 (记忆 r1672), 阈值卡 250k 合理. 但改后 NVCF 行为变了, no_content_gap
下移到 150-250k 段. 阈值没跟着调.

### 修法 (需用户决策, 见下)
**选项 A (保守)**: 降 NVU_BIG_INPUT_THRESHOLD 250k → 150k. 覆盖 150-250k 段的 no_content_gap.
  - 风险: 150-250k 段有 16 个成功请求 (200-250k: 16×200 + 5×502), 降阈值后这些成功请求里
    偶发失败会更快累积到 OPEN, 可能把正常大请求也导去 ms_gw (ms 每天限额, 浪费额度)
  - 但 FAIL_N=1 (R1674 改) 过于激进, 配 150k 阈值会频繁误开. 需同时把 FAIL_N 调回 3 (R1673 原值)

**选项 B (精准)**: 不降阈值, 改 record 逻辑 — no_content_gap / first_byte_timeout 这两类 hang
  **无论 input 大小都记 breaker** (它们本就是 NVCF 系统性坏信号, 不只限于大 input).
  - 加一个新 breaker 或扩 big_input_breaker 的 record 条件: `is_big_input(_bi_input) OR error_type in (no_content_gap, first_byte_timeout)`
  - 但这会把 50-200k 段的 8 个 no_content_gap 也计入 (它们 avg 107s, 也是 hang), 可能过度

**选项 C (推荐, 分两步)**: 本轮只修 NameError bug (选项明确的 4 行), big_input 阈值错配**先观测
  一轮再定** — 因为 6h 才 14 个 502, 样本小, 降阈值/改 record 的影响面需更多数据. 本轮修完 NameError
  后观测 24h, 再根据 no_content_gap 的真实分布决定阈值.

## 历史问题 (已修, 不用管)
- nv_breaker NameError (R1695 误删 import 引入): 重启后 0 次, 是 R1695 修复前残留日志

## 本轮改动 (只做选项 C 的 NameError 修复)

### 改动文件
`/opt/cc-infra/proxy/nv-gw/gateway/handlers.py` (HM2 nv_gw, bind-mount)

### 改动内容 (4 处, 纯日志行)
- L1045: `req={request_id}` → `req={metrics.get('request_id','?')}`
- L1049: 同上
- L1068: `req={request_id}` → `req={metrics.get('request_id','?')}`
- L1237: `req={request_id}` → `req={metrics.get('request_id','?')}`

不碰其他逻辑, 不碰 breaker record 顺序, 不碰阈值.

### 验证
1. ast 语法 + 容器内 import OK
2. bind-mount restart nv_gw
3. 触发一次 >250k zombie 请求 (或等真实流量), 确认:
   - 不再出 NVAnth_NameError
   - NV-BIGINPUT-FAIL 日志正常打印 (含 req=... 和 breaker 状态)
4. big_input_breaker 真实状态: 从日志看 (docker exec 是新进程, 看不到 live 状态, 坑同 R1648c)
5. 6h 后看 SR + no_content_gap 分布, 为阈值决策积累数据

### 不做
- 不降 big_input 阈值 (留观测轮)
- 不改 record 逻辑 (留观测轮)
- 不碰 HM1 (用户要求稳定后再部署)
- 不碰 cc4101 (架构妥当, 无 bug)
