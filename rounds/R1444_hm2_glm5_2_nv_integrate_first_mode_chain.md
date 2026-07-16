# R1444: HM2 nv_gw glm5_2_nv mode chain 改 integrate 优先 + cc4101 header 60s

## 背景 (改前数据)

2026-07-16 ~11:50 CST HM2 CC 死循环: 近1h 17×502 + 1×200, 每 502 跑满 120127ms.

根因链:
1. NVCF pexec 对 glm-5.2 间歇降级 (5 美国IP 全 SSLEOFError/empty200/timeout).
2. R1421 把 glm5_2_nv 全押单一 mode `pexec_us_rr`, MODE-STALL-RESET 反复重置回 mode0, 永远等不到成功.
3. chain budget 300s 耗尽 → ALL-TIERS-FAIL → 502. cc4101 120s header timeout 先断 → CC 重试 → 420s 大循环死锁.
4. NVCF API 本身可达 (`/v1/models` 正常), 是 pexec 调用 glm-5.2 端点降级, 非网络故障.

## 改动 (改 HM2, 破铁律例外 — 用户明确授权)

### 改动1: nv_gw mode chain 从单 mode 改为 5 mode 递进 (integrate 优先)

`/opt/cc-infra/docker-compose.yml` line 65:
```
- NV_GLM52_MODE_CHAIN=integrate_us_rr,integrate_us_single,pexec_direct,pexec_us_rr,pexec_us_single
```
(原 R1421 单 mode `pexec_us_rr`; R1444 改 5 mode 递进, integrate 优先因测速证明 integrate 全绿)

### 改动2: NV_GLM52_SINGLE_US_PROXY 7894→7897

line 66: `NV_GLM52_SINGLE_US_PROXY=socks5h://172.18.0.1:7897`
(7897=134.195.101.193 测速最快 3.82s avg, 原 7894=203.10.96.139 AU IP 最慢 6.73s)

### 改动3: cc4101 PRIMARY_HEADER_TIMEOUT 25→60

line 167 (新增 env): `PRIMARY_HEADER_TIMEOUT=60`
(原源码默认 25s 小请求档; 实测 nv_gw integrate_us_rr k4 成功需 32s(12:32:13 success), cc4101 25s 提前打断 < nv_gw 成功 → 502 误判. 60s 覆盖 integrate 典型成功时间)

### 改动4: 重置 glm52_mode_idx=0

`/opt/cc-infra/logs/nv_gw/glm52_mode_idx.json` 写 `{"idx":0}` + `docker compose up -d --force-recreate nv_gw`
(让新请求从 mode0=integrate_us_rr 开始, 不残留旧 idx=2=pexec_direct)

## 改前测速数据 (绕过 nv_gw 直接 curl 测 NVIDIA, 2026-07-16 ~12:25)

integrate channel (`/v1/chat/completions`) 全 5 proxy×5 key 全绿:

| proxy | egress | 5key avg tot |
|---|---|---|
| 7897 | 134.195.101.193 | 3.82s ← 最快 |
| 7896 | 134.195.101.195 | 3.83s |
| 7895 | 134.195.101.194 | 4.51s |
| 7899 | 134.195.101.180 | ~4.7s |
| 7894 | 203.10.96.139(AU) | 6.73s ← 最慢 |

pexec 未测完 (2min timeout), 但历史日志证明 pexec 降级期全 empty200/SSL_EOF.

## 改后验证

- nv_gw `restored idx=0` (=integrate_us_rr), mode chain 5 modes 加载.
- cc4101 `PRIMARY_HEADER_TIMEOUT=60` 生效.
- 测试请求经 cc4101 (anthropic /v1/messages, cc-glm5-2, "say hello in 3 words"):
  **HTTP 200 ttfb=3.55s** → `Hello to you!` ✅
- nv_gw 侧 `NV-GLM52-SUCCESS tier=glm5_2_nv mode=integrate_us_rr k4 succeeded`.
- 0 个 BREAKER-OPEN (熔断器恢复).
- CC 真实大请求未验证 (HM2 claude 进程已退出, 无流量).

## 残留/已知风险

- CC 大请求 (msgs=299,tools=30) 未实测 (进程已退出). 下次 CC 启动后需观测.
- 流式中途 stall (memory cc-mid-response-cc4101-stall) 未在本轮处理, 是独立问题.
- NVCF pexec 降级期 integrate 也可能偶发 stall, 但 integrate_us_rr 全绿期间应稳定.
- HM1 nv_gw 源码 (R1416 双 deadline) 与 HM2 不同步, 8 文件 md5 差异, 未本轮同步.

## 铁律

本轮破例改 HM2 (用户明确授权: "加多 mode fallback 改 HM2 nv_gw" + "测最快 deploy 远程").
备份: docker-compose.yml.bak.R1444.
