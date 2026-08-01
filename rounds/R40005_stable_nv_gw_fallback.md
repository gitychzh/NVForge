# R40005: 创建 40005 稳定版 nv_gw 兜底容器

## 摘要

在 HM2 创建独立端口 40005 的 nv_gw_stable 容器，作为 40006 (nv_gw) 的稳定版兜底。
40005 拥有独立的 gateway 代码目录和独立的 KeyManager 状态，互不影响。

## 背景

- openclaw → opclaw4103 → 40006 (dsv4p_nv) — 已配置，无需改动
- hermes → hm4104 → 40006 (dsv4p_nv) — 已配置，无需改动
- 需要一个稳定版兜底：40006 代码优化/参数调整时，40005 保持旧版稳定配置

## 改动

### 1. 独立代码目录

```
cp -r /opt/cc-infra/proxy/nv-gw /opt/cc-infra/proxy/nv-gw-stable
# 清理 .bak/.preR 文件，保持干净
```

### 2. docker-compose.yml 新增 nv_gw_stable 服务

- 端口: 40005:40005
- 镜像: cc-infra-nv_gw_stable:latest (独立 build)
- bind-mount: ./proxy/nv-gw-stable/gateway (独立代码目录)
- 日志: ./logs/nv_gw_stable
- 与 nv_gw 的关键差异:
  - `LISTEN_PORT=40005`
  - `NVU_HOST_MACHINE=opc2sname-stable` (区分日志)
  - `NVU_PEER_FALLBACK_ENABLED=0` (不回环 peer)
  - `NVU_BUFFER_CALLERS=` (清空，不做 buffer)
  - `NVU_CALLER_KEY_MAP=` (清空，5-key 自由轮转)
  - `NVU_DISABLE_MS_FALLBACK=1` (纯 NV，独立兜底)
- 其余参数与 nv_gw 完全一致 (keys, proxies, model tiers, timeouts)

### 3. 不改动的部分

- openclaw.json — 已是 opclaw4103/dsv4p_nv ✓
- hermes config.yaml — 已是 hm4104/dsv4p_nv ✓
- opclaw4103 容器 env — 已是 dsv4p_nv ✓
- hm4104 容器 env — 已是 dsv4p_nv ✓
- nv_gw (40006) — 未修改

## 验证

| 测试 | 路径 | 结果 |
|---|---|---|
| 40005 health | curl localhost:40005/health | ✅ ok, 5 keys, 3 tiers |
| 40005 dsv4p_nv (non-stream) | curl 40005 → NVCF pexec | ✅ HTTP 200, 2.75s, deepseek-v4-pro |
| 40005 dsv4p_nv (stream) | curl 40005 stream | ✅ NV-SUCCESS k2 (curl timeout due to stream close, gateway log confirms success) |
| 40006 health | curl localhost:40006/health | ✅ ok, 5 keys, 3 tiers |
| 40006 dsv4p_nv (non-stream) | curl 40006 → NVCF pexec | ✅ HTTP 200, 1.8s (after cooldown recovery) |
| 40006 glm5_2_nv (non-stream) | curl 40006 → NVCF integrate | ✅ HTTP 200, 33.8s |
| hm4104 health | curl 4104/health | ✅ primary=dsv4p_nv |
| opclaw4103 health | curl 4103/health | ✅ primary=dsv4p_nv |
| hm4104 E2E dsv4p_nv | hermes → hm4104 → 40006 → NVCF | ✅ HTTP 200, 4.6s |
| opclaw4103 E2E dsv4p_nv | openclaw → opclaw4103 → 40006 → NVCF | ✅ HTTP 200, 6.5s |

### 40005 优势验证

当 40006 的 dsv4p_nv 全部 5 key 429 冷却时 (NVCF 账户级限流)，40005 因独立 KeyManager
仍可成功 — 实测: 40006 返回 502 (all keys cooldown)，40005 同时返回 200 (k1 成功)。

## 后续

- 40005 作为稳定兜底，代码冻结在当前版本
- 40006 可继续代码优化 (模型自我优化)
- 如 40006 优化出问题，adapter 可切换 fallback 到 40005
