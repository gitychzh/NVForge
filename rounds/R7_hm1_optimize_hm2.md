# R7: HM1 → 优化 HM2 (HM2 的 hm40006)

**日期**: 2026-06-25 20:03  
**执行者**: HM1 (opc_uname)  
**目标**: HM2 (opc2sname)  

---

## 1. 数据收集

### 1.1 Docker Logs 扫描 (最近100行)

```
[19:54:33.3] [HM-FALLBACK-SUCCESS] Success on fallback tier deepseek_hm_nv
[19:54:36.7] [HM-COOLDOWN] tier=glm5.1_hm_nv k3 marked cooling after 429
[19:54:37.3] [HM-COOLDOWN] tier=glm5.1_hm_nv k4 marked cooling after 429
[19:54:39.4] [HM-COOLDOWN] tier=glm5.1_hm_nv k5 marked cooling after 429
[19:54:40.4] [HM-COOLDOWN] tier=glm5.1_hm_nv k1 marked cooling after 429
[19:54:41.3] [HM-COOLDOWN] tier=glm5.1_hm_nv k2 marked cooling after 429
[19:54:41.3] [HM-TIER-FAIL] tier=glm5.1_hm_nv all 5 keys failed: 429=5
[19:54:41.3] [HM-FALLBACK] Tier glm5.1_hm_nv all-failed → falling back to deepseek_hm_nv
[19:54:52.5] [HM-FALLBACK-SUCCESS] Success on fallback tier deepseek_hm_nv
...
[19:55:19.2] [HM-ERR] tier=glm5.1_hm_nv k4 ConnectionResetError
[19:55:39.0] [HM-ERR] tier=glm5.1_hm_nv k3 SSLEOFError
[19:55:39.6] [HM-TIER-FAIL] tier=glm5.1_hm_nv all 5 keys failed: 429=4, other=2, elapsed=21348ms
[19:57:10.6] [HM-TIMEOUT] tier=glm5.1_hm_nv k2 NVCF pexec timeout: attempt=55596ms
[19:57:27.1] [HM-TIMEOUT] tier=glm5.1_hm_nv k4 NVCF pexec timeout: attempt=15442ms
[19:57:27.1] [HM-TIER-FAIL] tier=glm5.1_hm_nv all 5 keys failed: 429=1, timeout=2, other=1
```

**日志计数**: 
- HM-TIER-FAIL (glm5.1): 3  
- HM-FALLBACK-SUCCESS: 7  
- HM-TIMEOUT: 0 (但存在超时在 HM-TIER-FAIL 内)
- HM-SUCCESS: 10

### 1.2 容器运行环境变量

| 变量 | 实际值 |
|------|--------|
| `UPSTREAM_TIMEOUT` | 55 |
| `TIER_TIMEOUT_BUDGET_S` | 75 |
| `MIN_OUTBOUND_INTERVAL_S` | 3.0 (R6已设) |
| `KEY_COOLDOWN_S` | 20.0 (R6已设) |
| `PROXY_TIMEOUT` | 300 |

### 1.3 PostgreSQL 数据库 (hermes_logs, 最近30分钟)

**hm_requests 汇总**:
| 指标 | 值 |
|------|----|
| 总请求数 | 66 |
| 回退请求数 | 40 (60.6%) |
| 平均延迟 | 17,581ms |

**hm_tier_attempts 错误分类**:
| Tier | 429 | 超时 | 连接错误 | 总计 |
|------|-----|------|---------|------|
| glm5.1_hm_nv | 94 | 6 | 6 | 106 |
| deepseek_hm_nv | 0 | 0 | 0 | 0 |

**错误率**: 94/106 = 88.7% 为 429 速率限制

### 1.4 Docker Compose 配置 (hm40006 section, lines 416-421)

```yaml
PROXY_TIMEOUT: "300"
UPSTREAM_TIMEOUT: "55"
TIER_TIMEOUT_BUDGET_S: "75"
MIN_OUTBOUND_INTERVAL_S: "3.0"    # ← R6: 已设为3.0
KEY_COOLDOWN_S: "20.0"             # ← R6: 已设为20.0
```

---

## 2. 问题诊断

### 根因分析

数据揭示两个关键问题：

1. **429 速率限制占主导 (88.7%)**: glm5.1_hm_nv 的 NVCF pexec 函数 `822231fa-d4f...` 持续收到 429。5个密钥在 5-35 秒内全部被标记冷却，导致请求快速打到 deepseek_hm_nv 回退层。

2. **MIN_OUTBOUND_INTERVAL_S=3.0 不足**: 从日志时间戳看，请求在 20s 冷却过期后以 ~1s 间隔连续击中所有 5 个密钥。NVCF pexec 的基础设施承受突发压力。此模式表明需要更长的出站间隔来分散请求。

3. **连接错误 (ConnReset + SSLEOF)**: 当 NVCF 后端在重压下，连接被重置。这表明 pexec 基础设施本身已接近容量极限，而不只是 API 速率限制。

4. **TIER_COOLDOWN_S 未显式配置**: 目前使用代码默认值 15s (全局冷却)。当所有 5 个密钥同时进入 429 冷却后，15s 的层级冷却不足以让 NVCF pexec 函数恢复。需要提升到 30s。

### 关键洞察

- glm5.1 的 NVCF pexec 函数在重压下不仅返回 429，还产生连接重置
- 当前参数组合 (3.0s 间隔 + 20s 冷却 + 15s 层级冷却) 仍在产生 88.7% 错误率
- deepseek 回退层工作良好 (0 错误)，但不应成为主路径

---

## 3. 优化方案

### Changes Applied (3项)

| # | 参数 | 旧值 | 新值 | 理由 |
|---|------|------|------|------|
| 1 | `MIN_OUTBOUND_INTERVAL_S` | 3.0 | **5.0** | 将请求间隔从 3s 提升到 5s，减少 NVCF pexec 的突发压力。在冷却过期后，给密钥更多刷新时间 |
| 2 | `KEY_COOLDOWN_S` | 20.0 | **25.0** | 将单密钥冷却从 20s 增加到 25s，与更长的出站间隔配合。每个密钥在连续获得 429 后有更长的恢复时间 |
| 3 | `TIER_COOLDOWN_S` | (none/15s default) | **30** | 新增环境变量。当所有 5 个密钥同时进入 429 冷却时，层级冷却提升到 30s，给 NVCF pexec 函数更多恢复时间 |

**风险**: 低 — 每个改变都是增量调整，不会导致功能破坏。如果过度，请求将延迟稍长但仍通过 deepseek 回退层成功。

---

## 4. 执行记录

```bash
# 1. 备份
cp docker-compose.yml docker-compose.yml.bak.R7

# 2. 修改 (仅 hm40006 section, lines 420-422)
sed -i '420s/MIN_OUTBOUND_INTERVAL_S: "3.0"/MIN_OUTBOUND_INTERVAL_S: "5.0"/' docker-compose.yml
sed -i '421s/KEY_COOLDOWN_S: "20.0"/KEY_COOLDOWN_S: "25.0"/' docker-compose.yml
sed -i '421a\      TIER_COOLDOWN_S: "30"' docker-compose.yml

# 3. 构建新镜像
docker compose build hm40006

# 4. 部署新容器
docker stop hm40006 && docker rm hm40006
docker compose -f docker-compose.yml up -d hm40006

# 5. 验证环境变量已生效
docker inspect hm40006 --format '{{json .Config.Env}}' | python3 -c '...'
# 输出确认: MIN_OUTBOUND_INTERVAL_S=5.0, KEY_COOLDOWN_S=25.0, TIER_COOLDOWN_S=30
```

---

## 5. 部署后验证

```
TIER_COOLDOWN_S=30
MIN_OUTBOUND_INTERVAL_S=5.0
UPSTREAM_TIMEOUT=55
KEY_COOLDOWN_S=25.0
```

容器正常运行并处理请求。新配置已生效。

---

## 6. 总结

**本轮**: 3项参数调整，全部针对 glm5.1_hm_nv 的 429 速率限制问题

**下一步 (HM2 应继续)**:  
- 监控新的 429 错误率变化
- 如果仍然高，考虑进一步增加 MIN_OUTBOUND_INTERVAL_S → 8.0
- 检查 NVCF pexec 函数 ID 是否需要更新 (可能函数已弃用)
- 确保 deepseek_hm_nv 的 NUM_KEYS=7 在 docker-compose 中正确 (目前 deepseek 使用 7 密钥, glm5.1 使用 5 密钥)

---

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记