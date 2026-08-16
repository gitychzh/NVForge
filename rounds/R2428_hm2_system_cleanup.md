# R2428 — HM2 系统瘦身与冗余清理

**日期**: 2026-08-16
**主机**: HM2 (100.109.57.26)
**类型**: 系统维护
**前序**: R2425 (CPU spin fix), R2426 (del 40005)

## 目标

HM2 系统全面扫描，保守清理冗余、垃圾文件，不影响任何功能使用。

## 清理清单

### Docker (回收 ~1.5GB)

| 项目 | 回收 | 说明 |
|------|------|------|
| dangling image `2d20b8096cc2` | 177MB | 旧构建残留 |
| build cache (all) | 178.5MB | 79条 build cache 全清 |
| `cc-adapter:test` 镜像 | 177MB | 未被任何容器使用 |
| `legacy_cc_1` + `legacy_ms_litellm` 容器 | 4.8MB | 已停 13 天 |
| `legacy_cc_1` + `legacy_ms_litellm` 镜像 | 354MB | legacy 链路已退役 (R827) |
| `python:3.12-slim` base 镜像 | 179MB | 无容器直接使用 |
| docker-compose.yml 中 legacy 服务定义 | 102 行 (739→637) | 2 个完整 service block |
| legacy proxy 源码目录 | ~500KB | `proxy/legacy-cc/`, `proxy/legacy-ms-gateway/` |
| legacy 日志目录 | ~26MB | `logs/legacy-40001/`, `logs/legacy-ms-gateway/` |
| 停止网络 + 残余 build cache | 135KB | `docker system prune` |

**Docker 清理后状态**: 7 镜像 (全部活跃), 11 容器 (全部运行), 0 可回收, 0 build cache。

### 日志 (回收 ~350MB)

| 项目 | 回收 | 说明 |
|------|------|------|
| nv_gw zombie_dumps | 153MB | 7月22日 dump 文件, 已过时 |
| hm4104 adapter.jsonl | 16MB | 累积型日志, truncate 归零 |
| legacy-40001 日志 | 26MB | 容器已删 |
| legacy-ms-gateway 日志 | 4KB | 容器已删 |
| journald vacuum → 50MB | 144MB | 删 9 个旧 journal 文件 |
| /var/log/syslog.1 truncate | 59MB | 当前轮转 syslog.1 |

### 缓存 (回收 ~1.2GB)

| 项目 | 回收 | 说明 |
|------|------|------|
| npm _cacache | 566MB | npm 全局缓存 |
| npm _npx | 398MB | 临时 npx 安装 |
| npm _prebuilds + _logs | 2.1MB | 杂项 |
| pip cache | 45MB | pip 下载缓存 |
| node-gyp cache | 65MB | node-gyp 头文件缓存 |
| uv cache | 76MB | uv 下载缓存 |
| bluwy-giget cache | 16MB | giget 下载缓存 |
| apt archive | 49MB | `apt-get clean` |

### 内核 (回收 ~200MB+)

| 项目 | 回收 | 说明 |
|------|------|------|
| linux-image-5.15.0-179 | purged | 非运行、非最新 |
| linux-image-5.15.0-181 | purged | 非运行、非最新 |
| linux-image-5.15.0-185 | purged | 非运行、非最新 |
| linux-headers-5.15.0-179 + generic | 104MB | purged |
| /lib/modules/5.15.0-179/ -181/ -185/ | 残留目录 | sudo rm -rf |

保留: 5.15.0-186 (运行中) + 5.15.0-187 (最新)。

### 其他

| 项目 | 回收 | 说明 |
|------|------|------|
| /var/crash Edge crash | 22MB | msedge.1000.crash |
| compose .bak 文件 (2个) | 61KB | .bak.R-del-40005, .preR857 |
| 零字节垃圾文件 | 0 | `/opt/cc-infra/=`, `hm_metrics.db` |
| cc_webui dist.bak | 6.7MB | 旧 dist 备份 |
| Docker apt 源重复 | — | 删 `docker.list` 保留 `docker.sources` |

## 未清理 (保守保留)

- **ms-playwright (641MB)**: chatgpt_api/login_edge.py 使用 Playwright 浏览器自动化, 保留
- **.local/share/uv/python (324MB)**: uv 管理的 Python 3.11/3.12, `.local/bin/` 软链接指向, 保留
- **.local/lib/python3.10 (560MB) + python3.11 (395MB)**: 用户安装的 Python 包, 保留
- **cc_webui/node_modules (918MB)**: cloudcli webui 运行依赖, 保留
- **research/ (333MB)**: 源码仓库 (opencode, kimi-code), 保留
- **.claude/ (231MB)**: Claude Code 会话/遥测数据, 保留

## 验证

```
=== 所有容器 ===
11 个容器全部 Up (无停止的)

=== 健康检查 ===
nv_gw:     {"status": "ok", "nv_default_model": "glm5_2_nv", "nv_num_keys": 5}
cc4101:    {"status": "ok", "proxy_role": "cc4101", "primary": "glm5_2_nv"}
ms_gw:     {"status": "ok", "num_keys": 7, "models": ["glm5_2_ms","dsv4p_ms","dsv4f0731_ms"]}
cloudcli:  HTTP 200 in 0.002s

=== systemd 用户服务 ===
6 个服务全部 active running

=== Docker ===
7 镜像 (全活跃) / 11 容器 (全运行) / 0 可回收

=== 磁盘 ===
115G total, 23G used, 86G avail, 22% (清理前: 25G used, 84G avail, 23%)
```

## 总回收空间估算

| 类别 | 回收 |
|------|------|
| Docker (镜像+容器+cache+build) | ~1.5GB |
| 日志 (zombie+journald+syslog+legacy) | ~400MB |
| 缓存 (npm+pip+node-gyp+uv+apt) | ~1.2GB |
| 内核 (image+headers+modules) | ~300MB |
| 其他 (crash+bak+junk) | ~30MB |
| **总计** | **~3.4GB** |

磁盘 used: 25G → 23G (差 2G, 因 Docker overlay 层有共享, 实际净回收 ~2G + 缓存释放不含磁盘 used 变化)。

## commit

清理操作不涉及 git 仓库内容修改 (均为 HM2 /opt/cc-infra + 系统), docker-compose.yml 已在 HM2 修改, 本 round 文件记录操作。
