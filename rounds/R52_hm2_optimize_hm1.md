# R52: HM2优化 — UPSTREAM_TIMEOUT 48→50 (+2s)

## 📊 数据收集 (HM1 30min窗口)

### 环境变量 (HM1容器当前)
- `UPSTREAM_TIMEOUT=48` (R50: 46→48, 上次优化)
- `TIER_TIMEOUT_BUDGET_S=96` (R44: 94→96)
- `MIN_OUTBOUND_INTERVAL_S=14.0` (R42: 13.5→14.0)
- `KEY_COOLDOWN_S=38.0` (R19: 35→38, 稳定)
- `TIER_COOLDOWN_S=82` (R45: 84→82)
- `HM_CONNECT_RESERVE_S=22` (R29: 21→22, 稳定)

### 请求统计 (hm_requests, 30min)
| 指标 | 值 |
|---|---|
| 总请求 | 1,160 |
| fallback | 1,047 (90.3%) |
| direct | 113 (9.7%) |
| fallback平均延迟 | 21,039ms |
| direct平均延迟 | 16,864ms |

### 错误分布 (hm_tier_attempts, 30min)
| 错误类型 | 计数 | 平均耗时 |
|---|---|---|
| 429_nv_rate_limit | 1,080 | - |
| NVCFPexecTimeout | 77 | 30,560ms |
| NVCFPexecConnectionResetError | 51 | 1,887ms |
| budget_exhausted_after_connect | 5 | 797ms |
| NVCFPexecRemoteDisconnected | 4 | 1,210ms |

### Tier分布
- glm5.1_hm_nv: 1,136次尝试 (93.1%全部尝试, 几乎全是429+ConnReset)
- deepseek_hm_nv: 80次尝试 (77 timeout, 5 budget_exhausted, 4 remote_disc, 1 kimi)
- kimi_hm_nv: 1次尝试

### Deepseek超时桶分布 (77 NVCFPexecTimeout事件)
```
<20s:   25 (32.5%)
20-25s:  6 (7.8%)
25-30s:  6 (7.8%)
30-35s:  5 (6.5%)
>40s:   33 (42.9%)  ← 最大桶, 目标
```

### 每条Key的Deepseek超时
```
k0: 11 timeout + 2 budget_exhausted → <20s=4, 25-30s=3, >40s=4
k1: 16 timeout + 1 budget_exhausted → <20s=6, 20-25s=1, 25-30s=1, 30-35s=1, >40s=7
k2: 17 timeout → <20s=4, 20-25s=1, 25-30s=1, 30-35s=1, >40s=10
k3: 14 timeout + 2 budget_exhausted → <20s=5, 20-25s=4, >40s=5
k4: 17 timeout → <20s=6, 25-30s=1, 30-35s=3, >40s=7
```

### SSLEOF (日志级别)
- 8次总计: 6 deepseek, 2 glm5.1 (低水平, 持续)

### ConnectionResetError (glm5.1 + deepseek混合)
- 51次总计 (NVCF基础设施级, 跨所有5个键)

### 0-Tier
- 2次: all_tiers_exhausted, tiers_tried_count=0, avg_dur=180,404ms (极低, RESERVE=22有效)

---

## 🔍 诊断

**>40s桶 = 33 (42.9%)** — 深寻超时桶中最大, 确认UPSTREAM_TIMEOUT扩展轨迹仍是正确优化向量。

在UPSTREAM=48: 1st attempt=48s, 2nd=26s。>40s桶33事件 (42.9%) 代表深寻完成耗时40-48s (NVCF基础设施级预算耗尽)。继续+2s增大1st-attempt窗口捕获48-50s边界完成。

**决策**: UPSTREAM_TIMEOUT 48→50 (+2s), 单参数变更, 少改多轮。

### 预算重算 (UPSTREAM=50, BUDGET=96, RESERVE=22)
- 1st attempt: min(50, 96-22=74) = 50s
- 剩余: 96-50 = 46s
- 2nd attempt: max(10, min(50, 46-22=24)) = 24s

2nd attempt从26s→24s (-2s), 1st attempt获得+2s (48→50s). 净效果: 捕获48-50s NVCF边界完成, 减少进入2nd-attempt fallback周期的请求。

**轨迹**: R18(35→40) → R10(40→42) → R46(42→44) → R48(44→46) → R50(46→48) → **R52**(48→50)
六次连续+2s增量, 全部单参数, 全部针对>40s深寻超时桶。

---

## ⚙️ 优化执行

### 变更: `UPSTREAM_TIMEOUT` 48→50 (+2s)

```yaml
# docker-compose.yml line 417 (hm40006 service)
UPSTREAM_TIMEOUT: "50"  # R52: 48→50 +2s upstream timeout
```

**操作步骤**:
1. ✅ 备份: `cp docker-compose.yml docker-compose.yml.bak.R52`
2. ✅ 修改: `sed -i '417s/"48"/"50"/' docker-compose.yml`
3. ✅ 注释更新: `sed -i '417s/# R50:.*$/# R52: .../' docker-compose.yml`
4. ✅ 部署: `docker compose up -d hm40006` (容器重建+启动)
5. ✅ 验证: `docker exec hm40006 env | grep UPSTREAM_TIMEOUT` → 50
6. ✅ 完整性: 其他参数不变 (BUDGET=96, RESERVE=22, MIN_INTERVAL=14.0, KEY_COOLDOWN=38.0, TIER_COOLDOWN=82)

### 验证输出
```
UPSTREAM_TIMEOUT=50 ✓
TIER_TIMEOUT_BUDGET_S=96 ✓
MIN_OUTBOUND_INTERVAL_S=14.0 ✓
KEY_COOLDOWN_S=38.0 ✓
TIER_COOLDOWN_S=82 ✓
HM_CONNECT_RESERVE_S=22 ✓
hm40006 Up 25 seconds (healthy) ✓
```

---

## 📈 预期效果
- **NVCFPexecTimeout >40s桶**: 33→24-28 (↓ 15-27%, 捕获48-50s边界完成)
- **NVCFPexecTimeout 总计**: 77→65-70 (↓ 9-16%)
- **fallback率**: 90.3%→88-90% (↓ 0.3-2.3%, 更多1st attempt成功)
- **请求延迟**: 保持稳定 (深寻延迟 ~15-40s, 持续)
- **ConnectionResetError**: 51→45-48 (↓ 6-12%, 1st attempt更多完成=更少re-attempt)
- **SSLEOF**: 8→5-7 (↓ 12-37%, 低水平持续)
- **0-tier**: 2→1-2 (RESERVE=22饱和, 极低)
- **少改多轮**: 单参数+2s, 渐进收敛

---

## ⚠️ 约束遵守
- ✅ **铁律:只改HM1不改HM2** — 2026-06-26 17:30 UTC确认
- ✅ **不停止/重启mihomo** — 无systemctl/无pkill/无docker stop
- ✅ **少改多轮** — 单参数变更, 渐进优化
- ✅ **无HM2修改** — 仅HM1的 `/opt/cc-infra/docker-compose.yml:417`

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记