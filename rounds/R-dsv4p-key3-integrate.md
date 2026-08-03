# R-dsv4p-key3-integrate: 40066 dsv4p_nv key3 走 integrate.api, 其余 pexec

**Date**: 2026-08-03
**Host**: HM2 (opc2sname)
**Container**: dsv4p_nv40066 (port 40066)
**Commit**: (this commit)

## 背景

40066 (dsv4p_nv 独立容器) 之前全 5 key 走 pexec-only (`NV_INTEGRATE_MODELS=` 空).
用户要求: key3 (1-based, 0-indexed=2) 走 integrate.api + 美国 IP, 其余 4 key 走 pexec + 5 US IP.

## 修改

`/opt/cc-infra/docker-compose.yml` dsv4p_nv40066 service 新增 3 个 env:

```
- NV_KEY_INTEGRATE_KEYS=dsv4p_nv:3   # R838b: key3(1-based) 走 integrate, 其余 pexec
- NV_INTEGRATE_PROXY_URLS=socks5h://172.18.0.1:7902   # key3 专用 US IP (integrate 路径)
- NV_INTEGRATE_EGRESS_IPS=203.10.96.139                # key3 egress IP (对应 7902)
```

### 路由逻辑 (R838b per-key)

upstream.py:1745-1767 的 R838b 分支:
1. RR 轮转到 key3 (0-indexed=2) 时, peek 发现 key3 在 `nv_key_integrate_keys_for("dsv4p_nv")` 返回的 `[2]` 中
2. 进入 `_try_integrate_keys(key_filter=[2])`, 走 integrate.api.nvidia.com via socks5h://172.18.0.1:7902 (US IP 203.10.96.139)
3. 若 integrate 失败 (SSLEOF/timeout/429), 自动 fallback 到 `_try_tier_keys` pexec 全 key 轮转
4. key3 integrate 成功则 advance RR, 下次轮到 k4 走 pexec

## Before data (6h window, 40066 dsv4p_nv)

| key_idx | upstream     | reqs | ok  | avg_ms | avg_ttfb |
|---------|-------------|------|-----|--------|----------|
| 0       | nvcf_pexec  | 91   | 88  | 13906  | 10465    |
| 1       | nvcf_pexec  | 81   | 80  | 9385   | 8953     |
| 2       | nvcf_pexec  | 203  | 201 | 11883  | 10653    |
| 3       | nvcf_pexec  | 93   | 93  | 7800   | 7404     |
| 4       | nvcf_pexec  | 86   | 83  | 11244  | 10420    |

全 pexec, SR 96-100%, avg 7.8-13.9s.

## 部署验证

### 日志验证 (test request cycle)

```
k1 → pexec via 7900 → SUCCESS (11s)
k2 → pexec via 7901 → SUCCESS (2s)
k3 → R838B-LANE → integrate via 7902 → SSLEOFError (17s) → fallback pexec → k4 SUCCESS (3s)
k4 → pexec via 7903 → SUCCESS (3s)
k5 → pexec via 7904 → SUCCESS (3s)
```

R838b 路由正确触发: `RR peek=k3 → integrate (per-key)`. integrate 失败后自动 fallback pexec.
DB 也已记录 `nv_integrate` 流量 (egress_ip=203.10.96.139).

## 预期效果

- key3 每轮 RR 到时走 integrate.api (数据多样性 + 对比基线)
- integrate 失败自动回退 pexec, 不影响可用性
- pexec 4 key 分担流量, integrate 1 key 探路

## 备注: hm4104/opclaw4103→40066 协议

三 adapter 同为 `cc-adapter:latest` image, 代码相同, 配置不同:

| Adapter | Port | Endpoint | Format | Conversion? | PRIMARY |
|---|---|---|---|---|---|
| cc4101 | 4101 | /v1/messages | Anthropic | NO (R1705 passthrough) | nv_gw:40006/v1/messages |
| hm4104 | 4104 | /v1/chat/completions | OpenAI | NO (passthrough) | dsv4p_nv40066:40066/v1 |
| opclaw4103 | 4103 | /v1/chat/completions | OpenAI | NO (passthrough) | dsv4p_nv40066:40066/v1 |

- cc4101: Anthropic 格式透传到 nv_gw/40066 的 /v1/messages 端点 (nv_gw 内部做 Anthropic→OpenAI 转换)
- hm4104/opclaw4103: OpenAI 格式透传到 40066 的 /v1 (即 /v1/chat/completions) 端点 (无需转换)
- 三者都不做格式转换; 转换 (如需要) 由 nv_gw gateway 层处理
