# 优化铁律（NVForge）

> R569 起取消"双机交替优化/只改对端"机制。CC 直接维护两机，不再互相改、不再轮转角色。
> 自动轮询/执行脚本（`watch_and_next.sh` / `run_my_turn.sh`）已归档至
> `scripts/_archived_alt_optimize/`，systemd timer/cron 在 R569 已停。

1. **改前必有数据** — 日志/DB/metrics 支撑，不靠猜测
2. **改后必有验证** — 端到端测试，日志/DB 确认
3. **聚焦 `nv_gw`** — 只关心 40006 这条 NV 链路（及其直接关联的 nv_gw 网关）。
   legacy 40000–40005 cc 链路服务 CC 自身，不是目标但也不能破。
4. **CC 直接改两机** — HM1/HM2 均由 CC 直接编辑部署，无需通过对方执行
5. **网络问题走 mihomo** — HM1 `socks5://127.0.0.1:9090` / HTTP `127.0.0.1:7880`；
   HM2 docker daemon 已在 7880 之后
6. **所有修改写入仓库** — round 文件 + 源码归档，可追溯

## 评判标准
- 更少的报错
- 更快的请求
- 超低的延迟
- 稳定优先
