# R2426: 删除 nv_gw_stable (40005) 冗余容器

## Summary

HM2 的 `nv_gw_stable` (端口 40005) 容器零流量、零引用，删除并清理所有相关配置和产物。

## 背景

R40005 (2026-08-02) 创建了 `nv_gw_stable` 作为 40006 (nv_gw) 的"稳定版兜底"——当 40006
代码优化/参数调整时, 40005 保持旧版稳定配置。但实际:
- DB 查询 `host_machine LIKE '%stable%'` 返回 **0 行** — 从未有请求经过 40005
- cc4101 的 fallback 是 `ms_gw:40007`, 不是 40005
- hm4104/opclaw4103/cx4102/oc4105 无一指向 40005
- 40005 的独立源码副本 (`proxy/nv-gw-stable/gateway/`) 已 drift, 缺少 R2425 CPU spin 修复
- HM1 无此容器 (HM1 的 40005 是 legacy_cc_2, 完全不同)

## 删除内容

| 产物 | 状态 |
|---|---|
| 容器 `nv_gw_stable` (Docker container) | 停止+删除 |
| docker-compose.yml 中 `nv_gw_stable:` 服务段 (115 行) | 删除 |
| 源码目录 `/opt/cc-infra/proxy/nv-gw-stable/` (968K) | 删除 (sudo, .pyc root-owned) |
| 日志目录 `/opt/cc-infra/logs/nv_gw_stable/` | 删除 |
| 镜像 `cc-infra-nv_gw_stable:latest` (232MB) | 删除 |
| 备份 `docker-compose.yml.bak.R-del-40005` | 保留 |

## 验证

- `docker compose config --services` 列出 12 个服务, 无 nv_gw_stable ✓
- `grep nv_gw_stable docker-compose.yml` 返回 0 ✓
- 其余 11 个容器全部 `Up` ✓
- nv_gw /health ok, cc4101 /health ok ✓

## 关联

- R40005: 原始创建记录 [[r40005-stable-nv-gw-fallback]]
- R2425: nv_gw CPU spin 根治 (40005 源码副本缺少此修复, 已 drift) [[r2425-nv-gw-cpu-spin-buffer-drain]]
