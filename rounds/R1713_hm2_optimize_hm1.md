# R1713: cc4101 收尾删死代码 — format/ 目录 + converters.py + stream.py 旧转换函数 (R1648 终态第3步)

> R1648 终态收尾三步走: R1704 (nv_gw /v1/messages 补诊断) → R1711 (cc4101 透传化) → **R1713 (删死代码)**.

## 背景

R1711 把 cc4101 从 anth↔oai 双转换器改成纯透传层后, 下列代码成死代码:
- `stream.py` 旧 `stream_to_anth` (L220-698) + `collect_stream_to_anth` (L701-1004) — 共 785 行,
  透传后不再被 handlers 调用.
- `converters.py` — thin re-export, handlers 不再 import.
- `format/` 目录 (anth_to_oai.py / oai_to_anth.py / __init__.py) — 只被 stream.py 旧函数 +
  converters.py import, 两者皆死, 故全死.

死代码不是无害的: 字节码路径多, mojibake 风险面大, 诊断点两套实现漂移 (R1640/R1674/R1675
皆因此踩坑). R1713 一次性切除.

## 改前确认 (ast 定位 + import 扫描)

`ast.parse` 顶层函数边界:
```
passthrough_stream:       L32-172  (保留)
passthrough_nonstream:   L175-217  (保留)
stream_to_anth:          L220-698  (删)
collect_stream_to_anth:  L701-1004 (删)
```

import 扫描确认:
- `handlers.py` 只 import `passthrough_stream, passthrough_nonstream` (不 import 旧函数).
- `converters.py` 不被任何活代码 import (只剩自身 + __init__ docstring 提及).
- `format/` 只被 stream.py L28 + converters.py import, 皆死.

circuit.py 评估: 纯状态机 (`is_primary_open`/`record_primary_*`/`circuit_state`),
**不含内容级逻辑**, 透传化后仍被 upstream.py + stream.py passthrough 正常使用, **不需简化**.

## 改动 (HM2 cc4101, /opt/cc-infra/proxy/cc4101/gateway/, bind-mount)

> 铁律: 只改 HM2. HM1 cc4101 缺 format/ 目录, 同步另轮.

### 1. stream.py (1004 → 212 行)
- 删 `stream_to_anth` (L220-698) + `collect_stream_to_anth` (L701-1004).
- 删模块级 `from .format.oai_to_anth import OaiSseToAnthropicConverter, oai_nonstream_to_anth` (L28).
- 删过时 R1696/R1703 注释块.
- 更新模块 docstring: 从"双转换器" → "R1713 纯透传层, 转换已下沉 nv_gw".
- 保留: `passthrough_stream` + `passthrough_nonstream` + 它们的 import (json/uuid/time/datetime/
  http.client/socket, config, logger, circuit).

### 2. converters.py — 删除
- `rm converters.py` (备份 converters.py.bak.R1713_pre).

### 3. format/ 目录 — 删除
- `rm -rf format/` (*.py 宿主删, __pycache__ 容器 root 删).
- 备份在 stream.py.bak.R1713_pre 里保留旧函数 (回滚用).

### 4. __init__.py docstring 更新
- 从"Anthropic↔OpenAI converter / always forces stream=true" → "R1711 透传层 / 转换下沉 /
  breaker 纯连接级 / fallback 仅 breaker OPEN 切".
- 模块结构清单删 converters.py, 加 circuit.py.

### 5. config.py
- 启动 banner docstring: 从"R854 NV-only no fallback" → "R1711 透传 /v1/messages + R1643 fallback".
- `PRIMARY_UPSTREAM_URL` 默认值: `.../v1/chat/completions` → `.../v1/messages`.
- `FALLBACK_UPSTREAM_URL` 默认值: 同上.
  (compose env 已覆盖为 /v1/messages, 改默认值防有人不设 env 时打错端点.)

### 6. app.py 启动 banner
- 旧: `upstream: nv_gw glm5_2_nv ONLY (R854, no ms_gw/40007 fallback)`.
- 新: `upstream: nv_gw glm5_2_nv /v1/messages` + `fallback: ms_gw glm5_2_ms (R1643, breaker-OPEN triggered) -> http://ms_gw:40007/v1/messages`.
- 加 `from .config import FALLBACK_UPSTREAM_URL, FALLBACK_UPSTREAM_MODEL`.

## 改后验证 (HM2, 重启 cc4101 后)

重启: `cd /opt/cc-infra && docker compose restart cc4101` (bind-mount 改动).

1. **语法**: `ast.parse(stream.py)` + `import gateway.stream, gateway.handlers, gateway.upstream` 全 OK.
2. **health**: `{"status":"ok","proxy_role":"cc4101","primary":"glm5_2_nv","port":4101}` ✅
3. **启动 banner** (准确反映现状):
   ```
   [START] cc4101 listening on 0.0.0.0:4101 (role=cc4101)
   [START]   primary  : glm5_2_nv
   [START]   upstream: nv_gw glm5_2_nv /v1/messages
   [START]   fallback: ms_gw glm5_2_ms (R1643, breaker-OPEN triggered) -> http://ms_gw:40007/v1/messages
   ```
4. **真实 CC 请求**: `model=claude-opus-4-8→glm5_2_nv cc_stream=True msgs=84 tools=30 (R1705 passthrough)` ✅
5. **E2E 流式**: 返回 anthropic SSE (message_start/content_block_start/content_block_delta "ok") ✅
6. **E2E 非流式**: 返回 anthropic JSON (`"type":"message","model":"glm5_2_nv",content=[{text:...}]`) ✅
7. **breaker**: `('CLOSED', 0, 0)` 纯连接级 ✅
8. **诊断联动** (R1704→R1711 架构稳定, 改后 15min 502 分布):
   ```
   empty_stream_response   | 12   (nv_gw zombie 检测透传)
   upstream_content_filter | 12   (R1704 content_filter polarity 透传)
   StreamStallWatcher      |  1   (passthrough 总时长兜底)
   ```
9. **总 SR** (改后 5min): 100×200 + 25×502 = 80.0% (502 全是 nv_gw 透传的 api_error, CC 重试) ✅
10. **无死循环回归** (R1672 铁律): 502 透传给 CC 重试, 不在 cc4101 内部循环; breaker CLOSED 不误切 ✅

## 体积对比

| 文件 | 改前 | 改后 |
|---|---|---|
| stream.py | 1004 行 | 212 行 |
| converters.py | 1018 字节 | (删) |
| format/ 目录 | 3 文件 ~32k | (删) |
| gateway 总 *.py | ~2500 行 | 1553 行 |

## 参数表

| 项 | 改前 | 改后 | 备注 |
|---|---|---|---|
| stream.py 旧函数 | stream_to_anth + collect_stream_to_anth | (删) | 785 行死代码 |
| converters.py | 存在 | (删) | 死 re-export |
| format/ 目录 | 3 文件 | (删) | 转换下沉 nv_gw |
| config 默认端点 | /v1/chat/completions | /v1/messages | 对齐透传 |
| app.py banner | "no fallback" | 列出 fallback URL | 准确 |

## 预期效果 (长期)

- cc4101 字节码路径收缩 38%, mojibake/漂移风险面减小.
- 诊断责任单一化: 只在 nv_gw (R1704 补齐), cc4101 不再持有任何转换/诊断逻辑.
- R1648 终态设想 "转换下沉各网关, cc4101 终瘦纯透传" **落地完成**.

## R1648 三步走总结

| 步 | 轮 | 改动 | 状态 |
|---|---|---|---|
| 1 | R1704 | nv_gw /v1/messages 补 recv-fallback + content_filter polarity | ✅ commit 3152cb1 |
| 2 | R1711 | cc4101 透传化 (anth→oai 转换 → 纯透传, breaker 纯连接级, fallback 降级) | ✅ commit d1efe54 |
| 3 | R1713 | 删 format/ + converters.py + stream.py 旧函数 (死代码) | ✅ 本轮 |

## 遗留 (另轮)

- HM1 cc4101 同步: HM1 缺 format/ 目录 (R1648 组只改 HM2), 需同步 R1711 透传化 + R1713 删死代码.
  铁律 HM2→HM1, 另轮处理.

## 验证清单

- [x] stream.py 语法 + 整包 import OK
- [x] format/ + converters.py 已删 (ls 确认)
- [x] health ok + StartedAt 新
- [x] 启动 banner 准确 (primary + fallback URL)
- [x] 真实 CC 请求走 passthrough
- [x] E2E 流/非流返回正确 anthropic 格式
- [x] breaker CLOSED (纯连接级)
- [x] 诊断联动 (content_filter + empty_stream + StreamStallWatcher) 稳定
- [x] 总 SR 80% (502 全透传 api_error)
- [x] 无死循环回归
- [x] stream.py 1004→212 行 (-785 行死代码)
