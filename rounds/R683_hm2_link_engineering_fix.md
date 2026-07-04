# R683: HM2 远程模型链路工程化修复 (5 偏差全修) — 完成

## 改前数据 (2026-07-04 16:45, 6h 窗口)

### HM2 nv_gw
- dsv4p_nv 850 req 93.1% / glm5_2_nv 215 req 91.6% / kimi_nv 1 req 100%
- 错误: NVStream_TimeoutError 41, all_tiers_exhausted 36 (全 glm5_2_nv, 全卡 ~61s)
- fallback: 4 次 glm5_2_nv→dsv4p_nv (本地 tier), **0 次 peer fallback** (自环空转)

### HM1 nv_gw
- glm5_2_nv 265 req 97.0% / dsv4p_nv 13 req 61.5% / kimi_nv 2 req; 7 fallback, 13 ATE

### HM2 ms_gw
- 77 req 全 ok; ms_requests 表来自 jsonl 离线导入 (非实时)

## 5 偏差 + 修复结果

### #1 🔴 HM2 peer fallback 自环 → 修复 ✅
- 原: `NVU_PEER_FALLBACK_URL: http://100.109.57.26:40006` (HM2 自己 IP) → 自环空转
- 改: `http://100.109.153.83:40006` (HM1 IP)
- **验证 (实测)**: 16:03:08 日志 `[NV-PEER-FB] attempting peer fallback to http://100.109.153.83:40006` — 修复前不可能出现此日志 (自环)。机制已恢复, 本次 HM1 也 timeout (NVCF surge), 但 peer fallback 通道正确触发 (metrics jsonl 13 次 peer_fallback_error, 全是 peer 端 timeout 非自环)

### #2 🟡 peer fallback timeout 两机对齐 ✅
- HM1 `NVU_PEER_FALLBACK_TIMEOUT` 8→25 (R649 的 8s 是 HM2 自环时 peer 100% timeout 的产物, 已失效)
- 两机现在都 25s, 语义一致

### #3 🟡 ms_gw 实时 DB 写入 (两机对称) ✅
- 新建 `proxy/ms-gw/gateway/db.py` (抄 nv_gw db.py 模式: 异步 queue + daemon thread + batch INSERT, env 前缀 MSU_DB_*)
- `logger.py` `_log_metrics` 加 `db.enqueue_metrics(entry)` 调用 (best-effort, DB down 不阻塞)
- `Dockerfile` 加 `pip install psycopg2-binary`
- compose 两机加 `MSU_DB_ENABLED/HOST/PORT/USER/PASSWORD/NAME + MSU_HOST_MACHINE` env
- `postgres/ms-schema.sql` 新建 (CREATE TABLE IF NOT EXISTS ms_requests + ALTER 补列)
- **验证**: HM1 `select ... where host_machine='opc_uname'` → 1 行; HM2 `host_machine='opc2sname'` → 3 行。旧 251 行 importer 数据 host_machine='unknown' 保留。

### #4 🟢 backend_model 大小写归一化 (仅观测层) ✅
- variant 10 个 typo 是设计本意 (绕 MS 限流), **不改 variant**
- db.py 写入时额外存 `normalized_backend_model` = backend_model.upper()
- 验证: HM2 新行 `backend_model=ZHIPUAI/gLm-5.2` / `normalized_backend_model=ZHIPUAI/GLM-5.2`, group by 可聚合

### #5 🟢 compose 注释过时视角 ✅ (不动)
- 大量 R-round 注释 "铁律:只改HM1不改HM2" 是 R569 前 HM2→HM1 交替优化视角
- **不逐条删** (R-number 演进有追溯价值), 只在本次新改注释写 R683 新视角
- CLAUDE.md / 本 round 文件已说明

## 端到端验证

| 链路 | HM1 | HM2 |
|---|---|---|
| nv_gw /health | ok | ok |
| nv_gw peer fallback URL | →HM2 (.57.26) ✅ | →HM1 (.83) ✅ |
| nv_gw peer fallback timeout | 25s | 25s |
| kimi_nv | 通 | 通 |
| dsv4p_nv / glm5_2_nv | ATE (NVCF surge) | ATE (NVCF surge) |
| ms_gw /health | ok | ok |
| ms_gw 实时 DB 写入 | 1 行 opc_uname | 3 行 opc2sname |
| 9 容器 healthy | 是 | 是 |

注: dsv4p_nv/glm5_2_nv 两机同时 ATE = NVCF 平台侧 surge (memory: nvcf-platform-intermittent-outage), 非 R683 引入。kimi_nv + ms_gw 两机全通证明链路本身健康。

## 改动文件清单

HM2 (`/opt/cc-infra`):
- `docker-compose.yml` — nv_gw PEER_FALLBACK_URL 修自环; ms_gw 加 MSU_DB_* env
- `proxy/ms-gw/gateway/db.py` — 新建
- `proxy/ms-gw/gateway/logger.py` — 加 db.enqueue_metrics 调用
- `proxy/ms-gw/Dockerfile` — 加 psycopg2-binary
- `postgres/ms-schema.sql` — 新建
- 备份: docker-compose.yml.bak.R683, logger.py.bak.R683, Dockerfile.bak.R683

HM1 (`/opt/cc-infra`): 同上对称

## 回滚
- #1/#2: compose 改回原值 + `docker compose up -d nv_gw`
- #3: compose 删 MSU_DB_* env + `docker compose up -d ms_gw` (db.py import 失败 graceful 降级) 或 Dockerfile 回滚
- ms_requests 表留着 (IF NOT EXISTS 幂等)
