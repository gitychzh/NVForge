# R2305 (HM2): opclaw4103 FALLBACK_HEADER_TIMEOUT 30→180 + CC4101_TOTAL_BUDGET 80→400 — 修 openclaw "primary 和 fallback 均不可用"

> 时间: 2026-07-24 01:23 CST. HM2 only. 链路: openclaw → opclaw4103(4103) → 40006(primary) + 40007(fallback).
> 紧接 R2303(同症状从 primary 侧治, PRIMARY_HEADER_TIMEOUT 25→180). 本轮从 fallback 侧补刀.

## 数据(改前基线, 2026-07-24 00:25-00:49 CST)

### opclaw4103 日志 60min
- 11 REQ; 1× `CONTENT_FILTER_ZOMBIE`(nv_gw content_filter zombie) → 1× `PRIMARY-ZOMBIE-FALLBACK` →
  2× `PRIMARY-BREAKER-SKIP-STREAM`(circuit OPEN 直走 fallback) → 2× `FALLBACK-STREAM` →
  **1× `FALLBACK-FAIL-STREAM`: `ms_gw 流式 timeout status=0 after 30035ms: header/ttfb timeout after 30.0s: timed out`**
  → 触发 "primary 和 fallback 均不可用".
- 改前 curl 基线: non-stream 200(走 fallback, content 空+reasoning 有); stream 返回空(SSE 被 head 截断).

### nv_gw 30min DB
- 200×74 / 502×11, SR≈87%. content_filter zombie 是 nv_gw 检测 NVCF 空/过滤响应(R840), 非网关 bug.

### ms_gw 日志 30min
- 大量 `MS-RL-BACKOFF http_429_rate_limit`(modelscope GLM-5.2 限流)、`MS-FASTBREAK consecutive_empty=3`、
  `MS-VARIANT-EXHAUSTED` variant 8/9/0/1 全 keys failed、`MS-TOTAL-CYCLE-CAP aborting attempts=12`、
  `MS-ALL-EXHAUSTED-COOL`; 也有成功 `MS-OK-STREAM`(但慢, ~13-30s 找 warm key).

### openclaw 进程
- PID 1097926 在跑, gateway 18789 `{"ok":true,"status":"live"}`, 飞书 bot 在用.

## 根因

1. **primary(nv_gw)偶发 content_filter zombie**(R840 检测) → 切 fallback; 连续几次后 primary circuit OPEN
   (CIRCUIT_FAILURE_THRESHOLD=5), 期间所有请求直走 fallback.
2. **fallback(ms_gw)的 `FALLBACK_HEADER_TIMEOUT=30s` 太短**: opclaw4103 env 未设此值, 用 config.py 默认 30s
   (注释原意"容纳 ~18s 找 warm key"). ms_gw 在 modelspace 429 风暴 + all-exhausted cooldown 期, RR 找 warm
   key 可达 30s+, 30s 到期 → fallback timeout → 双挂 → "均不可用".
   - 源码核证: `forwarder.py:206` 注释 `header/TTFB: header_timeout (PRIMARY_HEADER_TIMEOUT=25 / FALLBACK_HEADER_TIMEOUT=30)`;
     `forwarder.py:230` `sock.settimeout(header_timeout)`; `forwarder.py:247` `header/ttfb timeout after {header_timeout}s`;
     `forwarder.py:372/599` fallback 用 `FALLBACK_HEADER_TIMEOUT`; "primary 和 fallback 均不可用" 在 `forwarder.py:407/410`.
3. **加重因素**: non-stream 路径 fallback 失败后有 retry-primary 门控
   (`forwarder.py:390`: `remaining = CC4101_TOTAL_BUDGET_S - elapsed >= PRIMARY_HEADER_TIMEOUT`),
   默认 `CC4101_TOTAL_BUDGET_S=80` < `PRIMARY_HEADER_TIMEOUT=180` → 门控永不满足 → retry 被禁, fallback 失败直接 503.
   stream 路径无 retry(流已发 message_start 不能回头).

→ **直接根因 = opclaw4103 未设 `FALLBACK_HEADER_TIMEOUT`, 默认 30s 不足以覆盖 ms_gw 429 退避期 TTFB.**

## 拟改(聚焦 opclaw4103 compose env, 不碰 nv_gw/ms_gw 源码, 符合铁律)

### 改动 1(治本): opclaw4103 compose env 加 `FALLBACK_HEADER_TIMEOUT=180`
- 文件: `/opt/cc-infra/docker-compose.yml` service `opclaw4103` environment 块, L291 `PRIMARY_HEADER_TIMEOUT=180` 后新增.
- 180s 对齐 primary. ms_gw 自身有 MS-TOTAL-CYCLE-CAP 不会让 fallback 干等满 180s(真 all-exhausted 时较快返回错误).

### 改动 2(治标, 建议): `CC4101_TOTAL_BUDGET_S` 80→400
- 同块新增. 让 non-stream 路径 fallback 失败后能 retry primary 一次. stream 路径无 retry 不受影响, 靠改动 1 兜.

### 不改(明确)
- nv_gw 源码/content_filter zombie(上游 NVCF, 非本次范围; nv_gw 优化是 cc2/openclaw2 独立轮次).
- ms_gw 源码/compose(铁律3 热备不碰; ms_gw 429 是 modelspace 限流, 网关侧无法解决).
- openclaw.json primary 模型名 kimi_nv(被 opclaw4103 重写为 PRIMARY_MODEL=glm5_2_nv, 已验证能跑; 改它引入新变量无收益).
- cc-adapter 源码 forwarder.py/config.py(只改 compose env, 最小改动面).

## 执行

1. `cp docker-compose.yml docker-compose.yml.bak.R2304fb`(已备份).
2. Edit L291 后插入两行(见上).
3. `cd /opt/cc-infra && docker compose up -d opclaw4103`(改 env 必须 up -d 重建容器, 不是 restart — env 是容器创建期注入).
   - 重启窗口 ~5s, openclaw 新请求短暂失败(无备用 forwarder), 飞书消息重试兜住. 重启前 docker logs tail 3 确认无活跃流.
4. 验证(见下).

## 验证结果(改后, 01:23-01:30 CST)

### env 落地
```
CC4101_TOTAL_BUDGET_S=400
FALLBACK_HEADER_TIMEOUT=180
PRIMARY_HEADER_TIMEOUT=180
```
✓ 三值均落地. health ok. 容器 Up.

### opclaw4103 日志改后 8min(铁证)
- **FALLBACK-FAIL / "均不可用" / all_backends_down 计数 = 0**(改前 00:26 有 1 次双挂).
- 重启后首个真实请求即触发同样场景: 01:25:35 `CONTENT_FILTER_ZOMBIE` → 01:26:09 `FALLBACK-STREAM`(成功接住).
  改前同样场景 00:26:04 会 30s timeout 双挂, 改后 fallback 稳稳接住.
- tag 统计: 4 REQ + 3 curl 测试 = 7 请求全成功经 fallback; 0 失败.

### 端到端 curl(用户核心要求"真实可用")
- non-stream: `curl -m 90 ... stream=false` → **200 OK**, `model=glm5_2_ms`, content 有 fallback 提醒前缀, reasoning_content 有内容.
  对应日志 `01:27:09 FALLBACK` 成功(改前同场景会 503 均不可用).
- stream: `curl -sN -m 90 ... stream=true` → **SSE 流正常**, 多个 `data: {...}` chunk, `model=ZhipuAI/GLM-5.2`,
  reasoning_content 持续生成, `01:27:28 FALLBACK-STREAM` 成功 + `SUPPLEMENT-CONTENT` 流末补 content.
  (末尾 STREAM-CLIENT-ERR 是 curl head -15 截断致客户端断开, 非链路问题.)

### nv_gw primary 10min
- 200×35 / 502×3, SR 92%. primary 也在恢复中(content_filter zombie 是间歇上游波).

## 结论

- **"primary 和 fallback 均不可用" 根因 = opclaw4103 FALLBACK_HEADER_TIMEOUT 默认 30s 不足以覆盖 ms_gw 429 退避期 TTFB**.
  本轮 30→180 + budget 80→400, fallback 不再 30s timeout, 双挂消除.
- 链路 openclaw → opclaw4103(4103) → 40006(primary) + 40007(fallback) 端到端真实可用(非流+流式 curl 均验证).
- 铁律遵守: 只改 opclaw4103 compose env, 未碰 nv_gw/ms_gw 源码, 未碰 openclaw.json, 未碰 cc-adapter 源码.
- 改 env 用 `up -d`(非 restart), 已验证新 env 落地.

## 风险/后续

- 改动 2 会拉长 non-stream 失败请求总耗时(fallback 180s + retry primary 180s 最坏 ~360s 才 503). 但 non-stream 请求少
  (openclaw 真实请求多为 stream), 且能救回部分请求. 若负面可单独删 `CC4101_TOTAL_BUDGET_S` 行回滚.
- primary circuit 当前 OPEN 是上游 NVCF content_filter zombie 间歇波导致, 非 opclaw4103 问题; breaker 60s 后自动 HALF_OPEN 探活恢复.
- 后续观测点: opclaw4103 日志 `FALLBACK-FAIL` 应持续为 0; 若再现说明 ms_gw 429 风暴加剧到 180s 也兜不住(则需 nv_gw 侧治 zombie 源头, 归 cc2/openclaw2 轮次).

## 回滚
```
cp docker-compose.yml.bak.R2304fb docker-compose.yml && cd /opt/cc-infra && docker compose up -d opclaw4103
```
