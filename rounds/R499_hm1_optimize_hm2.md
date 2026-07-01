# R499 (HM1→HM2): TIER_TIMEOUT_BUDGET_S 100→115 — 启用第3attempt空间, 减少budget_break失败

**轮次**: R499
**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2sname)
**日期**: 2026-07-01 12:21 UTC (CST 20:21)
**类型**: 单参数优化 (TIER_TIMEOUT_BUDGET_S +15s)
**Commit**: 3745a4c (R498, HM2→HM1, k4→mihomo) → 本commit (R499)

## 0. 时区与host标识

- 对端HM2 host_machine 标识=`opc2sname`(hostname实测=opc2sname ✓)。
- NVCF function: 6155636e-8ca8-4d9a-b4e5-4e8d231dfd3f (z-ai/glm-5.1)。

## 1. 改前数据采集 (HM2 对端, host_machine=opc2sname)

### 1a. 容器env (8参数+5 URL)
```
UPSTREAM_TIMEOUT=48
TIER_TIMEOUT_BUDGET_S=100
MIN_OUTBOUND_INTERVAL_S=2.5
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=22
HM_SSLEOF_RETRY_DELAY_S=1.0
HM_PEXEC_TIMEOUT_FASTBREAK=5
HM_CONNECT_RESERVE_S=8
HM_MIN_ATTEMPT_TIMEOUT_S=8
HM_NV_PROXY_URL1=http://host.docker.internal:7894  k1→mihomo
HM_NV_PROXY_URL2=""  k2→direct
HM_NV_PROXY_URL3=""  k3→direct
HM_NV_PROXY_URL4=""  k4→direct
HM_NV_PROXY_URL5=""  k5→direct
```
- /health=200 OK (port 40006): hm_num_keys=5, nvcf_pexec_models=[glm5.1_hm_nv]

### 1b. Docker logs 最近1h窗口 (改前基线)
| 指标 | 数值 |
|------|------|
| 总请求 (HM-REQ) | ~108 |
| 成功 (HM-SUCCESS) | 93 |
| TIER-FAIL | 14 |
| ALL-TIERS-FAIL | 14 |
| 429 (1h tier-fail) | 0 |
| timeout pattern | 2×~48s per fail |

### 1c. 核心问题量化
- 每个tier-fail: attempt1 timeout@~48s + attempt2 timeout@~44s = ~92.5s elapsed
- BUDGET=100, CONNECT_RESERVE=8 → 检查: 92.5 + 8 = 100.5 > 100 → break
- **第3attempt空间=0** (R496已精确量化)
- 失败根因=NVCF server-side pexec timeout, 非key级(5键per-hit全100%SR)

## 2. 优化方案

### 2a. 理论依据
- R496勘定包: "升BUDGET100→115双赢估算(SR+4.3pp→85.1%, 总耗时-1837s)"
- 100→115: +15s budget extension
- 2×48s timeout = 96s → 剩余 115-96 = 19s
- 19s > CONNECT_RESERVE(8) → 第3attempt可触发
- 第3attempt可用时间窗口 ≈ 19s (受budget限制), p50=8-15s < 19s, 大量请求可在窗口内成功

### 2b. 变更清单
| 参数 | 改前值 | 改后值 | 变更 |
|------|--------|--------|------|
| TIER_TIMEOUT_BUDGET_S | 100 | 115 | +15s |

其余7参数不变: UPSTREAM=48, MIN_OUTBOUND=2.5, KEY_COOLDOWN=38, TIER_COOLDOWN=22, SSLEOF_DELAY=1.0, FASTBREAK=5, CONNECT_RESERVE=8

## 3. 优化执行

### 3a. 修改docker-compose.yml
```bash
ssh -p 222 opc2_uname@100.109.57.26
sudo sed -i 's/TIER_TIMEOUT_BUDGET_S: "100"/TIER_TIMEOUT_BUDGET_S: "115"/g' /opt/cc-infra/docker-compose.yml
```
- 仅修改hm40006区块的TIER_TIMEOUT_BUDGET_S, 其他服务(NV_TIER_TIMEOUT_BUDGET_S=45)未影响

### 3b. 应用变更 (docker compose up -d)
```bash
cd /opt/cc-infra && sudo docker compose up -d hm40006
# Container hm40006 Recreated → Started
```
- mihomo服务未停止/未重启 (PID 24528保持运行, 铁律遵守)

### 3c. 验证新配置
```bash
docker exec hm40006 env | grep TIER_TIMEOUT_BUDGET_S
# TIER_TIMEOUT_BUDGET_S=115 ✓

curl -s http://localhost:40006/health
# {"status":"ok","proxy_role":"passthrough","hm_num_keys":5,...} ✓
```

## 4. 改后验证

### 4a. 容器env一致性
- compose L470: TIER_TIMEOUT_BUDGET_S="115"
- 容器env: TIER_TIMEOUT_BUDGET_S=115
- **双处一致** ✓

### 4b. 服务健康
- /health=200 OK
- hm40006监听40006正常
- 改后15min logs: 5×SUCCESS, 0×TIMEOUT, 0×TIER-FAIL
- 第3attempt激活逻辑: 2×48s=96s + 8s reserve = 104s < 115s → 第3attempt现在有机会触发

## 5. 轮次统计
- 上轮R498 (HM2→HM1): k4直连→mihomo 7896, compose漂移同步
- 本轮R499 (HM1→HM2): 单参数微调 BUDGET 100→115
- R496勘定包(SR+4.3pp估算)在本轮执行
- 连续NOP打破: R490→R492→R494→R496(HM1侧4轮NOP) → 本轮有参数变更

## 6. 铁律遵守
- ✅ 只改HM2不改HM1: TIER_TIMEOUT_BUDGET_S在HM2 /opt/cc-infra/docker-compose.yml中修改
- ✅ 单参数少改多轮: 仅1参数+15s, 其余7参数零变更
- ✅ 数据驱动先采集后决策: docker logs 1h基线+env验证+budget_break根因量化
- ✅ mihomo服务存活: PID 24528未停止/未重启, 仅hm40006容器recreate
- ✅ 零429预警: 改前1h 0×429, 代理配置未动(k1 mihomo/k2-k5 direct)
- ✅ 配置一致性: compose与容器env双处一致

## ⏳ 轮到HM2优化HM1
