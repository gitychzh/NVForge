# R2427: nv_gw 三容器代码彻底解耦 (独立 gateway 目录)

> **日期**: 2026-08-16
> **类型**: 架构重构
> **影响范围**: nv_gw(40006) + dsv4p_nv40066(40066) + dsvf0731_nv40666(40666)
> **状态**: ✅ 已实施 + 验证通过

## 背景

三个 NV 网关容器 (40006/40066/40666) 历史上共用同一个 bind-mount 目录
`./proxy/nv-gw/gateway:/app/gateway`。这意味着在 40006 调整 glm5_2_nv 专属代码时,
可能无意中影响 40066 (dsv4p_nv) 或 40666 (dsv4f0731_nv) 的运行, 反之亦然。

虽然 `NVU_ACTIVE_TIERS` 环境变量已做模型级过滤 (每个容器只暴露自己的专职模型),
但共享代码意味着: 改 upstream.py 的 glm52 函数时, 40666 容器也会重启加载该改动,
如果改动有 bug, 三个容器同时挂。

## 方案

**方案 A: 独立目录 + sync 脚本** (用户批准)

- 每个容器拥有自己独立的 `gateway/` 目录
- 通用文件 (rr_counter, cooldown, nvcf_conn, pexec, func_health, db, logger, ...)
  通过 `sync_core.sh` 脚本保持同步
- 模型特定文件 (config.py, upstream.py, handlers.py, buffer_stream.py, glm52_mode_idx.py)
  各目录独立维护, 互不影响

## 实施细节

### 1. 备份 + 创建独立目录

```bash
cd /opt/cc-infra/proxy
cp -a nv-gw/gateway nv-gw/gateway.bak.R-decouple      # 全量备份
cp -a nv-gw/gateway nv-gw-dsv4p/gateway               # 40066 独立副本
cp -a nv-gw/gateway nv-gw-dsv4f0731/gateway            # 40666 独立副本
```

备份位置: `/opt/cc-infra/proxy/nv-gw/gateway.bak.R-decouple`

### 2. docker-compose.yml 挂载路径更新

| 容器 | 旧挂载 | 新挂载 |
|---|---|---|
| `nv_gw` (40006) | `./proxy/nv-gw/gateway` (不变) | `./proxy/nv-gw/gateway` |
| `dsv4p_nv40066` (40066) | `./proxy/nv-gw/gateway` | `./proxy/nv-gw-dsv4p/gateway` |
| `dsvf0731_nv40666` (40666) | `./proxy/nv-gw/gateway:rw` | `./proxy/nv-gw-dsv4f0731/gateway:rw` |

### 3. sync_core.sh 同步脚本

位置: `/opt/cc-infra/proxy/sync_core.sh`

通用文件清单 (16 个, 模型无关):
- `__init__.py`, `app.py`
- `rr_counter.py`, `cooldown.py`
- `nvcf_conn.py`, `pexec.py`
- `func_health.py`, `db.py`, `logger.py`
- `error_mapping.py`, `nv_breaker.py`, `big_input_breaker.py`
- `key_manager.py`, `probe_worker.py`
- `stream_success_judge.py`, `fid_discovery.py`

不同步的模型特定文件:
- `config.py` (各容器 NVU_ACTIVE_TIERS + 模型专属配置不同)
- `upstream.py` (glm52/dsv4p/dsv4f 专属函数)
- `handlers.py` (glm52 ms_fallback 门控)
- `buffer_stream.py` (glm52 mode chain 分发)
- `glm52_mode_idx.py` (仅 40006 使用)

用法:
```bash
./sync_core.sh             # 从 nv-gw(40006) 同步通用文件到 dsv4p + dsv4f0731
./sync_core.sh --diff      # 只看差异不同步
./sync_core.sh --from dsv4p # 反向: 从 dsv4p 同步到其他
```

### 4. 代码裁剪策略

**本轮不做激进代码裁剪**。原因:
- 三个目录已物理隔离, 编辑一个不影响其他 — 解耦已实现
- NVU_ACTIVE_TIERS 已确保非活跃模型代码不会执行
- upstream.py (2902行) / handlers.py (2603行) / buffer_stream.py (991行) 交错复杂,
  手动删行风险高 (import 引用、函数调用链断裂)
- 保留全量代码 = 未来如需在某容器临时加回某模型, 改 env 即可

后续可选: 在各目录中逐步删除非活跃模型的死代码 (独立 PR, 不影响运行)

## 验证

### 健康检查
```
nv_gw (40006):          {"status":"ok","nvcf_pexec_models":["glm5_2_nv"]}
dsv4p_nv40066 (40066):  {"status":"ok","nvcf_pexec_models":["dsv4p_nv"]}
dsvf0731_nv40666 (40666):{"status":"ok","nvcf_pexec_models":["dsv4f0731_nv"]}
```

### Docker 挂载验证
```
nv_gw:            /opt/cc-infra/proxy/nv-gw/gateway → /app/gateway (bind)
dsv4p_nv40066:    /opt/cc-infra/proxy/nv-gw-dsv4p/gateway → /app/gateway (bind)
dsvf0731_nv40666: /opt/cc-infra/proxy/nv-gw-dsv4f0731/gateway → /app/gateway (bind)
```

### 功能测试
- 40006 (glm5_2_nv): `POST /v1/chat/completions` → 200 OK, content="Hi!" ✅
- 40666 (dsv4f0731_nv): `POST /v1/chat/completions` → 200 OK, reasoning_content 正常 ✅
- 40066 (dsv4p_nv): NVCF dsv4p 端 EOL, 无法实测 (容器健康, 架构正确)

### sync_core.sh 验证
```
./sync_core.sh --diff → 0 file(s) differ (三个目录通用文件完全一致)
```

## 目录结构

```
/opt/cc-infra/proxy/
├── nv-gw/                    # 40006 (glm5_2_nv) — 主目录, 可自由改
│   ├── gateway/              #   bind-mount → /app/gateway
│   ├── gateway.bak.R-decouple  # 全量备份
│   ├── Dockerfile
│   └── gateway_main.py
├── nv-gw-dsv4p/              # 40066 (dsv4p_nv) — 独立目录, 可自由改
│   └── gateway/              #   bind-mount → /app/gateway
├── nv-gw-dsv4f0731/          # 40666 (dsv4f0731_nv) — 独立目录, 可自由改
│   └── gateway/              #   bind-mount → /app/gateway
└── sync_core.sh              # 通用文件同步脚本
```

## 下一步

1. **日常优化**: 可自由修改 `nv-gw/gateway/upstream.py` 的 glm5_2 代码, 不再影响 40066/40666
2. **通用 bug 修复**: 修好 `nv-gw/gateway/` 的通用文件后, 运行 `./sync_core.sh` 一键同步到其他目录
3. **可选裁剪**: 后续可在各目录中逐步删除非活跃模型的死代码 (降低认知负担, 非 P0)
4. **sync_core.sh CI**: 可选: 添加定时检查 (cron), 确保通用文件不漂移
