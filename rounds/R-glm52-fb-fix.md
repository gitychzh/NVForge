# R-glm52-fb-fix: glm5_2_nv 多链路测试 + mode chain/fid/proxy 优化 + cc4101 primary→nv_gw

**日期**: 2026-08-04
**主机**: HM2

## 摘要

对 glm5_2_nv 做了全面多链路对比测试, 据此修复 3 个问题 + cc4101 重新指向 nv_gw/glm5_2_nv。

## 测试数据 (改前必有数据)

### pexec direct (3 fids × 5 keys)

| FID | SR | 说明 |
|---|---|---|
| fid1 b1b22d03 | **5/5=100%** (1.1-11.4s) | 唯一可用 |
| fid2 3b9748d8 | 0/5=0% (全60s超时) | 不可用 |
| fid3 b6029a96 | 0/5=0% (全60s超时) | 不可用 |

### pexec via US SOCKS5 (fid1, 5 keys × 9 proxies)

| Proxy | SR | avg | Proxy | SR | avg |
|---|---|---|---|---|---|
| 7901 | **100%** | 12.0s | 7896 | 60% | 5.0s |
| 7894 | 80% | 8.7s | 7899 | 60% | 14.6s |
| 7897 | 80% | 4.8s | 7902 | 40% | 10.3s |
| 7895 | 40% | 8.3s | 7904 | 40% | 9.7s |
| 7903 | 20% | 11.8s | | | |

### integrate via US SOCKS5 (5 keys × 9 proxies)

**0/45=0% SR** — 全部 timeout 或 SSL EOF。integrate 路径对 glm5.2 完全不可用。

### 问题诊断

1. **NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2** → k3 绑 fid2, k5 绑 fid3, 两者全 60s 超时
2. **NV_GLM52_MODE_CHAIN=pexec_us_rr,integrate_us_rr** → integrate 0% SR, 递进到 integrate 必失败
3. **NV_GLM52_KEY_MODE_BIND** 把 k2/k4 分配到 integrate_us_rr → 0% SR

## 变更

### 1. nv_gw (40006) glm52 config

| 参数 | 旧值 | 新值 |
|---|---|---|
| NV_GLM52_MODE_CHAIN | pexec_us_rr,integrate_us_rr | **pexec_us_rr** |
| NV_GLM52_KEY_FID_BIND | 0:0;2:1;4:2 | **0:0;1:0;2:0;3:0;4:0** (全 key→fid1) |
| NV_GLM52_KEY_MODE_BIND | 0:pexec_us_rr;1:integrate_us_rr;... | **空** (全走 pexec_us_rr) |
| NV_GLM52_RR_US_PROXIES | 7894,7895,7896,7897,7899 | **7901,7894,7897,7896,7899** (按 SR) |
| NV_GLM52_SINGLE_US_PROXY | 7897 | **7901** (100% SR) |
| NV_GLM52_KEY_PROXY_BIND | 0,2,4:7894,7896,7899;1,3:7895,7897 | **0:7901;1:7894;2:7897;3:7896;4:7899** |

### 2. cc4101 primary/fallback

| 字段 | 旧值 | 新值 |
|---|---|---|
| PRIMARY_UPSTREAM_URL | dsv4p_nv40066:40066/v1/messages | **nv_gw:40006/v1/messages** |
| PRIMARY_UPSTREAM_MODEL | dsv4p_nv | **glm5_2_nv** |
| FALLBACK_UPSTREAM_URL | dsvf0731_nv40666:40666/v1/messages | (不变) |
| FALLBACK_UPSTREAM_MODEL | dsv4f_nv | (不变) |

### 3. hm4104 + opclaw4103 fallback (前一轮已改)

- hm4104: fallback → nv_gw:40006/glm5_2_nv
- opclaw4103: fallback → nv_gw:40006/glm5_2_nv

## 验证

### nv_gw 40006 E2E (5 请求)

| # | HTTP | Time | Notes |
|---|---|---|---|
| 1 | 200 | 27.8s | |
| 2 | 200 | 21.0s | |
| 3 | 502 | 300s | NVCF 连接中断, buffer 重试后仍超 budget |
| 4 | 200 | 9.9s | |
| 5 | 200 | 45.6s | |

4/5=80% SR (fid1+最优代理)。

### cc4101 E2E

- `cc-glm5-2` → 200 OK, 5.8s, model=glm5_2_nv (primary nv_gw 成功)
- 日志确认所有 attempt 使用 fid=b1b22d03, 无 fid2/fid3 超时

### 日志验证

全部 NV-GLM52-ATTEMPT 行均 `fid=b1b22d03`, 每个 key 用各自绑定代理:
- k1→7901, k2→7894, k3→7897, k4→7896, k5→7899

## Commit
