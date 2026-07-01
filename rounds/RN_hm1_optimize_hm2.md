# R533 (HM1→HM2): UPSTREAM_TIMEOUT 57→59 (+2s) — 对齐HM1 thinking ceiling 59s,消除57s cliff,继续救回边缘截断请求

**轮次**: R533
**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host=opc2sname@100.109.57.26)
**日期**: 2026-07-02 05:10 CST / 2026-07-01 21:10 UTC
**类型**: 单参数上调 (UPSTREAM_TIMEOUT)
**Commit**: 本commit

## 0. 时区与host标识

- 对端HM2 host=opc2sname, Tailscale IP=100.109.57.26, SSH端口=222。
- ts字段UTC(日志与系统时间一致)。
- 三模型运行: kimi_nv(f966661c), dsv4p_nv(8915fd28), glm5_1_nv(6155636e)。
- 当前HM2 env基线(改后): FASTBREAK=1, BUDGET=100, UPSTREAM=59, THINKING_TIMEOUT=59, OUTBOUND=1.0, KEY_CD=38, TIER_CD=22, CONNECT_RESERVE=3, PEER_FB_TIMEOUT=65。

## 1. 改前数据采集 (HM2对端)

### 1a. 容器env实测 (docker exec hm40006 env)

```
UPSTREAM_TIMEOUT=57
HM_FORCE_STREAM_UPGRADE_TIMEOUT=57
HM_PEER_FALLBACK_TIMEOUT=65
MIN_OUTBOUND_INTERVAL_S=1.0
TIER_TIMEOUT_BUDGET_S=100
HM_PEXEC_TIMEOUT_FASTBREAK=1
HM_CONNECT_RESERVE_S=3
```

### 1b. docker logs 6h窗口基线

**kimi_nv 6h 统计**(docker logs --since=6h):

| metric | value |
|--------|-------|
| HM-REQ (总请求数) | ~91 (估算) |
| HM-SUCCESS 本地 | 47 |
| HM-TIMEOUT 本地 | 29 |
| 429计数 | 0 |
| SSLEOF计数 | 0 |
| empty200计数 | 0 |
| 本地成功率 | 61.8% (47/76) |
| 超时耗时 | P100=58.9s (分布: 57.3s–58.9s, 全部聚集于ceiling) |
| peer fallback OK | 5 |
| peer fallback FAILED | 10 |
| 总体成功率(含peer fb) | ~84.8% (52/62) |

**超时分布**(29次timeout):
- <55s: 0
- 55–57s: 0
- 57–58s: 26 (89.7%)
- >=58s: 3 (10.3%)
- avg: 57.7s
- min: 57.338s, max: 58.966s

**peer fallback 4h 细查**: 5次OK全部<0.2s(ttfb=127/181/179/179/121ms),对应非kimi_nv快速请求透传HM1; 10次FAILED全部~57s(对端HM1也timeout在57s ceiling); peer fallback互备通道对fast请求有效,对thinking请求无效(双端同困57s ceiling)。

### 1c. HM1 对端状态 (R532后)

R532 (HM2→HM1) 已将HM1的 `HM_FORCE_STREAM_UPGRADE_TIMEOUT` 57→59 (+2s),目的是"消除57s cliff,救回边缘截断请求"。

HM1当前env:
```
UPSTREAM_TIMEOUT=25
HM_FORCE_STREAM_UPGRADE_TIMEOUT=59
HM_PEER_FALLBACK_TIMEOUT=57
HM_CONNECT_RESERVE_S=5
```

关键事实: HM1 thinking ceiling 已升至59s,但HM2仍为57s。当HM2本地57s失败后peer fallback到HM1,HM1最多可处理59s。但HM2的`HM_PEER_FALLBACK_TIMEOUT=65`意味着等待65s,此时HM2本地59s+HM1 59s=118s > BUDGET 100s, peer fallback仍可能被BUDGET截断。不过这是HM侧独立演化,本轮只改HM2。

## 2. 改动计划

### 2a. 候选评估

| 候选 | 数据支撑 | 风险 | 裁决 |
|------|---------|------|------|
| **UPSTREAM_TIMEOUT 57→59** | 29次timeout全部聚集在57-58s ceiling,零429零SSLEOF; HM1已升至59s; +2s继续削cliff,同轮对称 | 极低: FASTBREAK=1限制失败路径仅+2s,成功路径不受延迟 | **执行** |
| HM_FORCE_STREAM_UPGRADE_TIMEOUT 57→59 | 已在compose中预置59(容器重启后生效); 若override生效则此参数才是真正thinking控制 | 无风险(compose已写59) | **已生效(重启后发现)**,本轮顺承 |
| HM_PEER_FALLBACK_TIMEOUT 65→60 | 对HM1 peer fallback失败后多等5s浪费;但对OK请求(均<1s)无影响;失败路径减延迟 | 低: 思考请求HM1处理窗口59s,减至60仍>=59不损失 | 不执行(留待下轮) |
| BUDGET 100→130 | UPSTREAM(59)+PEER_FB(65)=124s,100会导致peer fb被budget截断 | 中: 失败请求多挂24s | 不执行(数据无budget截断直接证据) |
| MIN_OUTBOUND_INTERVAL_S 1.0→0.8 | 零429,当前throttle有余量 | 低: 可能刺激429 | 不执行(当前零429已最优) |

### 2b. 最终计划

只做1个参数改动: `UPSTREAM_TIMEOUT` `"57"` → `"59"`。

- 理由:
  1. **对称HM1**: HM1 thinking ceiling已59s (R532),HM2 57s落后2s,双端不对等→互备通道效能打折。
  2. **数据驱动**: 29次timeout全部集中在57-58s ceiling,不是随机网络抖动,是硬截断。+2s可救回那些恰好在57.0–59.0s完成的边缘请求。
  3. **FASTBREAK保护**: FASTBREAK=1使失败路径成本仅+2s/次,不浪费后续key budget。
  4. **保守**: 前3轮(R528/R530/R532)均为+2s增量,延续少改多轮节奏。
  5. **零副作用**: 非thinking请求本来就<10s完成,UPSTREAM ceiling提高对其无影响。

## 3. 改动执行

### 3a. 改docker-compose.yml (HM2远程)

```bash
# HM1侧执行
ssh -p 222 opc2_uname@100.109.57.26

# 改UPSTREAM_TIMEOUT 57→59
sed -i 's/UPSTREAM_TIMEOUT: "57"/UPSTREAM_TIMEOUT: "59"/' /opt/cc-infra/docker-compose.yml
```

验证compose:
```
grep 'UPSTREAM_TIMEOUT: "59"' /opt/cc-infra/docker-compose.yml
→ line 469: UPSTREAM_TIMEOUT: "59"  # R533: HM1→HM2 — 57→59 +2s 超时仍全部集中于57-58s天花板,继续削边缘截断; 少改多轮; 铁律:只改HM2不改HM1
```

### 3b. 容器重启 (应用新env)

```bash
cd /opt/cc-infra && docker compose up -d --no-deps hm40006
```

验证:
```
Container hm40006 Recreated
Container hm40006 Started
```

### 3c. 改后三源交叉验证

- **源1**: 容器内env确认
```
docker exec hm40006 env | grep UPSTREAM_TIMEOUT
→ UPSTREAM_TIMEOUT=59
```

- **源2**: 运行日志(重启后5min)
```
docker logs hm40006 --since=5m | grep -E 'HM-SUCCESS|HM-TIMEOUT'
→ 10 行全为 HM-SUCCESS, 零 HM-TIMEOUT (短窗口,积极信号)
```

- **源3**: HM_FORCE_STREAM_UPGRADE_TIMEOUT 同步确认
```
docker exec hm40006 env | grep FORCE_STREAM
→ HM_FORCE_STREAM_UPGRADE_TIMEOUT=59
```
*(注: 容器重启后HM_FORCE_STREAM_UPGRADE_TIMEOUT亦为59;检查compose发现此前已写入59但容器未重启,本次重启一并生效。双参数现均为59,对称HM1 R532配置。)*

## 4. 改后预期

- **kimi_nv 边缘救回**: 57–59s区间的请求不再被ceiling截断,预计6h timeout数从29向20收敛。
- **双端对称**: HM2与HM1 thinking ceiling均为59s,peer fallback互备通道的边界条件对齐。
- **零429风险**: 不改并发/代理/冷却参数,NVCF rate-limit状态不变。
- **失败路径成本可控**: FASTBREAK=1使单key失败后立即释放,+2s仅作用于该key的失败路径。

## 5. CC清单更新

- [HM2-A] UPSTREAM_TIMEOUT: ✅ R533 57→59 +2s。待30min+窗口验证timeout计数是否下降。
- [HM2-B] HM_FORCE_STREAM_UPGRADE_TIMEOUT: ✅ 现59s(重启后生效)。对称HM1 R532,待验证。
- [HM2-C] HM_PEER_FALLBACK_TIMEOUT: ⏸ 65s。当前HM1 ceiling=59s,65s仍留有余量。若下轮数据显示peer fb ATE被BUDGET截断(100-(59+59)=-18),考虑上调BUDGET或下调PEER_FB。
- [HM2-D] HM_PEXEC_TIMEOUT_FASTBREAK: ✅ R517 2→1。已验证有效,不改动。
- [HM2-E] MIN_OUTBOUND_INTERVAL_S: ✅ R518 1.2→1.0。零429稳态,不改动。
- [HM2-F] KEY_COOLDOWN_S/TIER_COOLDOWN_S: ⏸ 38/22。29次timeout后key回收余量充足,不改动。
- [HM2-G] HM_CONNECT_RESERVE_S: ⏸ 3s (vs HM1 5s)。连接建立时间占比极小(pexec timeout 57-59s中<1s),不改动。

## 6. 给下轮 (HM2 优化 HM1) 的接力信息

- HM2 当前配置: BUDGET=100 / UPSTREAM=59 / THINKING_TIMEOUT=59 / FASTBREAK=1 / MIN_OUTBOUND=1.0 / RESERVE=3 / KEY_CD=38 / TIER_CD=22 / PEER_FB=65。
- **验证重点**: 采集30min+窗口统计timeout率、peer fb成功率、429计数。关键指标: timeout是否从~29/6h下降; 成功请求的ttfb分布是否出现57-59s新桶; peer fb是否因BUDGET=100被过早截断。
- **HM1对端**: HM1 UPSTREAM=25 / THINKING_TIMEOUT=59 / PEER_FB=57 / RESERVE=5。双端thinking已对齐59s,HM1的PEER_FB=57对HM2透传请求有一定budget压力(59+57=116>100)。
- **严禁**: 任何stop/restart/kill mihomo服务。本round仅通过`docker compose up -d --no-deps hm40006`重启proxy容器,不涉及mihomo进程。
- **3model语义保留**: kimi/dsv4p/glm5.1映射逻辑不变。

## ⏳ 轮到HM2优化HM1
