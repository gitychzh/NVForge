# R700: hm4104/opclaw4103 链路切换 — primary=dsv4p_nv40066, fallback=nv_gw:40006(glm5_2_nv)

**日期**: 2026-08-03
**主机**: HM2 (opc2_uname)
**改动类型**: docker-compose.yml env 修改 (cc-adapter: hm4104 + opclaw4103)

## 背景

用户要求核实并修改 hermes agent (hm4104) 和 openclaw (opclaw4103) 的模型链路为:
- hm4104: primary=dsv4p_nv40066:40066/dsv4p_nv, fallback=nv_gw:40006/glm5_2_nv
- opclaw4103: primary=dsv4p_nv40066:40066/dsv4p_nv, fallback=nv_gw:40006/glm5_2_nv

## 改前状态 (不符合需求)

| 容器 | PRIMARY_URL | PRIMARY_MODEL | FALLBACK_URL | FALLBACK_ENABLED |
|---|---|---|---|---|
| hm4104 | http://nv_gw:40006/v1 | dsv4p_nv | none | 0 (disabled) |
| opclaw4103 | http://nv_gw:40006/v1 | dsv4p_nv | none | 0 (disabled) |

问题: 两个 adapter 都走 nv_gw:40006 访问 dsv4p_nv (经 glm5_2_nv 容器), fallback 全关.

## 改后状态 (符合需求)

| 容器 | PRIMARY_URL | PRIMARY_MODEL | FALLBACK_URL | FALLBACK_MODEL | FALLBACK_ENABLED |
|---|---|---|---|---|---|
| hm4104 | http://dsv4p_nv40066:40066/v1 | dsv4p_nv | http://nv_gw:40006/v1 | glm5_2_nv | 1 |
| opclaw4103 | http://dsv4p_nv40066:40066/v1 | dsv4p_nv | http://nv_gw:40006/v1 | glm5_2_nv | 1 |

关键改动:
1. PRIMARY_URL: nv_gw:40006 → dsv4p_nv40066:40066 (直连 dsv4p 独立容器)
2. FALLBACK_URL: none → nv_gw:40006 (glm5_2_nv per-key 混合链路)
3. FALLBACK_MODEL: dsv4p_ms/glm5_2_ms → glm5_2_nv
4. FALLBACK_ENABLED: 0 → 1
5. MS_GW_API_KEY: ms-gw-token → nv-gw-token (fallback 指向 nv_gw 需要 nv-gw-token)
6. FALLBACK_HEADER_TIMEOUT: 新增 180s (hm4104) / 已有 180s (opclaw4103)
7. depends_on: +dsv4p_nv40066 (primary 目标)

## 验证

### 1. Health endpoints (all OK)
- hm4104: `primary_url=dsv4p_nv40066:40066, fallback_url=nv_gw:40006, fallback_enabled=true`
- opclaw4103: `primary_url=dsv4p_nv40066:40066, fallback_url=nv_gw:40006, fallback_enabled=true`
- dsv4p_nv40066: ok, 5 keys
- nv_gw: ok, 5 keys

### 2. Non-stream E2E (both 200)
- hm4104 → dsv4p_nv40066/dsv4p_nv: HTTP 200, 1.36s, model=deepseek-v4-pro ✓
- opclaw4103 → dsv4p_nv40066/dsv4p_nv: HTTP 200, 2.02s, model=deepseek-v4-pro ✓

### 3. Stream E2E (both 200)
- hm4104 streaming: HTTP 200, 2.03s, data:[DONE] ✓
- opclaw4103 streaming: HTTP 200, 2.14s, data:[DONE] ✓

### 4. Fallback target direct test
- nv_gw:40006/glm5_2_nv: HTTP 200, 65.5s, model=z-ai/glm-5.2 ✓

### 5. DB 路由铁证
```
host_machine=opc2sname-dsv4p40066, request_model=dsv4p_nv, status=200, upstream_type=nvcf_pexec
```
所有请求经 dsv4p_nv40066 容器, 走 nvcf_pexec, 未走 nv_gw.

### 6. 容器状态
- hm4104: Up 7 min
- opclaw4103: Up 7 min
- dsv4p_nv40066: Up 3 hr
- nv_gw: Up 2 hr

## 回滚
`cp /opt/cc-infra/docker-compose.yml.bak.R686 /opt/cc-infra/docker-compose.yml && docker compose up -d opclaw4103 hm4104`
