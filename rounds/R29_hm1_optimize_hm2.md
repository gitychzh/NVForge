# R29: HM1优化HM2 — 容器重新部署 + TIER_COOLDOWN_S 60→55

**Actor**: HM1 (opc_uname)
**Target**: HM2 (opc2_uname, 100.109.57.26, hm40006)
**Previous Round**: R28 (HM2: HM_CONNECT_RESERVE_S 20→21 on HM1)
**Change**: TIER_COOLDOWN_S: **60→55** (-5s) + 容器重新部署

## 数据收集

### 发现：容器运行过期配置
`docker exec hm40006 env` 显示实际运行值 vs docker-compose.yml 记载值严重不一致:

| 参数 | 容器实际值 | docker-compose.yml | 差距 |
|------|-----------|-------------------|------|
| HM_CONNECT_RESERVE_S | 2 | 3 | -1s |
| TIER_TIMEOUT_BUDGET_S | 75 | 107 | -32s |
| UPSTREAM_TIMEOUT | 45 | 58 | -13s |
| MIN_OUTBOUND_INTERVAL_S | 13.0 | 11.0 | +2s (更慢) |
| TIER_COOLDOWN_S | 120 | 60 | +60s (2倍) |
| KEY_COOLDOWN_S | 30.0 | 30.0 | 相同 |

**容器启动时间**: 2026-06-26 00:33 UTC — 距今8小时，期间docker-compose.yml被R16-R28多轮修改但从未`docker compose up -d`。

### 日志分析 (08:35-08:55 UTC)
- **glm5.1_hm_nv**: 100% 429 rate limit，所有5个key同时触发NVCF函数级限流
- **deepseek_hm_nv**: 100% fallback成功，约20-30s per request
- **all_tiers_exhausted**: 0次在最近20分钟窗口
- **连接级错误**: 无SSLEOFError/ConnectionResetError/RemoteDisconnected
- **TIER_COOLDOWN_S=120**: 导致glm5.1失败后2分钟才恢复尝试，实际40多条glm5.1失败日志全部在2分钟窗口内

### 根本原因
容器从未被重新部署以应用docker-compose.yml的多轮优化值。R16-2(120→60), R18(28→30), R25(10.0→11.0), R26(55→58), R26(105→107) 全部只修改了compose文件但未执行`docker compose up -d`。容器持续运行过期配置8小时。

## 优化变更

### 步骤1: 容器重新部署（应用累积优化）
```bash
cd /opt/cc-infra
docker stop hm40006 && docker rm hm40006 && docker compose up -d hm40006
```
将所有R16-R28轮次的compose优化一次性应用到运行容器。

### 步骤2: TIER_COOLDOWN_S 60→55 (-5s)
```bash
sed -i 's/"60"/"55"/' docker-compose.yml  # 第481行
docker stop hm40006 && docker rm hm40006 && docker compose up -d hm40006
```

| 参数 | 变更前 | 变更后 | 理由 |
|------|--------|--------|------|
| TIER_COOLDOWN_S | 60 | **55** (-5s) | NVCF rate limit窗口~60s; 55s比典型重置周期快5s; glm5.1 429恢复更快; 减少TIER-SKIP等待时间; 单参数变更(少改多轮) |

### 未变更参数
`UPSTREAM_TIMEOUT=58`, `TIER_TIMEOUT_BUDGET_S=107`, `MIN_OUTBOUND_INTERVAL_S=11.0`, `KEY_COOLDOWN_S=30.0`, `HM_CONNECT_RESERVE_S=3`, `PROXY_TIMEOUT=300` — 全部保持compose值。

## 执行记录

```bash
# 备份
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R29

# 修改第481行
sed -i '481s/"60"/"55"/' /opt/cc-infra/docker-compose.yml

# 重新部署
cd /opt/cc-infra
docker stop hm40006 && docker rm hm40006 && docker compose up -d hm40006

# 验证
docker exec hm40006 env | grep TIER_COOLDOWN_S
# → TIER_COOLDOWN_S=55 ✓

# 健康检查
curl -s http://localhost:40006/health
# → {"status":"ok","port":40006} ✓

# 容器状态
docker inspect hm40006 --format '{{.State.Status}}'
# → running ✓
```

## 预期效果

- **TIER_COOLDOWN 60→55**: 每次glm5.1失败后恢复尝试时间减少5s（55s vs 60s vs 旧值120s）。NVCF rate limit窗口~60s，55s提前5s开始重试。
- **UPSTREAM_TIMEOUT 45→58**: +13s per-key超时，deepseek pexec函数运行更完整，减少NVCFPexecTimeout截断。
- **TIER_TIMEOUT_BUDGET 75→107**: +32s tier预算，2个完整key cycle保障，减少budget耗尽时的kimi回退触发。
- **MIN_OUTBOUND_INTERVAL 13.0→11.0**: -2s首key延迟，更快响应。
- **HM_CONNECT_RESERVE 2→3**: +1s SOCKS5+SSL连接预留，更安全。

**综合**: 容器从过期配置（RESERVE=2, BUDGET=75, TIMEOUT=45, COOLDOWN=120）升级到优化配置（RESERVE=3, BUDGET=107, TIMEOUT=58, COOLDOWN=55）。单轮净效果：-5s tier cooldown + 全栈重新部署。

## 观察项

1. **mihomo代理**: 进程PID=2008535，运行超过24小时，5个SOCKS5端口(7894-7899)全部正常监听。docker内部通过`host.docker.internal`访问。
2. **cc_postgres DB连接失败**: `[HM-DB] connect failed: could not translate host name "cc_postgres"` — Docker DNS无法解析此hostname。需检查`cc_postgres`是否在docker网络中或需使用IP/DNS别名。这是R40添加的DB功能，不影响核心代理逻辑（best-effort async）。
3. **glm5.1函数级429不可修复**: NVCF function ID 822231fa全部5个key同时触发429，是NVCF基础设施级rate limit，非per-key tuning可解决。当前策略：快速检测→fallback deepseek。
4. **deepseek为实际工作层**: 100%请求通过deepseek回退成功（glm5.1 100% 429）。deepseek per-key超时分布已从R24数据稳定。
5. **下次方向**: 如果TIER_COOLDOWN=55下glm5.1恢复尝试改善，考虑进一步减少至50s或调整MIN_INTERVAL。若Tier cooldown已达瓶颈，可考虑UPSTREAM_TIMEOUT微调或TIER_BUDGET微调。

## ⏳ 轮到HM2优化HM1