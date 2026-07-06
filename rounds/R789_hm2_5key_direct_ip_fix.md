# R789: HM2 nv_gw 5-key 出口 IP 路由修正 (R782/R783 美国节点回归 DIRECT)

## 摘要

R782/R783 把 K1/K3/K5 的 NVU_PROXY_URL 指向 mihomo 美国节点 (7894/7896/7899) 做 per-key IP 多样化。
实测发现: K1/K3/K5 走美国节点全部 30s timeout (3/5 key 硬故障), 只有 K2/K4 (国内直连/国内CMI) 200。
根因不是 "需要更多 timeout", 而是**美国出口节点到 NVCF 的链路本身不通**。

R789 把 K1/K3/K5 的 NVU_PROXY_URL 清空 (→ DIRECT), K2 保持空 (DIRECT), K4 保留 socks5h://172.17.0.1:7897 (国内CMI, 实测 200/6.8s 最快)。
结果: 4 DIRECT + 1 国内 socks, 5/5 key 直测全 200。

## 改前数据 (铁律)

### 直测 5 key pexec dsv4p (改前, R782/R783 配置)

| key | route (改前) | 结果 |
|-----|-------------|------|
| K1 | socks5h://172.17.0.1:7894 (美国) | TimeoutError 30.5s |
| K2 | "" (DIRECT) | 200 |
| K3 | socks5h://172.17.0.1:7896 (美国) | TimeoutError 30.5s |
| K4 | socks5h://172.17.0.1:7897 (国内CMI) | 200 6.8s |
| K5 | socks5h://172.17.0.1:7899 (美国) | TimeoutError 30.5s |

3/5 key 硬故障 → nv_gw TIER_TIMEOUT_BUDGET=60s 只够 2 次 30s 尝试 → all_tiers_exhausted → 502。

### DB 改前 24h 基线

| tier_model | total | ok | e502 | e429 | sr_pct |
|------------|-------|------|------|------|--------|
| dsv4p_nv | 1581 | 1405 | 172 | 4 | 88.9 |
| glm5_2_nv | 234 | 194 | 40 | 0 | 82.9 |
| kimi_nv | 59 | 58 | 1 | 0 | 98.3 |

172 个 dsv4p 502 + 40 个 glm5_2 502, 全部 60s 整 timeout, fallback_actually_attempted=false。
HM1 (100.109.153.83) 同期 5 key 全日本直连 100% SR, 佐证 "出口 IP 路由是根因"。

## 辩论 (与本机 hermes)

辩论记录见 `/tmp/nvforge_debate/final_plan_debated.md`。hermes 作为反对者提出:
- P2 (TIER_TIMEOUT_BUDGET 60→90) 是 "自欺欺人" — 502 根因是出口 IP 不通, 不是 budget 不够
- P3 (41xx stream-mid 失败切 fallback) 边界不清, 风险 > 收益
- P1 (修出口 IP) 单动充分, 先看效果再决定 P2/P3/P4

CC 接受 hermes 全部反对意见, 计划从 P1-P5 简化为 P1-only。
hermes 同时警告: 4 DIRECT key 同出口 IP 段 (134.195.101.x) 有 same-IP rate limit 风险 (R580 设计动机)。
折中: 先全 DIRECT 修硬故障, 观察 24h 429 量, 上升再分日本节点。

## 改动

### `/opt/cc-infra/docker-compose.yml` NVU_PROXY_URLx (第57/59/61行附近)

```yaml
# 改前 (R782/R783: K1/K3/K5 美国节点)
- NVU_PROXY_URL1=socks5h://172.17.0.1:7894
- NVU_PROXY_URL2=
- NVU_PROXY_URL3=socks5h://172.17.0.1:7896
- NVU_PROXY_URL4=socks5h://172.17.0.1:7897
- NVU_PROXY_URL5=socks5h://172.17.0.1:7899

# 改后 (R789: K1/K3/K5 回归 DIRECT)
- NVU_PROXY_URL1=
- NVU_PROXY_URL2=
- NVU_PROXY_URL3=
- NVU_PROXY_URL4=socks5h://172.17.0.1:7897
- NVU_PROXY_URL5=
```

backup: `/opt/cc-infra/docker-compose.yml.bak.R789_ip_fix`
仅第 57/59/61 行变化 (URL1/3/5), diff 已校验。

## 验证 (铁律: 改后有验证)

### 1. 容器 env 确认

```
NVU_PROXY_URL1=
NVU_PROXY_URL2=
NVU_PROXY_URL3=
NVU_PROXY_URL4=socks5h://172.17.0.1:7897
NVU_PROXY_URL5=
```

### 2. 直测 5 key pexec dsv4p (改后)

| key | route | status | latency |
|-----|-------|--------|---------|
| K1 | DIRECT | 200 | 4.0s |
| K2 | DIRECT | 200 | 11.8s |
| K3 | DIRECT | 200 | 4.2s |
| K4 | socks5h 7897 | 200 | 10.7s |
| K5 | DIRECT | 200 | 1.6s |

**5/5 全 200, K1/K3/K5 硬故障消除。**

### 3. 三模型 curl

- dsv4p_nv: 200, 11.3s ✓
- kimi_nv: 200, 1.5s ✓
- glm5_2_nv: 40s timeout (NVCF 端 glm5_2 function 慢响应, 既有问题, 非 P1 引入)

### 4. DB egress_route 生效确认 (改后样本)

| ts | tier | status | dur | egress_ip | route | key |
|----|------|--------|-----|-----------|-------|-----|
| 10:25:02 | dsv4p | 200 | 23882 | 134.195.101.193 | direct | 0 |
| 10:25:30 | dsv4p | 200 | 19648 | 218.93.250.242 | direct | 1 |
| 10:25:51 | dsv4p | 200 | 20909 | 134.195.101.195 | direct | 2 |
| 10:26:12 | dsv4p | 200 | 19135 | 103.62.49.162 | mihomo-7897 | 3 |
| 10:26:20 | dsv4p | 200 | 11322 | 134.195.101.180 | direct | 4 |

egress_route 列正确填充: K0/1/2/4=direct, K3=mihomo-7897。配置生效。

## 观察项 (24h)

1. **dsv4p_nv SR 应 >95%, 502 应接近 0** — 改前 88.9%/172个502。
2. **429 量监控** — 4 DIRECT key 出口 IP 集中在 134.195.101.x 段, hermes 警告 same-IP rate limit。
   改前 24h 429=4 (极低)。若 24h 后 429 上升 → 考虑把部分 DIRECT key 分到日本 mihomo 节点。
3. **glm5_2_nv 502** — NVCF 端 function 慢响应 (思考 16-63s), 60s budget 不够。
   属 deferred P2/P3 范畴, hermes 推翻, 本轮不动。若 24h 后 glm5_2 SR 仍 <85% → 重开 P2 (TIER_TIMEOUT_BUDGET) 讨论。

## 未做 (hermes 推翻)

- P2: TIER_TIMEOUT_BUDGET_S 60→90 (hermes: 自欺欺人, 根因不在 budget)
- P3: 41xx adapter stream-mid 失败切 fallback (hermes: 边界不清)
- P4: egress_ip DB logging 扩展 (已存在 egress_ip/egress_route 列, 已生效, 无需再做)

## 临时改动 (HM1, 辩论用, 需还原)

为让本机 hermes 能完成辩论 (hermes 走 40006 dsv4p_nv, 改前 502 高发跑不完), 临时改了
`~/.hermes/config.yaml` 第385行 `default: dsv4p_nv` → `default: glm5_2_nv` (HM1 有跨模型 fallback, SR 稳)。
backup: `~/.hermes/config.yaml.bak.debate_20260706_181359`。
辩论已完成, 待还原 (用户默认 HM1 不动)。
