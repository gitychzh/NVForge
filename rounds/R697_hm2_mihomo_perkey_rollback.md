# R697 (HM2): 试图配 mihomo per-key 分流 → 失败回滚

## 背景

R696 根治 dsv4p_nv 502 后, 注意到 HM2 的 `NVU_PROXY_URL1..5` 全空 (mihomo per-key 代理未配),
5 个 NV key 共用 HM2 宿主 IP。假设这会触发 NVCF IP 级限流 (k1 偶发 429)。

R696 记忆里曾判定 docker-compose.yml 的 R_direct 注释"美国代理节点对 dsv4p 反挂死"是过时误判
(因为 R696 已证 dsv4p 挂死真因是 integrate+stream_options+thinking)。
本轮目标: 配 HM2 mihomo per-key 分流, 5 key 各走不同美国出口 IP, 消除 IP 限流。

## 改前数据

- mihomo 5 个 NV listener 端口 7894/7895/7896/7897/7899 全部 LISTEN (config.yaml)。
- 但 5 个 `♻️US-NV-K1..K5` proxy-group 全部 `type:select` 且 `now` 都指向同一节点
  `🇺🇸美国洛杉矶08 | 三网推荐` → 5 端口出口 IP 全是 `203.10.96.139` (未分流)。
- mihomo config 注释提到有 `nv_proxy_selector.sh` 脚本会按 NV 延迟选 top5 分配 K1-K5,
  **但脚本不存在** (find 全盘无), crontab/systemd timer 也无。5 group 无人管理, 退化到首节点。
- mihomo `nv-us-provider` health-check url = `https://integrate.api.nvidia.com/v1/models`
  (R696 已证对 deepseek-v4-pro 挂死的端点) → health-check 全失败 → 节点延迟数据缺失。

## 实施步骤

1. 用 mihomo API 测 8 个候选美国节点延迟 (url=NV models):
   `🇺🇸美国01-0.1倍` ~198ms, `02` ~190ms, `03` ~226ms, `04` ~192ms, `05` ~197ms (全活)。
   圣何塞/洛杉矶/阿什本节点 timeout 或 error。
2. 用 mihomo API `PUT /proxies/{name}` 把 K1-K5 分别选到 `美国01..05-0.1倍` 5 个不同节点。
3. 验证 5 端口出口 IP 已分流: 7894→134.195.101.193, 7895→.194, 7896→.195, 7897→.197, 7899→.120。
4. 容器内 SOCKS5 → 5 端口 → 5 不同 IP 全通 (python socks 测 api.ipify.org)。
5. 容器内经 5 key+5 proxy 打 NVCF pexec `/v2/nvcf/pexec/models` 全 404 (路径不对但连接 OK, key 有效)。
6. 备份 compose: `docker-compose.yml.bak.R697`。
7. 改 compose `NVU_PROXY_URL1..5` = `http://host.docker.internal:7894..7897,7899` (K5 用 7899 非 7898)。
8. `docker compose up -d nv_gw` 重启, env 生效, health OK。

## 改后验证 (失败)

6 次 openclaw-style dsv4p_nv 请求 (复杂 prompt "用中文写一段50字关于春天的描写" + reasoning_effort=medium):
**6/6 全 60s 超时**。

docker logs 关键链:
```
[23:28-23:30] 5 次 74f02205 (primary) attempt, 全 40s NVCFPexecTimeout
  → func_health 标记 74f02205 unhealthy → 切 8915fd28
[23:31-23:33] 5 次 8915fd28 (fallback) attempt, 全 40s timeout
  → func_health 切回 74f02205 (health 恢复)
[23:34] 再切回 74f02205, 继续 timeout
```

每次 attempt 都经 `http://host.docker.internal:789x` (mihomo), 连接建立 OK (无 socks/connect error),
但 NVCF pexec 40s 不出首字节。`is_thinking_req=True` (client 发 reasoning_effort) → 走 40s timeout 路径
(NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40, R696 已调), 40s 仍不够。

## 根因 (R696 记忆修正)

**R_direct 注释"美国代理节点对 dsv4p 反挂死"是对的, 不是过时误判。**

R696 只在 HM1 (日本直连 IP) 验证 dsv4p 秒回 (1.8-4.9s 无思考参数 / 9.7-27.3s openclaw-style)。
经 mihomo **美国出口 IP** 时, 74f02205 复杂 prompt 推理仍 >40s → 全 timeout。
不是 mihomo/socks5 连接问题 (连接建立 OK), 是 NVCF 后端对美国 IP 的 dsv4p 推理慢/挂。

HM2 mihomo 的 `nv-us-provider` filter = `美国|圣何塞|阿什本|洛杉矶` (全美国节点),
无日本节点可选。要解决 HM2 5key 共 IP 429 需换日本节点, 非换美国节点。

## 回滚

`docker-compose.yml` `NVU_PROXY_URL1..5` 全部回空 (注释标注 R697 rollback 原因)。
`docker compose up -d nv_gw` 重启。验证 3 次 openclaw-style 请求: 18s/3s/8s 全成功。
HM2 恢复 R696 后状态, 无 regression。

## 未解决 (留待后续轮次)

- HM2 5 NV key 共用宿主 IP (中国 IP), 偶发 NVCF IP 限流 429。
- 解法方向: mihomo `nv-us-provider` filter 改含日本节点 (但当前机场 pq-provider 日本节点是否对 NVCF dsv4p 友好未知, 需测)。
- 或: 接受 HM2 直连现状 (R696 后 502 <10%, 429 偶发可容忍)。
- mihomo `nv_proxy_selector.sh` 脚本不存在 (config 注释提到的), 5 group 无自动化管理。
- mihomo `nv-us-provider` health-check url 用 integrate 端点 (已挂死), 应改 pexec 或 models。

## 修改清单

| 文件 | 修改 | 状态 |
|---|---|---|
| HM2 `/opt/cc-infra/docker-compose.yml` | `NVU_PROXY_URL1..5` 空→mihomo 7894-7899 | **已回滚到空** |
| HM2 `/opt/cc-infra/docker-compose.yml.bak.R697` | 备份 | 保留 |
| HM2 mihomo K1-K5 proxy-group 节点选择 (API 层) | 选到 5 不同美国节点 | **未持久化** (mihomo config 未改, 重启 mihomo 会丢; profile.store-selected=true 可能持久但未验证) |

## 教训

1. R696 的"美国节点对 dsv4p 反挂死是过时误判"判断本身才是误判 — R_direct 注释来自实测, 在未复测美国节点前不应推翻。
2. 改前数据要覆盖目标路径 (HM2 美国 mihomo), 不能用 HM1 日本直连的数据外推到 HM2 美国代理。
3. 失败实验也要记 round 文件 + 回滚 + 更新记忆, 避免下轮重蹈。
