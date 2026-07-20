# R2082: dsv4p_nv pexec 5 独立美国 socks5 (7900-7904) + cc2 resume 脚本 R2082 三修

**日期**: 2026-07-21 (HM2 only, 用户授权改 HM2 nv_gw config)
**铁律**: 改前必有数据 ✓ / 改后必有验证 ✓ / 聚焦 40006 ✓ / 写入仓库 ✓

## 背景

dsv4p_nv (hermes2 自优化走) 慢性低 SR。6h 数据: 304 req / 80 OK(26.3%?) → 实 60.5% SR
(80 OK + 13 429 + 103 all_tiers_exhausted + 2 abs_cap + 1 first_byte)。502 里 103/120 =
`all_tiers_exhausted` = 5 key 全打空。对比同窗 glm5_2_nv 90.6% SR (96 req)。

cc2 session `d87568cd` 反复被 CC SDK "no visible output" 看门狗中断, 深挖根因 =
hermes2 的 dsv4p_nv 429 风暴抢光共享 NV API key 配额 → glm5_2_nv pexec "Remote end
closed" → cc4101 primary 75s 超时 → CC SDK tool-use 死循环 → 65s 看门狗中断。

## 改前数据 (HM2, 6h 窗口, 改前)

| 指标 | dsv4p_nv | glm5_2_nv |
|---|---|---|
| 总请求 | 304 | 96 |
| SR% | 60.5% | 90.6% |
| 429 | 13 | 0 |
| 502 | 107 | 9 |
| 502 主因 | 103 all_tiers_exhausted | — |

## 根因深挖 (nv_gw 日志实证)

```
[01:48:41-46] dsv4p_nv: k3→429, k4→429, k5→429, k1→429, k2→429 (5s 内全 5 key)
[NV-TIER-FAIL] all 5 keys failed: 429=5
[NV-GLOBAL-COOLDOWN] all keys 429. Marking all cooling 180s (TIER_COOLDOWN)
→ 之后 180s 内: [NV-TIER-SKIP] all keys in cooldown → ABORT-NO-FALLBACK → 502
```

dsv4p_nv 走 pexec + DIRECT (HM2 单 IP) → NVCF 对单 IP 限流严 → 5 key 连环 429 →
180s 全局 cooldown → 期间全 502。

## 关键架构发现 (纠正认知)

1. **dsv4p_nv 早已是 pexec** (非 integrate), 走 `NVU_PROXY_URLS` (全局 per-key,
   config.py line 611 / upstream.py), 当前全空 = DIRECT。
2. **glm5_2_nv 走 `NV_GLM52_RR_US_PROXIES` (7894-7899, glm5_2 专用), 不碰
   NVU_PROXY_URLS** → 改 NVU_PROXY_URL1-5 只影响 dsv4p/kimi, 不影响 glm5_2_nv
   (结构隔离)。
3. KEY_MODE_BINDING 把 glm5_2_nv 全 5 key 绑 pexec_us_rr (实测 98/98 走 pexec 非
   integrate)。

## 改动 (备份 docker-compose.yml.bak.R2082 + mihomo config.yaml.bak.R2082)

### A. mihomo config 加 5 个新美国 listener (7900-7904)

- 5 个新 proxy-group `♻️US-DSV-K1..K5` (type:select, use:nv-us-provider, 空组,
  同 K1-K5 格式)。
- 5 个新 listener 7900-7904, 各 proxy 绑一个 ♻️US-DSV-K*。
- mihomo API PUT 各 group 选 "0.1倍" CDN 美国节点 (避开 K1-K5 已用 IP 193/195/180):

| port | group | 节点 | 出口 IP |
|---|---|---|---|
| 7900 | ♻️US-DSV-K1 | 🇺🇸美国06-0.1倍 | 134.195.101.180 |
| 7901 | ♻️US-DSV-K2 | 🇺🇸美国07-0.1倍 | 134.195.101.188 |
| 7902 | ♻️US-DSV-K3 | 🇺🇸美国08-0.1倍 | 203.10.96.139 |
| 7903 | ♻️US-DSV-K4 | 🇺🇸美国02-0.1倍 | 134.195.101.194 |
| 7904 | ♻️US-DSV-K5 | 🇺🇸美国05-0.1倍 | 134.195.101.120 |

**坑**: "三网推荐"圣何塞直连 IP (134.195.101.x) 的 vless 握手被 reset (connection
reset by peer), 只有 CDN 域名节点 (pq.us*.globals-download.com, "0.1倍"系列) 能通。
同 K1-K5 用同类节点。

### B. compose env: NVU_PROXY_URL1-5 + NVU_EGRESS_IP1-5

```
NVU_PROXY_URL1=socks5h://172.18.0.1:7900  # k1->7900->180
NVU_PROXY_URL2=socks5h://172.18.0.1:7901  # k2->7901->188
NVU_PROXY_URL3=socks5h://172.18.0.1:7902  # k3->7902->139
NVU_PROXY_URL4=socks5h://172.18.0.1:7903  # k4->7903->194
NVU_PROXY_URL5=socks5h://172.18.0.1:7904  # k5->7904->120
NVU_EGRESS_IP1=134.195.101.180
NVU_EGRESS_IP2=134.195.101.188
NVU_EGRESS_IP3=203.10.96.139
NVU_EGRESS_IP4=134.195.101.194
NVU_EGRESS_IP5=134.195.101.120
```

`docker compose up -d nv_gw` (env 改需 up -d 非 restart)。

### C. cc2 resume 脚本 R2082 三修 (备份 .bak.R2082)

(详见 [[r2082-cc2-resume-novisible-output-inject]] 记忆, 此处简述)
1. 检测上一轮 jsonl "no visible output" → 本轮注入"别 Read /tmp 死循环"铁律。
2. tee 进程替换 → `2>>` 重定向 (cc2-stuck 同款坑, cc2 恢复前置已修)。
3. setsid 降级 fallback。
cc2 已恢复 (systemctl --user enable --now cc2-resume.timer), 首轮 01:47 跑通, setsid
不再失败 (parse_errors.log 无新增)。

## 改后验证 (重启后 6min, dsv4p_nv)

| 指标 | 改前(6h) | 改后(6min) |
|---|---|---|
| SR% | 60.5% | **100%** (10/10) |
| 429 | 13 | 0 |
| 502 | 107 | 0 |
| all_tiers_exhausted | 103 | 0 |
| 429 连环日志 | 频繁 | **完全消失** |
| egress IP | 空(DIRECT) | 5 个不同美国 IP 全填 |

5 egress IP 各不同 (180/188/139/194/120), 全 mihomo-7900..7904。429 连环 → 全局
180s cooldown → 502 链路彻底断。

## 预期效果

- dsv4p_nv 5 key 各走不同美国 IP → NVCF 端 IP 级限流分散 (k1 走 IP-A 429 ≠ k2
  走 IP-B 429) → 不再连环 5-key 全 429 → 不再触发全局 180s cooldown。
- hermes2 自优化不再因 429 风暴拖垮共享 key 配额 → glm5_2_nv pexec 不再被抢 →
  cc4101 primary 不再 75s 超时 → CC SDK 不再 tool-use 死循环 → cc2 不再被
  "no visible output" 中断 (d87568cd 同款中断链根治)。

## 未做 / 后续

- **P1.5 节点持久化**: mihomo API 选节点是运行时状态, mihomo 重启会丢。需写
  nv_proxy_selector 类似启动脚本 (@reboot crontab 或 systemd) 重选 5 节点, 或改
  group 默认 proxy。当前靠本地 nv-us-provider 缓存兜底, 但 provider 远程拉取 403
  (订阅可能过期, 待观察)。
- **P2**: 修 hermes2 resume 脚本 backoff (N 连续 DEGRADED → interval 30min) +
  cc4101 fallback 路径 stall 检测 (BUG 2: fallback 路径 is_primary=False 不记
  breaker)。
- **P3**: cc4101 _try_primary timeout 改 drain 已到达 buffer 替代 conn.close()
  (BUG 1)。
- **HM1 同步**: 用户决定先只改 HM2 验证, HM1 暂不动 (HM1 是日本 IP 非 HM2 美国代理
  结构)。

## 关联

- [[r2082-cc2-resume-novisible-output-inject]] — cc2 resume 三修 + 为何 cc2 没发现
  BUG 的三重原因 (冻结+停摆+观测错位)
- [[hermes2-biginput-breaker-firstfight]] — hermes2 首仗诊断
- [[hermes2-deploy-bugs-fixed]] — hermes2 三个部署 bug
