# R1648: HM2 gateway 架构重构框架（最终定稿）

> 状态: **框架定稿，待分轮实施**。本文是设计文档，审阅通过后按 R1648a~f 分轮落地。
> 范围: 只改 HM2。HM1 保持现状。破铁律"只改HM1"，本轮显式豁免。
> 定稿日期: 2026-07-17。

## 一、用户需求（已澄清定稿）

1. cc4101 不退役——Claude Code 本身无 fallback，但 cc4101 **退化为纯透传层**（抉择 B）：
   只做鉴权 + 透传 anthropic body 到 40006 的 `/v1/messages`，**格式转换全在 40006**。
2. 40006(nv_gw) 双格式：openai(`/v1/chat/completions`，给 agent) + anthropic(`/v1/messages`，新增)。
3. 40007(ms_gw) 同样双格式。
4. fallback 下沉到 40006：glm5.2_nv 5key 全坏 → nv_gw 自己 fallback 40007(glm5.2_ms)。
5. "cc 自己优化自己" = fallback 保命，不加自动调参闭环。

## 二、四个设计抉择（已定）

| 抉择点 | 选择 | 说明 |
|---|---|---|
| cc4101 定位 | **B: 纯透传** | cc4101 只鉴权+透传 anthropic body 到 40006 `/v1/messages`；转换全在 40006 |
| fallback 触发 | **两者结合** | (a) 5key×mode 全坏(all_tiers_exhausted)才切 ms；(b) nv_gw 侧 breaker(阈值15)OPEN 期间直走 ms |
| format 共享 | **各复制一份** | converters + stream 反向转换代码复制到 nv-gw / ms-gw / cc4101 各自 gateway 下，先求简单不共享 |
| 落地节奏 | **分6轮** | a→b→c→d→e→f，每轮验证+commit+观察，符合铁律 |

## 三、目标架构

```
远程 CC (anthropic /v1/messages)
   │  ANTHROPIC_BASE_URL=127.0.0.1:4101
   ▼
cc4101 (4101) — 纯透传层 [抉择B]
   │  - 鉴权 (x-api-key/Bearer, CC4101_GATEWAY_API_KEY)
   │  - 透传 anthropic body 到 40006 /v1/messages (不改 body)
   │  - 透传 40006 回的 anthropic SSE 给 CC
   │  - 删: converters / stream 转换 / breaker / fallback (全下沉 40006)
   ▼
40006 nv_gw — 双格式 + nv→ms fallback  [重构核心]
   ├─ /v1/chat/completions (openai, 给 agent — 现有不动)
   ├─ /v1/messages (anthropic, 给 cc4101/CC — 新增)
   │     → anth_to_oai 转 openai → NVCF 5key 链 → oai_to_anth 转回 → anthropic SSE
   ├─ NVCF 5key pexec↔integrate mode chain (现有)
   ├─ nv breaker (阈值15) OPEN → 直走 ms  [新增]
   └─ 5key×mode 全坏 → fallback 40007 glm5_2_ms  [新增, 复用 peer-fallback 模式]
         │  (ms_gw 吃 openai, nv_gw 内部用 anth_to_oai 转好的 openai body 发)
         ▼
40007 ms_gw — 双格式  [重构]
   ├─ /v1/chat/completions (openai, 现有)
   ├─ /v1/messages (anthropic — 新增, 同样转换)
   └─ ModelScope 7key×10variant (现有, 兜底层无 fallback)
```

### 数据流（CC 一次请求）

```
CC → cc4101: anthropic /v1/messages (原样 body)
cc4101 → nv_gw: POST /v1/messages (透传, 加 Bearer nv-gw-token)
nv_gw /v1/messages handler:
  1. 鉴权
  2. anth_to_oai(body, "glm5_2_nv") → openai body
  3. execute_request(openai body) → 走现有 5key NVCF 链
     - 5key 全坏 或 nv breaker OPEN:
       → fallback: POST 40007 /v1/chat/completions (openai body, model=glm5_2_ms)
       → ms_gw 返回 openai SSE
  4. oai_to_anth(openai SSE) → anthropic SSE
nv_gw → cc4101: anthropic SSE
cc4101 → CC: 透传 anthropic SSE
```

关键：cc4101 全程不碰格式（纯透传），转换+fallback 全在 nv_gw。nv→ms 的 fallback 在 nv_gw 内部完成，
对 cc4101/CC 透明（CC 只看到 anthropic SSE，不知道走了 nv 还是 ms）。

## 四、现状关键事实（已核实）

- nv_gw/ms_gw 当前**只认 openai**，无 anthropic 端点。ms_gw 注释明确 "no Anthropic conversion"。
- nv_gw 已有**跨机 peer-fallback**机制（`NVU_PEER_FALLBACK_URL`/`NVU_PEER_FALLBACK_ENABLED`，对端 nv_gw，
  默认关）——模式可复用做 nv→ms fallback。
- nv_gw `execute_request` (upstream.py:1328) 是 NVCF 总入口，5key×mode 全坏返 `all_keys_exhausted`
  ——**fallback 插入点确认可行**（tier 全挂后、return 失败前）。
- nv_gw R753 删了跨 model fallback，注释原话"跨后端同模型 fallback 已由 41xx 适配器做"——本框架把
  这份责任从 cc4101 **下沉回 nv_gw**。
- cc4101 `converters.py` 纯函数（`anth_to_openai` 核心），**无反向** `openai_to_anth`——反向转换散在
  `stream.py`（`stream_to_anth` chunk级 + `collect_stream_to_anth` 整体）。
- 所有容器在 `cc-net` 网络，互用容器名访问。cc4101/nv_gw/ms_gw 均 bind-mount `gateway/`，改 .py 只需
  `docker compose up -d`，无需 build。

## 五、分轮落地计划（6轮）

每轮：备份 .py.bak.R1648x → 改 → 语法检查 → `docker compose up -d` → 验证 → commit + push + memory。

### R1648a: 抽共享 format 包，cc4101 先改用它（行为不变，纯重构）

- 把 cc4101 `converters.py` 改名为 `format/anth_to_oai.py`（或新建子目录复制）。
- 把 cc4101 `stream.py` 的反向转换部分（chunk级+collect级）抽成 `format/oai_to_anth.py` + `format/sse.py`。
- cc4101 import 改指向新位置。
- **行为不变**，纯代码组织，可安全验证（CC 请求 200 不变）。
- 目的：为 R1648b 把 format 代码复制进 nv_gw 做准备——先在 cc4101 里把边界理清。

### R1648b: nv_gw 加 /v1/messages anthropic 端点（只转换，无 fallback）

- `nv-gw/gateway/handlers.py` ProxyHandler:
  - do_GET/HEAD 路由加 `/v1/messages`、anthropic `/v1/models`
  - do_POST 加 `if path=="/v1/messages": self._handle_messages_anthropic()`
- 复制 cc4101 的 `format/` 包到 `nv-gw/gateway/format/`
- `_handle_messages_anthropic()`:
  1. 鉴权（复用 NVU_GATEWAY_API_KEY）
  2. `anth_to_oai(body, "glm5_2_nv")` → openai body
  3. 调现有 `execute_request(handler, openai body, "glm5_2_nv", ...)`
  4. 响应：openai SSE → `oai_to_anth` → anthropic SSE 回客户端
- **不含 fallback**，纯端点新增。验证：`curl /v1/messages` 返回 anthropic 200。
- 不影响现有 openai 路径（路由 if/elif 隔离）。

### R1648c: nv_gw 加 5key全坏→ms_gw fallback（glm5_2_nv 专）

- `nv-gw/gateway/config.py` 加：
  - `NVU_MS_FALLBACK_URL`（默认 `http://ms_gw:40007/v1/chat/completions`）
  - `NVU_MS_FALLBACK_ENABLED`（默认 1）
  - `NVU_MS_FALLBACK_FAIL_THRESHOLD=15`（nv breaker 阈值）
  - `NVU_MS_FALLBACK_SKIP_S=30`（OPEN 冷却）
- `nv-gw/gateway/upstream.py` `execute_request`:
  - tier 全挂(`all_keys_exhausted`)后：若 glm5_2_nv + MS_FALLBACK enabled → POST ms_gw
    （用已转好的 openai body，model 字段换 glm5_2_ms）
  - 加 nv breaker（复用 cc4101 circuit.py 模式）：连续 15 次全挂 → OPEN → 直走 ms，冷却 30s HALF_OPEN probe
- **只 glm5_2_nv**：dsv4p_nv/kimi_nv 不 fallback ms（模型不对应）。
- 验证：临时让 5key 全挂（把 NV key 全设坏值），确认切 ms 200。

### R1648d: ms_gw 加 /v1/messages anthropic 端点

- 复制 cc4101 `format/` 到 `ms-gw/gateway/format/`
- `ms-gw/gateway/handlers.py` 加 `/v1/messages` 端点，同 R1648b 结构
- ms_gw 无 fallback（兜底层）。验证：curl 测。

### R1648e: cc4101 瘦身为纯透传（抉择 B）

- `cc4101/gateway/handlers.py` `_handle_messages`:
  - 删 `anth_to_openai` 调用、删 `execute_request` 调用
  - 改为：鉴权 → 透传原 anthropic body 到 `nv_gw:40006/v1/messages` → 透传回 SSE
- `cc4101/gateway/upstream.py` / `circuit.py` / `stream.py` / `converters.py`：删（或归档 bak-archive/）
- `cc4101/gateway/config.py`：删 PRIMARY/FALLBACK_UPSTREAM_*，加 `CC4101_TARGET_URL=http://nv_gw:40006/v1/messages`
- `docker-compose.yml` cc4101 段：删 fallback env（R1643 加的），改 PRIMARY URL 指 /v1/messages
- 验证：远程 CC 请求 200，DB fallback_triggered 仍记（现在由 nv_gw 记，nv_requests 表）。

### R1648f: 切换 + 长跑观察

- 确认 compose + agent 配置全就位
- 远程 CC 长跑 ≥6h 观察：nv_requests fallback_occurred、CC 是否不中断、ms_gw 配额消耗
- 更新 memory（cc4101 定位变更、fallback 下沉、两边源码分歧）
- HM1 暂不同步（留后续轮）

## 六、fallback 触发逻辑（两者结合，最终）

```
nv_gw execute_request(glm5_2_nv):
  if nv_breaker OPEN:          # 连续15次全挂
     → 直走 ms_gw (省每条等 nv 跑满 chain ~120s)
     → 冷却 30s 后 HALF_OPEN probe nv 一次
  else:
     → 走 5key×mode chain
     → 全坏(all_keys_exhausted):
        → 记 nv breaker failure
        → fallback POST ms_gw glm5_2_ms (openai body, model 已换)
        → 成 → 返回; 败 → 返回 ms error 让 CC 重试
  client_4xx (请求级) → 不 fallback
```

- 阈值 15（高于 cc4101 旧 8）：nv 偶发抖动不误切 ms，省配额。
- ms_gw 不计 nv breaker（breaker 只盯 nv 5key 健康）。
- 中途流挂（SSE 已发 CC）仍不能切——由 nv_gw emit content_filter/api_error 让 CC 重试
  （复用 R1640 polarity 逻辑，现已在 nv_gw stream 层）。

## 七、风险

- **两层 fallback 打架**: R1648e 删 cc4101 fallback 后，只剩 nv_gw 一层，避免双重重试。
- **format 代码漂移**: 三份复制（cc4101/nv_gw/ms_gw）会漂移。R1648a 先理边界，后续可考虑共享 volume。
- **agent 路径回归**: nv_gw 加 `/v1/messages` 不能影响 openai 路径，路由 if/elif 隔离 + 回归测 agent。
- **改动面大**: 6 轮跨 3 容器，每轮必须验证+commit，不可合并。
- **cc4101 纯透传后无转换**: 若 40006 的 /v1/messages 出 bug，cc4101 无法兜。需 40006 端点充分测后
  再做 R1648e。

## 八、与历史轮次关系

- R1643（刚完成）: cc4101 加回 ms fallback——**R1648e 会删除这部分**（fallback 下沉到 40006）。
  R1643 是过渡方案，R1648 是目标架构。
- R1640: cc4101 header 倒挂 + polarity 修复——这些逻辑在 R1648b/c 转移到 nv_gw 的 /v1/messages
  handler（stream 反向转换层）。
- R753: nv_gw 删跨 model fallback——R1648c 反向加回（但只 nv→ms，且在 gateway 层而非 adapter 层）。
