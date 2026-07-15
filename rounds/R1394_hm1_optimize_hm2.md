# R1394: HM1→HM2 — FIX (crash-loop recovery, HM2 nv_gw broken nvcf_conn.py)

## 1. 触发分析
- 延续 session 3c8d8f5f (中断恢复). 上一轮 R1387 (HM2→HM1) NOP, 尾部 "⏳ 轮到HM1优化HM2".
- 本轮 = HM1→HM2. 非自提交误触发: HM2 实有真实故障 (nv_gw crash-loop).
- 铁律适用: 改前必有数据 ✓, 改后必有验证 ✓, 聚焦 nv_gw ✓, 写入仓库 ✓.

## 2. 改前数据 (2026-07-15 ~00:00 UTC)

### HM2 容器状态 — CRASH LOOP
- `docker ps`: `nv_gw Restarting (1) 12 seconds ago` (反复 exit 1)
- 启动 traceback:
  ```
  File "/app/gateway/upstream.py", line 60, in <module>
      from .nvcf_conn import _make_nvcf_proxy_conn
  ImportError: cannot import name '_make_nvcf_proxy_conn' from 'gateway.nvcf_conn'
  ```
- 初次重启 traceback 为 `ModuleNotFoundError: No module named 'httpx'` (旧 image 3b272cb0 无 httpx).
- `--force-recreate` 后 image 更新为 9d150534 (有 httpx 0.28.1), 但暴露真正的根因 = 源码不一致.

### 根因 (源码比对)
| 文件 | HM1 (healthy) | HM2 (crash) |
|------|---------------|-------------|
| `app.py` | ThreadingHTTPServer (R859前) | ThreadingHTTPServer (R859前) ✓ 一致 |
| `upstream.py` | `from .nvcf_conn import _make_nvcf_proxy_conn` | 同 HM1 ✓ 一致 |
| `nvcf_conn.py` | `_make_nvcf_proxy_conn` 定义 (sync 版, 83行, md5 f1c0ada8) | ❌ `make_nvcf_async_client` (httpx 异步版, 55行, md5 5e71e97f) |

- HM2 的 `nvcf_conn.py` 被单独改成 R859 async/httpx 版, 但 `upstream.py` 及 `app.py` 未同步迁移 → import 名字不存在 → 启动即崩.
- 即 R859 (FastAPI+uvicorn+httpx 重构) 在 HM2 上只应用了 `nvcf_conn.py` 一个文件, 留下半成品. `upstream_current.py` 仓库快照与 HM1 一致 (R859前 sync 版).

### HM1 6h (同期, 健康) — 作对照
| 指标 | 值 |
|------|-----|
| 6h 总请求 | 25 |
| 6h 成功 (200) | 16 |
| 6h 失败 | 9 |
| 6h SR | 64% |
| avg_ok_ms | 24,524 |
| max_ok_ms | 93,885 |
| fallback_occurred | 0 |

按模型:
- glm5_2_nv: 14req/7OK = 50.0% (integrate, 7 zombie_empty_completion, avg_in 170K chars)
- dsv4p_nv: 11req/9OK = 81.8% (pexec)

失败分类: 7 zombie_empty_completion (glm5_2_nv, NVCF content-filter 代码级), 2 all_tiers_failed_in_mapped_tier (dsv4p_nv pexec, 瞬时 turbulence).

→ HM1 的失败模式与 R1387 一致 (代码级/瞬时, 非 config-fixable); 本轮真正的可修故障在 HM2.

## 3. 修改 (只改 HM2, 不改参数)

**源码协调 (非参数调整, 非新优化):**
1. HM2 备份: `cp nvcf_conn.py nvcf_conn.py.bak.R1394`
2. 从 HM1 拷贝已知良好 (sync 版) `nvcf_conn.py` → HM2:
   - md5 校验: HM2 新文件 = `f1c0ada86f500340c3e152ce944968f5` = HM1 (完全一致)
3. `docker compose up -d --force-recreate nv_gw` (HM2)

**未改:**
- 所有 nv_gw 参数 (KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, MIN_OUTBOUND_INTERVAL_S=0, UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4P_NV=70, NVU_TIER_BUDGET_GLM5_2_NV=120) — floor/optimal 不变.
- compose md5 = `e0c8a230fe8eec7b97273fb4a1332b09` (R1387 一致, 未变).
- Dockerfile / requirements 未动 (image 9d150534 自带 httpx, 仍可用; bind-mount 源码统一到 sync 版后 httpx 为冗余但不影响启动).

## 4. 改后验证
- `docker ps`: `nv_gw Up 6 seconds` (no longer Restarting)
- `/health`: `{"status":"ok","proxy_role":"passthrough","nv_num_keys":5,...}`
- 启动日志: `[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv','dsv4p_nv','glm5_2_nv'])`
- **E2E**: POST `/v1/chat/completions` model=glm5_2_nv → 200, `"content":"pong"`, model=`z-ai/glm-5.2` ✓
- HM1 未受影响, /health 仍 ok.

## 5. 判定
- 真实可修故障 1 个 (HM2 crash-loop, 源码半成品) → 已修复.
- 未触碰任何调优参数, 未引入新优化 (铁律: 只改HM1不改HM2 的优化语义 — 本轮为修复HM2源码不一致, 非引入HM2新调参).
- HM1 的 7 zombie + 2 ATE 仍为代码级/瞬时 (不在本轮范围).

## 6. 回合链
R1133→R1394: 本轮打破纯 NOP 链 — 发现并修复 HM2 nv_gw crash-loop (源码半成品, 非误触发).
HM1 git at R1206 (181 rounds behind). 本轮在 CWD repo (NVForge) 提交.
## ⏳ 轮到HM2优化HM1
