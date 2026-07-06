# NVForge

> 双机对称的 LLM 网关基础设施，聚焦 `nv_gw → NVCF` 这一条链路的持续调优。
> 三 agent（hermes / openclaw / opencode）作为对等独立 APP 跑在两台主机上，
> CC 只做基础设施侧：构建并调优 agent 指向的本地网关，不干涉 agent 自身的模型选择。

**仓库**：`git@github.com:gitychzh/NVForge.git`（原名 `hermes_improve_self`，R787 起更名；
GitHub 对旧 URL 自动重定向，旧 clone 仍可正常 pull/push）

## 主机（双机对称）

| 角色 | 用户 | IP | ssh | hostname |
|---|---|---|---|---|
| **HM1**（本机） | `opc_uname` | `100.109.153.83` | `ssh -p 222` | `opcsname` |
| **HM2**（对端） | `opc2_uname` | `100.109.57.26` | `ssh -p 222` | `opc2sname` |

两机各自持有本仓库的 clone 与本地 `/opt/cc-infra` 的 docker-compose 栈。

## 铁律（见 `rule.md`）

1. **改前必有数据** — 日志/DB/metrics 支撑，不靠猜测
2. **改后必有验证** — 端到端测试，日志/DB 确认
3. **聚焦 `nv_gw`** — 只关心 40006 这条 NV 链路（legacy 40000–40005 cc 链路服务 CC 自身，不是目标但也不能破）
4. **网络问题走 mihomo** — HM1 `socks5://127.0.0.1:9090` / HTTP `127.0.0.1:7880`；HM2 docker daemon 已在 7880 之后
5. **所有修改写入仓库** — round 文件 + 源码归档，可追溯

> R569 起取消"双机交替优化/只改对端"机制，CC 直接编辑两机（仍数据支撑、仍验证、仍 commit）。
> 评判标准：更少报错、更快请求、超低延迟、稳定优先。

## 仓库结构

```
NVForge/
├── README.md                       # 本文件
├── rule.md                         # 优化铁律
├── CLAUDE.md                       # 给 Claude Code 的工作指南（最详尽）
├── docs/
│   └── agent_unified_nv.md         # 三 agent 统一接入 nv_gw 的历史设计
├── rounds/                         # 轮次记录（R568+ 现行机制；R1–R567 见 _archive_pre_r568/）
├── scripts/
│   ├── nvcf_func_monitor.py        # NVCF function 健康监控（每 10min，活跃）
│   └── nv_proxy_selector.sh        # 每 key 出口 IP 选择/兜底
├── deploy_artifacts/               # 现行机制源码快照（R699/R700/cx4102/R780/R782/R783）
├── upstream_current.py             # live 代理源码快照（live 在 /opt/cc-infra/proxy/nv-gw/）
└── logs/                           # 监控/运行日志（不入库）
```

## 实际部署位置

| 路径 | 内容 |
|---|---|
| `~/hm_ps/hermes_improve_self`（两机） | 本仓库 clone（目录名保留历史，未随仓库更名而改） |
| `/opt/cc-infra`（两机） | docker-compose 栈，9 个容器实跑 |

## 快速验证

```bash
cd ~/hm_ps/hermes_improve_self && git pull --ff-only origin main
curl -s http://localhost:40006/health
docker ps --filter name=nv_gw
```

详见 `CLAUDE.md`。
