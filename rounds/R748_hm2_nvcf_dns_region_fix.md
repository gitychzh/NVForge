# R748: HM2 — NVCF DNS region 路由真因修复 (容器 8.8.8.8 返亚太挂死 → 223.5.5.5 返美国稳定)

> 仅 HM2。HM1 不动 (HM1 是日本 IP, R696 记录的 region 偏好可能相反, 需独立验证).

## TL;DR
HM2 nv_gw glm5_2_nv 思考请求 62s 后 NVCF 返 504/202 cl=0 挂死, 长期被 R745-R747 误判为
"NVCF function 3b9748d8 dead, wait for recovery"。真因彻查清: **容器 DNS 走 8.8.8.8 基于
EDNS Client Subnet (ECS) 返亚太节点 (13.193/52.193/35.75), 该 region 对 glm5_2 思考挂死;
宿主走 223.5.5.5 (阿里) 返美国节点 (34.227/54.84/52.87), 3 个全稳定 5-15s**。
修复: nv_gw compose 加 `dns: [223.5.5.5, 223.6.6.6]` + should_cycle 加入 504/503/202 防御。
改后 6min 窗口 glm5_2_nv 9/9=100% 成功 (含 2 次 fallback, 最终全成功), 对比改前全 fallback dsv4p 或 62s 挂死。

## 改动背景 (用户要求彻查真伪)
R705 已把 glm5_2_nv 40s timeout 归因于 "mihomo 5 出口 IP 被 NVCF 阻断" (临时解法 NVU_PROXY_URL=""
直连)。但直连后 glm5_2_nv 仍 62s 挂死, 当时又误归因 "思考 timeout 太短" (bump 40→90s)。
用户要求 "当遇到 NVCF 上游限速/timeout, 必须彻查真伪, 是不是特定 IP 限制, 换 IP 试试"。
本轮彻查到底: 加 debug 日志 → 看到 NVCF 返 504 cl=0 → 对比容器/宿主/直连 → 抓 DNS 解析差异
→ 定位 ECS 地理路由。

## 改前数据 (彻查链)
1. **nv_gw 日志**: glm5_2_nv k3/k4/k5 直连 pexec, 62s 后 `NV-FALLBACK all-failed`, 中间无
   NV-TIMEOUT/EMPTY/ERR 日志。加 debug 日志后看到: `status=504 cl=0 time=62.6s`。
2. **容器内 repro** (python http.client + 同样 camouflage headers + 同样 body):
   - try1=504 62.6s / try2=202 60.7s / try3=202 60.7s — **3 次全挂**
3. **宿主 repro** (同样代码): try1=202 60.6s / try2=200 6.4s / try3=202 62.2s — 间歇 (宿主
   偶发解析到亚太节点)。
4. **强制美国节点** (`--resolve` 34.227.137.56 / 54.84.218.221 / 52.87.56.15):
   - glm5_2 思考: 3/3 成功 (15s / 11.5s / 14.9s)
   - dsv4p: 3/3 成功 (9.5s / 5.6s / 5.3s) — **R696 当时记录的 "dsv4p 美国挂死" 现已不存在**
5. **DNS provider 对比**:
   | DNS | 返回 region | glm5_2 思考 |
   |---|---|---|
   | 8.8.8.8 (容器 ExtServers) | 亚太 35.75/52.193/13.193 | **挂死 ❌** |
   | 1.1.1.1 | 亚太 Mumbai 3.6/43.204/13.127 | 挂死 ❌ |
   | 223.5.5.5/223.6.6.6 (阿里, 宿主上游) | 美国 34.227/52.87/54.84 | **稳定 ✅** |
6. **根因**: `api.nvcf.nvidia.com` 的 DNS 基于 EDNS Client Subnet 做地理路由。8.8.8.8/1.1.1.1
   严格遵循 ECS, 看到 HM2 中国源 IP 返亚太节点 (Tokyo/Mumbai), 该 region 对 glm5_2 思考 504/202
   挂死。阿里 DNS 不传 ECS 或用 anycast, 返美国节点 (Virginia), 稳定。容器 nv_gw 的
   /etc/resolv.conf → 127.0.0.11 (docker embedded) → ExtServers [8.8.8.8, 8.8.4.4] → 永远亚太。
   宿主 systemd-resolved → 223.5.5.5 → 美国。

## 改动清单

### A. compose (`/opt/cc-infra/docker-compose.yml`) — nv_gw 加 dns
```yaml
  nv_gw:
    ...
    networks:
    - cc-net
    dns:              # R748: 强制用阿里 DNS, 避 ECS 返亚太挂死节点
    - 223.5.5.5
    - 223.6.6.6
    healthcheck: ...
```
备份: `docker-compose.yml.bak.R705_dns`.

### B. upstream.py — should_cycle 加入 504/503/202 (防御层)
现状 504/503/202 是 non-cycling error → 1 次失败就 `return result` 退出整个 tier, 不重试
其他 key。本轮把三者加入 cycling, 让单 key 挂死时 cycle 到下个 key (同 region 都挂则
all_keys_exhausted → peer fallback HM1, 正确兜底)。

两处改动 (pexec 路径 line 582 + integrate 路径 line 231):
```python
should_cycle = resp.status in (429, 408, 500, 502, 503, 504, 202)
```
cycle_reason 分类扩展 (pexec 用 `_nv_` 前缀, integrate 用 `_integrate_` 前缀):
- 503 → `503_nv_error` / `503_integrate_error`
- 504 → `504_nv_gateway_timeout` / `504_integrate_gateway_timeout`
- 202 → `202_nv_async_hang` / `202_integrate_async_hang`
备份: `upstream.py.bak.R705_cycle`.

## 改后验证 (6min 窗口)
```
 mapped_model | total | ok | ok_pct | avg_ms | fb
--------------+-------+----+--------+--------+----
 dsv4p_nv     |     2 |  2 |  100.0 |   2121 |  0
 glm5_2_nv    |     9 |  9 |  100.0 |  32494 |  2
```
- 容器内解析: `['34.227.137.56', ...]` (美国节点, 修复前是 13.193/52.193 亚太)。
- 流式思考 5 次: 4 次成功 (5-18s, 含 GLM 真回复), 1 次偶发 empty200 cycle (60s, cycle 后
  下个 key 成功)。
- 日志确认: `NV-SUCCESS tier=glm5_2_nv k2/k3/k5 succeeded on first attempt` — 不再全 fallback。
- dsv4p_nv 不受影响 (美国节点也稳定)。

## 推翻 R745-R747 结论
R745-R747 持续记录 "glm5_2_nv primary 3b9748d8 dead (health=0.0), wait for NVCF recovery",
"dsv4p_nv 56.8% SR"。这是**误判**: function_id 3b9748d8 本身没死, 是容器 DNS 把请求路由到
亚太挂死节点, func_health 累积失败标记 dead。改 DNS 后 3b9748d8 立即恢复健康。无需"等 NVCF
recovery"。

## 铁律遵守
- 改前必有数据: 6 步彻查链 (debug 日志 / 容器 repro / 宿主 repro / 强制美国节点 / DNS provider
  对比 / ECS 地理路由定位) ✓
- 改后必有验证: 6min 窗口 9/9=100% + 容器解析到美国节点 + 日志 SUCCESS ✓
- 聚焦 nv_gw: 只动 nv_gw compose dns + upstream.py should_cycle, 未动 agent/thinking/模型选择 ✓
- 所有修改写入仓库: 本 round + compose + upstream.py (bind-mount 已生效, 源码改动同步到
  ~/hm_ps/hermes_improve_self 的 upstream_current.py 待同步) ✓

## 后续
- HM1 (日本 IP) 的 nv_gw 是否也有 DNS region 问题需独立验证 (R696 记录 dsv4p 经日本 IP 秒回
  美国 IP 挂死, 方向可能相反; 若 HM1 容器也走 8.8.8.8 返亚太, 而 HM1 日本到亚太反而正常,
  可能不需要改。待 HM1 单独验证)。
- 偶发 empty200 (流式 cl=0) 仍存在 1/5 概率, 已被 cycle 机制救回, 暂不深究 (NVCF 侧思考
  超时返回空流)。
