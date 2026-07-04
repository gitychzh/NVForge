# R698 (HM2): mihomo per-key 分流改用日本节点 (R697 回滚后的正确解法)

## 背景

R697 试图配 HM2 mihomo per-key 分流, 5 key → 5 个美国节点 → 5 个不同美国出口 IP, 消除 5key 共 IP
的 NVCF 429 限流。失败: 74f02205 经美国 IP 复杂 prompt 全 40s timeout, 6/6 失败。回滚到全直连。

R697 教训: docker-compose.yml R_direct 注释"美国代理节点对 dsv4p 反挂死"是对的。HM1 日本直连 dsv4p
秒回 (R696 验证 1.8-27.3s), 但经美国 IP 74f02205 复杂 prompt >40s。

本轮思路: HM2 mihomo 改用日本节点 (而非美国节点), 5 key 各走不同日本出口 IP, 既分流又保持日本 IP
对 dsv4p 的友好性。

## 改前数据 (R698 定位)

### 关键对比测试 (容器内, 5 key 各经一节点打 74f02205 dsv4p 非流式)

| 节点 | 出口 IP | 结果 |
|---|---|---|
| 🇯🇵日本东京05 (port 7892) | 103.62.49.154 | HTTP 200, 5.8s ✅ |
| 🇺🇸美国01-K1 (port 7894) | 134.195.101.193 | 40s timeout ❌ |

决定性证据: 74f02205 经日本 IP 秒回, 经美国 IP 挂死。R_direct 注释正确, 解法是换日本节点。

### HM2 mihomo 现状 (R697 已发现)

- 5 个 `♻️US-NV-K1..K5` proxy-group, `type:select`, `use: nv-us-provider`。
- `nv-us-provider` filter = `美国|圣何塞|阿什本|洛杉矶` (纯美国, 无日本节点)。
- health-check url = `https://integrate.api.nvidia.com/v1/models` (R696 证挂死端点)。
- `nv_proxy_selector.sh` 脚本不存在 (config 注释提到的), 5 group 无自动化管理, 全退化到首节点。

## 实施

### 1. 改 mihomo config (`~/.config/mihomo/config.yaml`)

- `nv-us-provider.filter`: `美国|圣何塞|阿什本|洛杉矶` → 加 `|日本东京|AWS日本`
- `nv-us-provider.health-check.url`: `https://integrate.api.nvidia.com/v1/models` → `https://api.nvcf.nvidia.com/v1/models`
  (integrate 端点对 dsv4p 挂死, 改 pexec models 端点)
- 备份: `config.yaml.bak.R698`
- 重载: `curl -X PUT .../configs?force=true` (API reload, 204 OK)

### 2. 用 mihomo API 把 K1-K5 选到 5 个不同日本节点

| group | 节点 | 出口 IP |
|---|---|---|
| K1 (7894) | 🇯🇵日本东京05-0.1倍 | 103.62.49.154 |
| K2 (7895) | 🇯🇵AWS日本01 | 103.62.49.138 |
| K3 (7896) | 🇯🇵AWS日本02 | 103.62.49.162 |
| K4 (7897) | 🇯🇵日本东京04-0.1倍 | 103.62.49.178 |
| K5 (7899) | 🇯🇵日本东京03-0.1倍 | 103.62.49.170 |

5 个不同日本 IP (103.62.49.x), 实现分流。

### 3. 容器内验证 5 key 经 5 日本节点打 74f02205

K1 8.1s, K2 19.4s, K3 11.9s, K4 7.5s, K5 25.4s — 5/5 全 200 ✅。

### 4. 改 HM2 docker-compose.yml

`NVU_PROXY_URL1..5` 从全空 → `http://host.docker.internal:7894..7897,7899` (K5 用 7899)。
备份: `docker-compose.yml.bak.R698`。`docker compose up -d nv_gw` 重启, env 生效, health OK。

## 改后验证

### 端到端 (openclaw-style, 流式, reasoning_effort=medium, 复杂 prompt)

6/6 全成功 (16/20/20/23/17/16s)。
mihomo + nv_gw 双重启后 3/3 全成功 (18/6/4s), 配置持久稳定。

### DB (nv_requests)

- 23:55-23:59 (R698 改后): 8 条 dsv4p_nv 全 200, 5 key (idx 0-4) 都正常轮转使用。
- 23:40-23:43 (R697 失败期对照): 6 条 502 all_tiers_exhausted。
- DB `now()` 时区偏移 (16:02 UTC vs 最新 ts 23:59 UTC), 不影响数据, 待另轮修 DB 时区。

### 持久化验证

mihomo `profile.store-selected: true` + cache.db, `systemctl --user restart mihomo` 后
K1-K5 仍保持 5 个日本节点, 5 端口出口 IP 不变。select 选择持久化。

## 修改清单

| 文件/对象 | 修改 | 状态 |
|---|---|---|
| HM2 `~/.config/mihomo/config.yaml` | filter 加日本, health-check url 改 pexec | 已改 + 备份 |
| HM2 `~/.config/mihomo/config.yaml.bak.R698` | 备份 | 保留 |
| HM2 mihomo API K1-K5 select | 选到 5 日本节点 | 持久化 (store-selected) |
| HM2 `/opt/cc-infra/docker-compose.yml` | `NVU_PROXY_URL1..5` 空→7894-7899 | 已改 + 备份 |
| HM2 `/opt/cc-infra/docker-compose.yml.bak.R698` | 备份 | 保留 |
| HM1 | 无改动 (HM1 日本直连 R696 后已稳定) | — |

## 未解决 (留待后续)

- HM2 `nv_proxy_selector.sh` 脚本仍缺失, K1-K5 是手动选的固定 5 节点。若某日本节点掉线,
  mihomo `type:select` 不会自动切换 (不像 `url-test`)。可考虑改 group type 或补脚本。
- mihomo `nv-us-provider` 现在混含美国+日本节点, health-check 会给所有节点打延迟数据,
  但 K1-K5 手动选日本节点不受影响。若将来要自动化, 需按延迟选日本子集。
- DB `now()` 时区与 ts 不一致, 待另轮排查。
- HM1 仍全直连 (日本 IP), 未配 mihomo 分流 — HM1 单 IP 但日本直连 dsv4p 友好, 暂不需要。

## 教训

1. R697 失败的根因不是"不该用 mihomo", 而是"用了美国节点"。换日本节点后 mihomo per-key 分流成功。
2. 改前数据要覆盖目标路径的具体节点地区, "美国节点对 dsv4p 挂死"和"日本节点对 dsv4p 友好"是两个事实。
3. mihomo `type:select` group 的 `use: provider` 受 provider filter 限制, 选 filter 外节点会被拒 (400)。
4. mihomo `profile.store-selected: true` 让手动 select 持久化跨重启, 不需额外脚本固化。
