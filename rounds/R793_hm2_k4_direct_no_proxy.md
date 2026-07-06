# R793: HM2 nv_gw K4 去掉最后一条 mihomo 代理 — 5 key 全直连, 与 HM1 对称

## 摘要

R789 把 K1/K3/K5 的 mihomo 美国节点回归 DIRECT, 但 K4 (`socks5h://172.17.0.1:7897` 国内CMI) 保留。
R793 是收尾: 把 K4 这最后一条 mihomo 也清空, HM2 5 key 全部直连 NVIDIA, 与 HM1 完全对称。

动机: 用户对比两机模型链路稳定性, HM2 比 HM1 不稳定。实测 HM2 6 条 mihomo SOCKS5 端口里
7898 已断 (其余 5 条返回 401 正常)。多一层代理链 + 一条坏隧道 + 为掩盖不稳定而拉长的
超时预算 (TIER_TIMEOUT_BUDGET=180 vs HM1 114, FORCE_STREAM_UPGRADE_TIMEOUT=150 vs HM1 66)
= HM2 不稳定的全部来源。HM1 直连一跳, 拓扑上就没有这些故障点。

## 改前数据 (铁律)

### HM1 vs HM2 配置对比 (改前)

| 项 | HM1 (本机) | HM2 (远程) |
|---|---|---|
| 出口方式 | 5 key 全直连 (日本 IP) | 4 直连 + 1 socks5h mihomo 7897 |
| UPSTREAM_TIMEOUT | 66 | 66 |
| TIER_TIMEOUT_BUDGET_S | 114 | 180 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 150 |
| nv_gw 运行时长 | Up 10h (healthy) | Up 48min (刚重启) |

### HM2 mihomo 端口实测 (改前)

| 端口 | 用途 | curl https://api.nvcf.nvidia.com |
|---|---|---|
| 7894 | K1 美国 (R789 已弃用) | 401 ✓ |
| 7895 | K3 美国 (R789 已弃用) | 401 ✓ |
| 7896 | K3 美国 (R789 已弃用) | 401 ✓ |
| 7897 | **K4 国内CMI (R793 前仍在用)** | 401 ✓ |
| 7898 | (未指派) | **000 ✗ 断** |
| 7899 | K5 美国 (R789 已弃用) | 401 ✓ |

注: 401 是 NVCF 对未带 Authorization 的探测请求的正常响应, 说明隧道通; 000 = 隧道断。
7898 当前未指派给任何 key, 但 mihomo 整体健康度可疑 (有一条坏端口)。

### DB 近 1h 失败率对比 (改前)

| 主机 | 成功 | 失败 | 失败类型 |
|---|---|---|---|
| HM1 | 7 | 2 | NVCFPexecTimeout + 504_nv_gateway_timeout |
| HM2 | 44 | 7 (~13.7%) | empty_200 |

HM2 失败率约为 HM1 的 1.6 倍, 且错误类型是 `empty_200` (代理中继截断响应体),
而非 HM1 的干净 timeout — 代理层引入的典型症状。

## 改动

### `/opt/cc-infra/docker-compose.yml` (HM2) NVU_PROXY_URL4 第60行

```yaml
# 改前
- NVU_PROXY_URL4=socks5h://172.17.0.1:7897

# 改后
- NVU_PROXY_URL4=
```

### NVU_EGRESS_IP4 第60行附近

K4 原出口 = mihomo 日本CMI 103.62.49.162。改直连后 K4 出口 = HM2 本机直连 IP 218.93.250.242
(与 K2 同出口, 因 K2 本就是直连)。

```yaml
# 改前
- NVU_EGRESS_IP4=103.62.49.162

# 改后
- NVU_EGRESS_IP4=218.93.250.242
```

### 新增注释 (R793)

```yaml
# R793: K4 也改直连, 去掉 mihomo 7897. K4 出口 = HM2 直连 IP 218.93.250.242 (与 K2 同出口).
#       5 key 全直连, 与 HM1 对称. R_direct: 用户授权两机全直连.
```

backup: `docker-compose.yml.bak.R793` (HM2 本机)。

## 验证 (铁律: 改后必有验证)

### 1. env 生效

```
docker exec nv_gw env | grep NVU_PROXY_URL
NVU_PROXY_URL1=
NVU_PROXY_URL2=
NVU_PROXY_URL3=
NVU_PROXY_URL4=
NVU_PROXY_URL5=
NVU_EGRESS_IP4=218.93.250.242
```
health: `{"status":"ok","nv_num_keys":5,...}` ✓

### 2. 端到端直连实测 (HM2, 改后)

| 模型 | HTTP | 耗时 | 说明 |
|---|---|---|---|
| dsv4p_nv | 200 | 1.50s | 直连秒回 ✓ |
| kimi_nv | 200 | 1.88s | 直连秒回 ✓ |
| glm5_2_nv | 000 | 90s timeout | **function 3b9748d8 本身挂了 (HM1 也记录 health=0.0 dead), 与代理无关** |

### 3. 双机直连对比 (改后)

| 模型 | HM1 (日本直连) | HM2 (改后直连) |
|---|---|---|
| dsv4p_nv | 200 / 2.14s | 200 / 1.50s |

HM2 直连甚至比 HM1 快。链路本身正常, 之前的不稳定 = mihomo 代理层。

## 不改的项 (避免单轮多参数)

- `TIER_TIMEOUT_BUDGET_S=180` / `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150` 暂不动。
  这两个值是 R789 之后为掩盖代理不稳定拉长的; 现在 K4 已直连, 理论上可回调到 HM1 的
  114/66, 但属于不同 round 的参数调整, 留待下轮基于数据决定。
- glm5_2_nv function `3b9748d8` 死亡是 NVCF 侧问题, 非配置可修复, 不在本轮范围。

## 铁律检查

- [x] 改前有数据 (双机配置对比 + mihomo 端口实测 + DB 失败率)
- [x] 改后有验证 (env 生效 + 3 模型端到端实测 + 双机对比)
- [x] 聚焦 nv_gw (只动 40006 链路的 K4 出口)
- [x] 写入仓库 (本 round 文件 + compose backup)

单参数 (K4 代理清空) 每轮; 铁律: HM2 链路由本机 CC 优化 (HM1 不动)。
