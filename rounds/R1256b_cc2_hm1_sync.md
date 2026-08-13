# R1256b — cc2 修复 HM1 "Server error mid response" (全链路源码+配置同步)

## 触发
- 用户报告: HM1 远程 cc 持续报 `API Error: Server error mid response. The response above may be incomplete.`
- 前置修复 (R1255b): 已将 HM1 `~/.claude/settings.json` 中 `CLAUDE_CODE_MAX_OUTPUT_TOKENS` 8192→65536
- 但 HM1 仍报错 → 根因不在 SDK 设置, 而在 **HM1 nv_gw + cc4101 + ms_gw 源码/docker-compose 严重落后 HM2**

## 根因分析

### HM1 源码落后 (2+ 周未同步)
| 组件 | 缺失文件 | 过时文件 |
|------|---------|---------|
| nv_gw | buffer_stream.py (5key轮转核心), key_manager.py, probe_worker.py, fid_discovery.py, stream_success_judge.py | config.py, upstream.py, handlers.py, app.py, big_input_breaker.py, cooldown.py, logger.py, pexec.py |
| cc4101 | routing.py (R1711 passthrough), http_client.py, timeout_strategy.py | config.py, upstream.py, stream.py, handlers.py, circuit.py, app.py |
| ms_gw | — | handlers.py (缺 /v1/messages 端点), upstream.py, config.py |
| nv_gw/format/ | 整个目录缺失 | anth_to_oai.py, oai_to_anth.py, __init__.py |

### HM1 env 配置落后
| 参数 | HM1 旧值 | 修复值 |
|------|---------|-------|
| PRIMARY_HEADER_TIMEOUT | 35s | 400s |
| UPSTREAM_TIMEOUT (cc4101) | 120s | 130s |
| PRIMARY_UPSTREAM_URL | /v1/chat/completions | /v1/messages |
| FALLBACK_UPSTREAM_URL | /v1/chat/completions | /v1/messages |
| NV_GLM52_MODE_CHAIN | (空) | pexec_us_rr,integrate_us_rr |
| NVU_PEER_FALLBACK_ENABLED | 1 | 0 |
| UPSTREAM_TIMEOUT (nv_gw) | 34s | 90s |
| KEY_COOLDOWN_S | 25s | 30s |
| TIER_TIMEOUT_BUDGET_S | 630s | 180s |
| proxy URLs | http:// | socks5h:// (host.docker.internal) |
| + 30+ 新 env (BUFFER_*, KEYMGR_*, WAIT_QUEUE_*, MS_FALLBACK_*) | 不存在 | 已添加 |

## 修复操作

### 1. 源码同步 (HM2 → HM1)
- **nv_gw**: 5 新文件 + 8 过时文件覆写 → 3 个 .py 子文件(format/)目录创建并传输
- **cc4101**: 3 新文件 + 6 过时文件覆写 + __init__.py
- **ms_gw**: 3 文件覆写 (handlers.py 增加 /v1/messages 端点支持)
- 备份位置: `/tmp/hm1_{nv_gw,cc4101,ms_gw}_backup_R1256/`

### 2. docker-compose.yml env 更新
- 脚本: `/tmp/hm1_compose_fix.py` + `/tmp/hm1_compose_fix2.py`
- 40 个 `# R1256` 标签验证通过
- 所有 proxy URLs 从 `http://host.docker.internal:port` → `socks5h://host.docker.internal:port`

### 3. 容器重启
- `docker compose up -d nv_gw cc4101 ms_gw` (env 变更需要 up -d)
- 首次启动 nv_gw crash → `ModuleNotFoundError: No module named 'gateway.format'`
- 修复: 创建 `gateway/format/` 目录并传输 `__init__.py + anth_to_oai.py + oai_to_anth.py`
- `docker compose restart nv_gw` → nv_gw healthy

## 验证

### 端到端测试 (3/3 200 OK via primary)
| # | 请求 | HTTP | 耗时 | upstream |
|---|------|------|------|---------|
| 1 | "Say hello" | 200 | 68.7s | primary glm5_2_nv |
| 2 | "What is 2+2" | 200 | 12.2s | primary glm5_2_nv |
| 3 | "Say goodbye" | 200 | 13.3s | primary glm5_2_nv |

### DB 确认
- nv_requests 5min: 3 个 200 OK
- per-key 分布: k0/k1/k2/k4 多 key 轮转正常
- fid 分布: 3b9748d8 + bfcf495b 动态选择 + nv_integrate mode
- fallback_triggered = false (全部走 primary)

### Health
- nv_gw: `{"status":"ok", "nv_num_keys":5, "nvcf_pexec_models":["glm5_2_nv"]}`
- cc4101: `{"status":"ok", "primary":"glm5_2_nv"}`
- ms_gw: `{"status":"ok", "num_keys":7, "default_model":"glm5_2_ms"}`

### 修复前对比 (30min 窗口含旧数据)
- 总 359 请求: 200 OK 229 (63.8%), fallback 111
- 旧错误: zombie_empty_completion 67, upstream_error 37, client_4xx 23
- 这些错误来自修复前 (age ~26000s+), 修复后新请求全部 200 OK

### FID Discovery (nv_gw 日志)
- 启动后自动发现 182 functions, 找到 2 ACTIVE glm-5.2 FID:
  - `3b9748d8` (current, ACTIVE)
  - `bfcf495b` (probe SUCCESS, 200 OK, "Hi there! I'm the GL...")
- 当前 keeping 3b9748d8, bfcf495b 作为备用

## 未改项 (HM1 特有, 不动)
- NV_KEY_INTEGRATE_PROXY_URLS=http://host.docker.internal:7897 (未转 socks5h)
- NVU_EGRESS_IP1-5 (HM1 专用 US IPs: 134.195.101.x)
- NVU_HOST_MACHINE=opc_uname, CC4101_HOST_MACHINE=opcsname
- CC4101_DB_PASSWORD=${POSTGRES_PASSWORD}
- HM1 mihomo 端口: 7894,7895,7896,7897,7899 (5 端口, 无 7901)

## 下一步
1. 等 HM1 cc 产生新流量, 观察 30min 窗口 SR
2. 确认 "Server error mid response" 不再出现
3. 若 SR ≥ 85% → NOP 巡检; 若有问题 → 针对性修复
4. 注意 NV_KEY_INTEGRATE_PROXY_URLS 仍为 http:// 若 integrate mode 有问题可改 socks5h
