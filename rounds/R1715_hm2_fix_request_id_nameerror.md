# R1715: 修 R1704 引入的 request_id NameError (nv_gw _stream_openai_to_anth / _collect_stream_to_anth)

> 聚焦 HM2 cc4101→40006(glm5.2_nv) 链路. HM1 暂缓(稳定2-3天后再部署).

## 框架审视结论 (妥当性)

R1711 透传化 + R1713 删死代码后的 cc4101→nv_gw /v1/messages 链路**架构妥当**:
- cc4101 纯透传(只改 model 做路由 + 透传 SSE/JSON + 连接级 breaker), 不持转换/诊断逻辑
- 诊断责任单一在 nv_gw (R1704 补齐 recv-fallback + content_filter polarity)
- breaker 纯连接级, header 失败切 ms_gw (9 个 fallback 全 200), 流中途 zombie 透传 api_error 给 CC 重试
- 无死循环回归 (R1672 场景验证)

但框架审视发现一个 R1704 引入的真 bug + 一个 R1673 阈值错配(本轮只修 bug, 阈值留观测).

## Bug: R1704 引入的 request_id NameError (框架级崩溃)

### 根因
R1704 给 nv_gw `_stream_openai_to_anth` / `_collect_stream_to_anth` 补 content_filter polarity +
big_input record 时, 在 4 处 `_log` f-string 里写了 `req={request_id}`. 但这两个函数签名是
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

(L483 在 _handle_openai_nv 方法内, 该方法 L236 定义了 request_id, **不是 bug** — agents 路径 OK)

### 实发影响 (6h, nv_gw 侧 cc4101-primary)
- 1 次 NVAnth_NameError (260k input, 8.2s) — L1068 触发, >250k zombie 走 big_input record 分支
- NameError 从 _stream_openai_to_anth 冒泡 (调用点 L836 无 try/except) → socketserver 兜住 →
  强制关连接 → cc4101 收半截响应 → 记 502
- L1066/L1234 的 record_big_input_failure 在 NameError 前已执行(breaker 该记的记了),
  但 L1665 的 R1675 兜底 record 块被异常绕过(在 _stream 函数外, 异常先冒泡)

## 历史问题 (已修, 不用管)
- nv_breaker NameError (R1695 误删 import 引入): 重启后 0 次, 是 R1695 修复前残留日志

## 设计漏洞: big_input_breaker 阈值错配 (本轮只观测, 不改)

### 数据 (6h, nv_gw 侧 cc4101-primary)
真实 502 来源:
| error_type | count | avg_ms | avg_input | max_input |
|---|---|---|---|---|
| stream_no_content_gap | 12 | 117s | 192k | 246k |
| stream_first_byte_timeout | 1 | 136s | 157k | 157k |
| NVAnth_NameError | 1 | 8.2s | 260k | 260k |

12 个 no_content_gap 全在 150-250k 段(max 246k < 250k 阈值), big_input_breaker
(NVU_BIG_INPUT_THRESHOLD=250000) 全部漏记 → 永不到 OPEN. R1673 设 250k 阈值是针对
当时 283k 死循环, 现 NVCF 行为下移到 150-250k 段, 阈值没跟着调.

**本轮只修 NameError, 阈值错配留观测轮** — 6h 才 14 个 502, 样本小, 降阈值/改 record
的影响面需更多数据. 本轮修完 NameError 后观测 24h, 再根据 no_content_gap 真实分布决定.

## 改动 (HM2 nv_gw, /opt/cc-infra/proxy/nv-gw/gateway/handlers.py, bind-mount)

4 处纯日志行:
- L1045: `req={request_id}` → `req={metrics.get('request_id','?')}`
- L1049: 同上
- L1068: `req={request_id}` → `req={metrics.get('request_id','?')}`
- L1237: 同上

对齐 L1671 已有的正确写法. 不碰逻辑, 不碰 breaker record 顺序, 不碰阈值.
备份: handlers.py.bak.R1715_post (修后版本; .bak.R1715_pre 坏版本已删).

## 改后验证
1. ast 语法 OK (容器内 import ast.parse 通过)
2. bind-mount restart nv_gw, health OK
3. E2E 小请求流式: anthropic SSE 正常 (message_start/content_block_delta "Hi")
4. E2E 非流式: anthropic JSON 正常 (model=glm5_2_nv)
5. 重启后无 NameError (docker logs grep nameerror 空)
6. 真实 CC 请求继续走 passthrough (cc4101 侧无变化)

## 坑 (本轮踩)
- heredoc 里给 f-string 嵌套引号, 用 `\"` 转义在 f-string `{}` 表达式内非法
  (SyntaxError: unexpected character after line continuation character).
  → 必须用单引号 `metrics.get('request_id','?')`, 不用 `\"`.
- 备份时机: cp 备份前要先确认源文件是好的, 否则备份存坏版本(本轮 .bak.R1715_pre 存了
  带转义错的版本, 已删换 .bak.R1715_post).

## 不做
- 不降 big_input 阈值 (留观测轮)
- 不改 record 逻辑 (留观测轮)
- 不碰 HM1 (用户要求稳定后再部署)
- 不碰 cc4101 (架构妥当, 无 bug)

## 验证清单
- [x] ast 语法 OK
- [x] 4 处 request_id → metrics.get('request_id','?')
- [x] _stream_openai_to_anth / _collect_stream_to_anth 内无残留裸 request_id
- [x] nv_gw restart + health OK
- [x] E2E 流/非流正常
- [x] 重启后无 NameError
- [ ] 24h 后看 SR + no_content_gap 分布 (为阈值决策积累数据, 下轮)

## 下一步 (观测轮, 不改代码)
观测 24h: >250k 请求的 NameError 是否归零, no_content_gap 在 150-250k 段的真实分布.
若 no_content_gap 持续集中在 150-250k, 下轮考虑降阈值(250k→150k)或改 record 逻辑.
