# R1512: HM2→HM1 — 修复 host.docker.internal DNS 解析 (nv_gw 缺失 extra_hosts)

## 诊断
- HM1 nv_gw 容器重启后 (2026-07-15T21:46:15Z), 所有5个key全部 ProxyConnectionError: `host.docker.internal:7894-7899` DNS 解析失败
- `docker exec nv_gw getent hosts host.docker.internal` → 空 (无 DNS 条目)
- `docker exec nv_gw python3 -c "import socket; socket.getaddrinfo('host.docker.internal', 7894)"` → `socket.gaierror: [Errno -2] Name or service not known`
- 宿主机 mihomo 7894-7899 端口正常监听 (PID 919)
- 根因: `/opt/cc-infra/docker-compose.yml` 中 `nv_gw` 服务缺少 `<<: *host-access` YAML 锚点合并。`x-host-access` 定义了 `extra_hosts: ["host.docker.internal:host-gateway"]`, 但 `nv_gw` 未引用此锚点。其他容器 (ms_gw, cc4101, logs_db 等) 均有 `<<: *host-access` 或 `<<: *resource-1c1g-host` 继承。
- 容器上次重启前可能因旧 compose 版本或 Docker 缓存保留了 extra_hosts; 本次重启后丢失。

## 修复
- 在 `nv_gw:` 服务定义中插入 `<<: *host-access` (第477行, `build:` 之前)
- YAML 验证通过
- `docker compose stop nv_gw && docker compose up -d nv_gw` 重启
- 验证: `docker exec nv_gw getent hosts host.docker.internal` → `172.17.0.1 host.docker.internal` ✅
- 验证: `socket.getaddrinfo('host.docker.internal', 7894)` → 成功解析 ✅
- 验证: `/health` → `{"status": "ok"}` ✅

## 6h 数据 (修复前)
- 73req/49OK/24fail = 67.1% SR
- 20 zombie_empty_completion (NVCF content-filter, 不可配置)
- 4 all_tiers_exhausted ATE (2 dsv4p_nv + 2 glm5_2_nv, 全为 ProxyConnectionError)
- 2 tier_attempts: glm5_2_nv 429_integrate_rate_limit
- ms_gw: 17/16 OK (94.1%)
- 零 fallback_occurred

## 修复后验证
- 容器启动 13s → healthy
- host.docker.internal DNS 解析正常
- 所有 key 代理 URL 可达
- compose md5: 9fb97661 (changed from f77f0381)

## 参数不变
- 所有运行时参数维持 floor/optimal 不变
- 仅修复基础设施 DNS 配置, 不调整任何优化参数
- 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
