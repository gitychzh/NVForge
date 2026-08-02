# R-modref: cc4101 模块化拆分 — upstream.py 456行→3模块

## 摘要

cc4101 的 `upstream.py` (456行) 混合了 8 个职责:HTTP 传输、动态超时分档、路由、fallback、熔断集成、错误分类、CHAIN_BUDGET 判断、FORCE_FALLBACK。拆为 3 个独立模块,不改任何逻辑。

## 背景

cc4101 在 HM2 上经过 R684→R1643→R1705→R2154→R2202→R2417 等多轮迭代,`upstream.py` 膨胀到 456 行。虽然其他模块(config/circuit/db/logger/error_mapping/handlers/stream)已经相对干净,但 `upstream.py` 成了单点复杂度。

注: HM1 的 cc4101 代码与 HM2 不同(HM1 仍做 anth→oai 转换,HM2 已 R1705 透传化)。本次只改 HM2。

## 变更

### 新增 3 个模块

| 模块 | 行数 | 职责 | 改什么时动它 |
|---|---|---|---|
| `http_client.py` | ~120 | 纯 HTTP 传输: `_parse_url`, `_call_upstream`, `_restore_read_timeout`, `_UpstreamError` | 改网络层 |
| `timeout_strategy.py` | ~50 | 超时分档: `get_primary_header_timeout`, `get_fallback_header_timeout` (R2154 6档) | 改超时策略 |
| `routing.py` | ~250 | 路由 + 熔断 + fallback + 错误分类: `execute_request`, `UpstreamResult`, `_try_primary`, `_try_fallback`, `_should_record_primary_failure` | 改路由/fallback 策略 |

### upstream.py → re-export 兼容

`upstream.py` 保留为 re-export 文件,`from .upstream import execute_request` 仍可用。handlers.py 不需改 import。

### 未动的文件

- `handlers.py` — 不改(通过 `from .upstream import execute_request` 间接走 routing.py)
- `stream.py` — 不改(316 行,相对内聚)
- `config.py` / `circuit.py` / `error_mapping.py` / `db.py` / `logger.py` — 不改

## 参数表

无参数变更。所有 env 变量、超时值、分档表完全保持不变。

## 数据

重构前 30min 窗口 cc2 链路 SR=100% (R-nvonly-post264~post266 NOP patrol 数据)。
本次纯代码重组,不改运行时行为。

## 验证

1. ✅ `docker restart cc4101` — 启动无 import 错误
2. ✅ `curl /health` — `{"status":"ok"}`
3. ✅ 非流式 E2E — `POST /v1/messages` 返回正常 anthropic JSON (dsv4p_nv, 3.5s)
4. ✅ 流式 E2E — SSE 事件正常 (message_start → thinking_delta → text_delta → message_stop)
5. ✅ cc_requests DB — 重构后 10 条请求全 200,无 error_type
6. ✅ 日志 — R2254-OBS 观测点正常输出,hdr_to 值正确

## 预期效果

- 改超时策略 → 只动 `timeout_strategy.py` (~50 行),不碰 HTTP 传输和路由
- 改路由/fallback → 只动 `routing.py` (~250 行),不碰 HTTP 传输和超时
- 改网络层 → 只动 `http_client.py` (~120 行),不碰路由和超时
- 单个模块最大 250 行(之前 456 行),复杂度降低 45%

## 文件清单

| 文件 | 位置 |
|---|---|
| http_client.py | /opt/cc-infra/proxy/cc4101/gateway/ + deploy_artifacts/R-modref_cc4101_modular_split/ |
| timeout_strategy.py | 同上 |
| routing.py | 同上 |
| upstream.py (re-export) | 同上 |
| *.py.bak.R-modref | 备份在 gateway/ 目录 |
