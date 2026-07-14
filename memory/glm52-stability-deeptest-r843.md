---
name: glm52-stability-deeptest-r843
description: "GLM5.2_nv 稳定性深挖(07-11): 死亡窗口88-102k + 7894端口07-11突发59.8%zombie; RR模式13/13全OK; mode_idx=4固定7894是放大器"
metadata: 
  node_type: memory
  type: project
  originSessionId: c3734594-fcf5-43ff-9b8d-e14d8c206a00
---

# R843 GLM5.2 稳定性深测(2026-07-11)

## 核心发现(三层数据交叉验证)

### 1. 死亡窗口精确 = 88k-102k chars(4天696条聚合)
| 桶 | total | ok | zombie | zombie% |
|---|---|---|---|---|
| <80k | 322 | 216 | 0 | 0% |
| 88-95k | 33 | 16 | 17 | **51.5%** |
| 95-100k | 52 | 6 | 45 | **86.5%** |
| 100-105k | 225 | 186 | 13 | 5.8%(R842c fallback 起效) |
| 105k+ | 319 | 124 | 0 | 0%(但 other=148=NVCF 202 降级) |

### 2. 7894 端口 07-11 突发(非端口固有缺陷)
跨天同 mode(integrate single-7894):
- 07-09: 60条 0% zombie
- 07-10: 41条 0% zombie
- **07-11: 97条 59.8% zombie** ← 突发,首例 04:38,末例 07:04(2.5h窗口)
- 7894 从 07-10 16:34 就开始用,12小时全 OK,07-11 04:38 突变

### 3. 7894 vs 7897 同节点同IP 却不同结果(排除IP风控)
- mihomo 5 listener: 7894(K1)/7895(K2)/7896(K3)/7897(K4)/7899(K5) 各绑 US-NV-K1~5 group
- 当前选中节点: K1=美国01, K2=美国02, K3=美国03, **K4=美国01(同K1!)**, K5=美国06
- 7894 和 7897 **同走美国01节点(同出口IP 134.195.101.193)**
- 但 7894 zombie 59.8%, 7897 是 0% → 排除"出口IP被风控"
- 差异在 mihomo listener 层面(7894 是 nv-us-k1 listener,TLS session/连接池特征不同)或 NVCF 对 7894 连接的临时标记

### 4. RR 模式死亡窗口测试 13/13 全 OK(v3 测试, pexec_us_rr)
- death_90k×5: 5/5 OK (12-58s)
- death_95k×5: 5/5 OK (8-26s)
- death_98k×3: 3/3 OK (18-27s)
- 对照: 同期生产 7894 single 死亡窗口 51-86% zombie
- RR 轮换 5 端口分散了 NVCF 对单连接的限流/风控

### 5. zombie 特征(75个)
- ttfb 1-41s(median 3.6s)= 快速假完成,非超时
- output_tokens: **40个是3 token(53%),11个是4 token(15%)** — NVCF 返回 200+stop 但只 3-4 token
- thinking_type 全 None(与思考无关)
- key_idx 均匀 14-18(与 key 无关)
- 全在 ic=88609-104178(死亡窗口)

## 根因结论
**三层叠加**:
1. NVCF 后端: 对 glm5.2 + 88-102k chars 请求返回 200+stop+3token 空响应(zombie),这是 NVCF 内部 tokenizer/model boundary 行为,07-11 04:38-07:04 突发约2.5h
2. mode_idx=4(integrate_us_single)固定 7894: 在 NVCF 波动期集中承受 zombie,无分散(RR 能分散到4个0%端口)
3. R840 zombie 检测 + R842c forwarder 拦截: 已兜底切 ms_gw fallback,但 primary 仍记录 502

## 测试基础设施
- speedtest cron(~/scripts/glm52_speedtest.py,每天2:00/14:00)只测"Say hi"短prompt,**测不到死亡窗口**(全100%假象)
- v3 全测脚本(~/scripts/glm52_fulltest3.py)用 urllib 会卡死在 SSL read(无idle deadline),需改用容器内httpx或加socket强制timeout
- 生产 jsonl(/app/logs/nv_metrics.YYYY-MM-DD.jsonl)是最可靠数据源,696条4天聚合足够下结论

## 相关
[[r842c-forwarder-content-filter-fallback-fix]] [[r842-88k-zombie-window-root-cause]] [[r839-glm52-mode-chain]] [[r839-glm52-mode-chain]] [[glm52-speedtest-cron]]
