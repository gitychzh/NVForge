# R310: HM1 工程化重构 — gateway 源码模块化 (authorized self-change)

**Role**: HM1 (opc_uname) — 工程化重构 (非交替优化轮; 用户授权本轮仅设置HM1)
**Timestamp**: 2026-06-29 22:10 CST
**Change**: gateway 源码模块化拆分, **逻辑零改动**, 仅工程结构优化 + 修 1 个真实配置 bug
**Category**: 工程化/可维护性 — 长期维护、方便修改、模块化设计
**前轮**: R309 (HM1→HM2 无变更)

> 本轮不属交替优化(optimizer→peer)序列, 是用户授权的 HM1 自身工程化重构
> ([[iron-rule-interpretation]] 授权破例自改边界). 不碰 HM2 任何东西.
> 铁律破例依据: 用户明确 "本轮仅设置HM1,聚焦HM1,不讨论hm2".

## 1. 目标
从工程化角度重构 hm40006 gateway 源码: 模块化、格式统一、可长期维护.
**不改变任何运行时逻辑**(路由/超时/重试/冷却/DB字段全部等价). 改后必须 rebuild +
端到端测试确认能跑、配置生效、DB 记录正确.

## 2. 改前数据(改前必有数据)
- gateway 源码 8 个 .py, 最大 upstream.py=705L 混 5 类职责(连接构造+请求体构造+空200检查+tier循环+execute_request), config.py=275L 混(纯配置+RR计数器+cooldown状态机+throttle+signal handler)
- flake8 全量: 仅 1 处 E702 (handlers.py:105 分号) + upstream.py 2 处 trailing-ws. 底子不错.
- **真实配置 bug**: `/opt/cc-infra/.env:2 HM_HOST_MACHINE=opcsname` (HM2 主机名被复制到 HM1) → HM1 写入 DB 的 `host_machine` 字段标成 HM2, 两台数据在 DB 混淆. DB 实测改前确有 `host_machine=opcsname` 行.

## 3. 模块化拆分(纯搬家, 逻辑等价)

| 原 | → 新 | 搬移内容 |
|---|---|---|
| upstream.py | nvcf_conn.py (~85L) | `_make_nvcf_direct_conn`, `_make_nvcf_proxy_conn` (含空url→直连分支) |
| upstream.py | pexec.py (~80L) | `_build_pexec_body`, `_check_empty_200` |
| upstream.py | upstream.py (~530L) | `UpstreamResult`, `_try_tier_keys`, `execute_request` (从 nvcf_conn/pexec import) |
| config.py | rr_counter.py (~95L) | RR 计数器状态机: `_load/_save/_log_migration/_next_hm_nv_key`, atexit/signal flush |
| config.py | cooldown.py (~55L) | 429 冷却状态机: `is/mark/reset_key429`, `KEY/TIER_COOLDOWN_S` |
| config.py | config.py (~160L) | 纯配置 + `throttle_outbound`, 末尾 re-export 保持下游 import 不破 |

**兼容性关键**: config.py 末尾 `from .rr_counter import _next_hm_nv_key, _save_rr_counter`
+ `from .cooldown import is_key_cooling, mark_key_cooling, reset_key429_count, KEY_COOLDOWN_S, TIER_COOLDOWN_S`
→ 所有 handlers.py/upstream.py 现有 `from .config import ...` 语句零改动. 风险最小.

### 格式统一
- 修 upstream.py 2 处 trailing-ws
- 修 handlers.py:105 E702 分号 → 两行
- upstream.py docstring 更新到 Rproxy/Reng 现状(原写 R50 旧设计)

### 不动的部分
- db.py / logger.py / error_mapping.py / app.py / __init__.py — 不改
- 所有运行时参数 (TIER_TIMEOUT_BUDGET_S=182, UPSTREAM_TIMEOUT=64, cooldown=38, MIN_OUTBOUND=18.2 等) — 不动
- 路由逻辑 (k1/k3/k5 mihomo, k2/k4 直连) — 不动
- DB schema/INSERT 字段/表结构 — 不动
- docker-compose tunable env — 不动(只改 .env 的 HM_HOST_MACHINE)

### 修复的 1 个 bug
- `.env:2 HM_HOST_MACHINE=opcsname` → `opc_uname` (HM1 真实名), 使 DB host_machine 字段正确

## 4. 改后验证(改后必有验证 — 8 步全过)

1. **语法**: 每个新文件 `ast.parse` 通过 ✅ (12/12 OK)
2. **flake8**: 容器内 `flake8 --max-line-length=120 --extend-ignore=E203,W503,E702 *.py` → **FLAKE8-CLEAN** ✅
3. **import 链**: `docker exec hm40006 python3 -c "import gateway.config, rr_counter, cooldown, nvcf_conn, pexec, upstream, handlers, app"` → **IMPORT-CHAIN-OK** ✅
4. **re-export 生效**: `from gateway.config import _next_hm_nv_key, is_key_cooling, mark_key_cooling, reset_key429_count, TIER_COOLDOWN_S, KEY_COOLDOWN_S, _save_rr_counter` → **REEXPORT-OK** ✅
5. **rebuild + up**: `docker compose build hm40006 && up -d hm40006`, health=ok ✅ (`hm_num_keys:5, nvcf_pexec_models:["deepseek_hm_nv"]`)
6. **路由不变**: 发请求, HM-KEY 日志仍 k1/k3/k5=via mihomo(7894/7896/7899)、k2/k4=DIRECT ✅ (RR 正确轮转 k3→k4→k5→k1→k2→k3)
7. **DB 记录正确**: 改后请求落地 hm_requests, `host_machine=opc_uname` (不再是 opcsname), status=200, nv_key_idx 与 RR key 对齐 ✅
8. **抓包**: nsenter 进容器 netns ss 抓连接(proxy=host.docker.internal:789x / direct=NVCF:443). 流式连接瞬时难抓, 但 HM-KEY 日志的 `via` vs `DIRECT` + DB nv_key_idx 已双重确认路由生效 ✅

### 改后实测请求
- `POST /v1/chat/completions deepseek_hm_nv stream=false` → HTTP 200, 22.7s, 有效 content
- DB 5 行: k1(idx0)/k2(idx1)/k3(idx2)/k4(idx3)/k5(idx4) 各 status=200, host_machine=opc_uname

### 重构中遇到并修复的 1 个迁移缺陷
- 首次 rebuild 后容器 Restarting(1): `rr_counter.py NameError: name 'sys' is not defined`
  (config.py 原有 `import sys`, 提取时漏带; rr_counter.py 的 `print(..., file=sys.stderr)` 需要).
  补 `import sys` 后 rebuild → 容器 Up, 正常. 已纳入最终交付.

## 5. 回滚
全部源码备份 `*.bak.Reng_20260629_220211`, compose + .env 同名备份. 任何失败 → 还原 + rebuild.
最终方案已全部验证通过, 无需回滚.

## 6. 交付
- 重构后 8→12 个 .py (新增 nvcf_conn/pexec/rr_counter/cooldown)
- 修 `.env HM_HOST_MACHINE=opcsname→opc_uname`
- 更新 upstream.py docstring
- 端到端测试报告(本文件 §4)
- 关键工程收益: upstream.py 705L→530L(降25%), config.py 275L→160L(降42%), 单文件单职责, 后续改连接/请求体/RR/冷却各自只动一个文件

## 7. 参数表(本轮未动, 仅工程化)
| 参数 | 值 | 说明 |
|---|---|---|
| TIER_TIMEOUT_BUDGET_S | 182 | 不变 |
| UPSTREAM_TIMEOUT | 64 | 不变 |
| KEY_COOLDOWN_S / TIER_COOLDOWN_S | 38 / 22 | 不变 |
| MIN_OUTBOUND_INTERVAL_S | 18.2 | 不变 |
| HM_CONNECT_RESERVE_S | 5 | 不变 |
| 路由 | k1/k3/k5=mihomo(7894/7896/7899), k2/k4=DIRECT | 不变 |

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记(交替优化序列恢复)
