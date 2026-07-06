# R782: HM2 nv_gw 配 socks 代理走美国出口 + 快速失败 timeout

## 摘要

HM2 nv_gw 容器 `NVU_PROXY_URL1-5` 全空, 5 个 NV key 全走容器默认出口 (国内 CMI IP
103.62.49.x 同 C 段), 被 NVCF 区域封锁 → 每请求 110-200s timeout 才失败. 配上
socks5h 代理走 mihomo 美国节点 (134.195.101.193) 后, K1/2/4/5 立即恢复 200,
K3 快速 403 (0.55s, cooldown 跳过). 三模型链路 (glm5_2_nv/dsv4p_nv/kimi_nv) 全部
端到端验证通过.

## 改前数据 (铁律: 改前必有数据)

### HM2 nv_gw 灾难路径 (每请求 110-200s 才失败)
```
41xx 适配器 → nv_gw (本地容器 connect OK)
  → K1 试 pexec 48s timeout (容器走国内 IP, NVCF 封)
  → K2 试 48s timeout (TIER_TIMEOUT_BUDGET_S=110s 只够 2 key)
  → all_tiers_exhausted → PEER-FB 到 HM1 (110s 后才触发)
  → PEER-FB relay BrokenPipeError (38-85s 后失败)
  → nv_gw 返 502 → 41xx 切 ms_gw → ms_gw 又 timeout
  → 总计 35-200s+ 才失败
```

### 根因彻查
1. **nv_gw 容器 `NVU_PROXY_URL1-5` 全空** → 5 key 全走 docker bridge → 宿主 NAT →
   国内 CMI IP (103.62.49.x)
2. NVCF 对 103.62.49.x 同 C 段区域封锁: K1/2/4/5 timeout 48s, K3 403 0.6s
3. mihomo 5 个 NV group (♻️US-NV-K1..K5) 名字是"日本东京05"等, 但实测出口全是
   103.62.49.x (CMI 中转, 不是真日本)
4. 切到 `🇺🇸美国01-0.1倍` 节点 → 出口 IP 变 134.195.101.193 (真美国 OVH) →
   **K1/2/4/5 立即 200, K3 仍 403 但 0.55s 快速失败**

### 容器内 socks 链路验证 (改前)
- nv_gw 容器能访问 `172.17.0.1:7894-7899` (mihomo mixed port, SOCKS5+HTTP 共用)
- 容器内 python pysocks 通过 `socks5h://172.17.0.1:7894` 测 NVCF pexec:
  K2/K4/K5 = 200 流式 OK, K3 = 403 0.55s
- mihomo 7894-7899 是 `type: mixed` (HTTP+SOCKS5 共用)

### K3 结论 (用户确认: 不调整 K3)
- K3 在 HM2 任何 IP (CMI + 美国01) 都 403, 在 HM1 日本 IP 200 OK — K3 有 IP 维度特殊性
- K3 403 是快速失败 (0.55s), 不浪费 timeout budget, nv_gw KEY_AUTHFAIL_COOLDOWN_S=60
  会跳过 K3
- 维持 R780 的 60s cooldown, 不改 K3 配置

## 参数表

| 参数 | 改前 | 改后 | 文件 |
|---|---|---|---|
| NVU_PROXY_URL1 | (空) | socks5h://172.17.0.1:7894 | docker-compose.yml |
| NVU_PROXY_URL2 | (空) | socks5h://172.17.0.1:7895 | docker-compose.yml |
| NVU_PROXY_URL3 | (空) | socks5h://172.17.0.1:7896 | docker-compose.yml |
| NVU_PROXY_URL4 | (空) | socks5h://172.17.0.1:7897 | docker-compose.yml |
| NVU_PROXY_URL5 | (空) | socks5h://172.17.0.1:7899 | docker-compose.yml |
| TIER_TIMEOUT_BUDGET_S | 110 | 40 | docker-compose.yml |
| NVU_PEER_FALLBACK_TIMEOUT | 90 | 25 | docker-compose.yml |
| mihomo ♻️US-NV-K1..K5 | 日本东京05等 (CMI 103.62.49.x) | 🇺🇸美国01 (134.195.101.193) | mihomo API 运行时切换 |

## 改动详情

### 改动 1: nv_gw compose env (核心修复)
文件: `/opt/cc-infra/docker-compose.yml` (HM2) nv_gw.environment 段

```yaml
- NVU_PROXY_URL1=socks5h://172.17.0.1:7894
- NVU_PROXY_URL2=socks5h://172.17.0.1:7895
- NVU_PROXY_URL3=socks5h://172.17.0.1:7896
- NVU_PROXY_URL4=socks5h://172.17.0.1:7897
- NVU_PROXY_URL5=socks5h://172.17.0.1:7899
- TIER_TIMEOUT_BUDGET_S=40
- NVU_PEER_FALLBACK_TIMEOUT=25
```

说明:
- `socks5h://` (h = 远程 DNS 解析), 让 mihomo 做 DNS, 避免容器本地 DNS 返亚太节点
  (记忆 nvcf-dns-region-routing-r705)
- 5 个端口对应 5 个 NV group (K1→7894→♻️US-NV-K1, ..., K5→7899)
- 每个 key 走独立 group/出口, 避免 same-IP rate limit (R580 设计)
- K3 走 7896, 即使 K3 403 也只影响 K3 自己, 不拖累其他 key

### 改动 2: mihomo 5 个 NV group 切到美国01 (网络层, 运行时)
```bash
SECRET="set-your-secret"
NODE="🇺🇸美国01-0.1倍 | 电信联通移动推荐"
for g in "♻️US-NV-K1" "♻️US-NV-K2" "♻️US-NV-K3" "♻️US-NV-K4" "♻️US-NV-K5"; do
  curl -X PUT -H "Authorization: Bearer $SECRET" -H "Content-Type: application/json" \
    http://127.0.0.1:9090/proxies/$g -d "{\"name\":\"$NODE\"}"
done
```

**注意**: 这是运行时切换, mihomo 重启后会丢. 后续需写 nv_proxy_selector.sh @reboot
持久化 (follow-up, 本轮先验证可行性).

### 改动 3: timeout 下调 (快速失败)
- `TIER_TIMEOUT_BUDGET_S=40`: K3 403 0.55s, K1/2/4/5 单次 pexec ~10-25s, 40s 够试
  1-2 个 key. 全挂后快速触发 PEER-FB (原 110s 才触发)
- `NVU_PEER_FALLBACK_TIMEOUT=25`: HM1 health 0.002s 200, relay 不该 38-85s.
  25s 够 NVCF 一次 pexec. 超时立即返 502 让 41xx 切 ms_gw

不改 41xx 适配器 timeout (opclaw4103 PRIMARY_STREAM_TIMEOUT_S=90, FALLBACK_TIMEOUT_S=120
维持), 因为 nv_gw 快速失败后 41xx 自然快速切 fallback.

## 改后验证 (铁律: 改后必有验证)

### 1. nv_gw health + env 生效
```
curl http://localhost:40006/health → 200 ok
docker exec nv_gw env | grep NVU_PROXY_URL → 5 个 socks5h 已配
docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET → 40
docker exec nv_gw env | grep NVU_PEER_FALLBACK_TIMEOUT → 25
```

### 2. nv_gw 直连三模型流式 (全部 200)
| 模型 | key | 出口 | 结果 | 耗时 |
|---|---|---|---|---|
| glm5_2_nv | K5 | socks 7899 | 200 流式 reasoning+content | 33s (thinking) |
| dsv4p_nv | K1 | socks 7894 | 200 "Hi there! 👋" | 13.8s |
| kimi_nv | K1 | socks 7894 | 200 流式 reasoning | - |
| dsv4p_nv (二次) | K2 | socks 7895 | 200 | 10.6s |

### 3. 41xx 适配器端到端 (全部 200)
| 适配器 | 模型 | key | 结果 | 耗时 |
|---|---|---|---|---|
| opclaw4103 | glm5_2_nv | K4 | 200 "1+1=2" 完整回答 | 5.1s |
| hm4104 | dsv4p_nv | K5 | 200 | 2.1s |
| oc4105 | kimi_nv | K2 | 200 | 1.2s |

### 4. nv_gw 日志确认
```
[12:14:02.2] [NV-KEY] tier=glm5_2_nv attempt 1/7: k4 → NVCF pexec ... via socks5h://172.17.0.1:7897
[12:14:07.3] [NV-SUCCESS] tier=glm5_2_nv k4 succeeded on first attempt
```
- 走 socks 代理 ✅
- `succeeded on first attempt` ✅ (不再 5 key 全 timeout)
- K3 在轮转中 403 后 cycle 到 K4 (cooldown 机制正常)
- PEER-FB 不再触发 (本地能成功)

## 预期效果

- HM2 nv_gw 每请求 110-200s timeout → 2-15s 成功 (或快速失败切 fallback)
- 41xx 适配器不再每请求等 35s 才切 ms_gw
- PEER-FB 不再频繁触发 (本地 socks 能成功)
- K3 维持 403 但快速失败 + cooldown, 不拖累整体

## 未做 / Follow-up

- **mihomo 持久化**: 5 个 NV group 切美国01 是运行时, mihomo 重启会丢. 需写
  nv_proxy_selector.sh @reboot 脚本 (下轮)
- **PEER-FB relay BrokenPipe 修复**: 本轮先做 env 改动, nv_gw 本地能成功后
  PEER-FB 不再触发, relay 修复可缓做. 若后续需要, 改 handlers.py _peer_fallback
  分离 connect/read timeout (参考 41xx R763)
- **HM1 同步**: 用户明确 HM1 暂不动, 本轮所有改动仅 HM2
- **K3**: 用户明确不调整, 维持 R780 60s cooldown

## 回滚

```bash
cd /opt/cc-infra
cp docker-compose.yml.bak.R782 docker-compose.yml  # 或手动改回
docker compose up -d nv_gw
# mihomo: 把 5 个 NV group 切回原节点 (可选, 不影响)
```

## 不改的东西 (铁律: 聚焦)

- HM1 任何配置 (用户: HM1 暂时不动)
- K3 key 配置 (用户: 不需要调整 K3)
- nv_gw/ms_gw 源码 (本轮只改 env, 不改源码)
- 41xx 适配器 (timeout 维持, nv_gw 快速失败后自然快速切 fallback)
- ms_gw (兜底后端, 不动)
