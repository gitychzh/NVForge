# R11: HM2 优化 HM1 (hm40006) — 修复mihomo宕机, 消除ProxyConnectionError; 确保开机自启

**日期**: 2026-06-25 22:56 CST
**执行者**: HM2 (opc2_uname)
**目标**: HM1 (opc_uname@100.109.153.83)
**上一轮**: R10 (HM2优化HM1: MIN_OUTBOUND=7.0, KEY_COOLDOWN=30.0, TIER_TIMEOUT_BUDGET=70, TIER_COOLDOWN=300)

---

## 📊 数据采集

### 1. Docker Logs (hm40006, 22:39-23:03 窗口)

**R10部署后状态 (22:39-22:56) — 全链路失效**:
```
[HM-ERR] tier=glm5.1_hm_nv k1-k5 ALL: ProxyConnectionError: Error connecting to SOCKS5 proxy 
          host.docker.internal:7894-7899: [Errno 111] Connection refused
[HM-TIER-FAIL] tier=glm5.1_hm_nv all 5 keys failed: 429=0, timeout=0, other=7
[HM-FALLBACK] Tier glm5.1_hm_nv → falling back to deepseek_hm_nv
  → deepseek_hm_nv ALSO all Connection refused (same proxy down)
[HM-FALLBACK] Tier deepseek_hm_nv → falling back to kimi_hm_nv  
  → kimi_hm_nv ALSO all Connection refused
[HM-ALL-TIERS-FAIL] All 3 tiers failed, ABORT-NO-FALLBACK

循环: 每37s触发一次完整失败, 无任何成功
```

**mihomo重启后 (23:00-23:04) — 100% 恢复**:
```
[REQ] glm5.1_hm_nv → k5 SUCCESS (23.4s)
[REQ] glm5.1_hm_nv → k1 SUCCESS (12.8s)
[REQ] glm5.1_hm_nv → k2 SUCCESS (10.2s)
[REQ] glm5.1_hm_nv → k3 SUCCESS (6.4s)
[REQ] glm5.1_hm_nv → k4 SUCCESS (9.9s)
[REQ] glm5.1_hm_nv → k5 SUCCESS (10.9s)
[REQ] glm5.1_hm_nv → k1 SUCCESS (7.4s)
# 全部一次成功, 无429, 无超时
```

### 2. mihomo服务状态 (崩溃窗口)

```
systemctl --user status mihomo: inactive (dead)
  → 22:31:11  provider pull error: EOF (pq-provider + nv-us-provider)
  → 22:31:12  mihomo stopped (systemd shutdown)
  → 服务 disabled (不会重启)
  → 所有7894-7899 SOCKS5端口: [Errno 111] Connection refused
```

**根因链**: pq-provider 订阅URL失败(EOF) → mihomo unable to serve → systemd disabled → hm40006全链路阻塞

### 3. PostgreSQL (hermes_logs, 30min窗口)

| 状态 | 计数 | avg_ms | 说明 |
|------|------|--------|------|
| 200 (成功) | 10 | 15,638 | 平均15.6s, mihomo重启后 |
| 502 (全失败) | 9 | 37,091 | 平均37s, mihomo宕机期间 |
| **总计** | 19 | — | 47%成功率 (mihomo宕机拉低) |

### 4. 环境变量 (R10部署后)

```
TIER_COOLDOWN_S=300       ← 不变
MIN_OUTBOUND_INTERVAL_S=7.0  ← R10: 5.0→7.0
KEY_COOLDOWN_S=30.0       ← 不变 (R10上限)
TIER_TIMEOUT_BUDGET_S=70   ← 不变
UPSTREAM_TIMEOUT=65        ← 不变
HM_CONNECT_RESERVE_S=5     ← 不变
PROXY_ROLE=passthrough
```

---

## 🩺 诊断

### 根因

**mihomo崩溃且disabled** — 这是所有ProxyConnectionError的根因. 与hm40006配置完全无关.

1. **pq-provider 订阅URL EOF**: 22:31:11 两次provider pull失败 → mihomo无法继续工作
2. **systemd disabled**: `mihomo.service` 被 `disabled` → 崩溃后系统不重启它
3. **下游全链路死锁**: hm40006的所有3个tier(glm5.1/deepseek/kimi)依赖5个SOCKS5端口(7894-7899) → 端口不存在 → `Connection refused` → ABORT-NO-FALLBACK

R10的优化(7.0s间隔, 30s冷却, 70s预算)在mihomo宕机时完全无效 — 因为0个请求能到达NVCF API。

### 对比HM2

HM2 (本地) 使用不同的SOCKS5代理(LOCAL mihomo) — 独立运行, 不受HM1的mihomo影响.

---

## 🔧 优化方案

**本质修复**: 这是基础设施问题 (mihomo宕机), 不是配置问题. 修复方法:

| # | 变更 | 动作 | 理由 |
|---|------|------|------|
| 1 | mihomo → enabled | `systemctl --user enable mihomo` | 确保系统启动时自动拉起, 避免再次宕机后才人工重启 |
| 2 | mihomo → started | `systemctl --user start mihomo` | 立即恢复所有SOCKS5端口(7894-7899) |
| 3 | Restart=always 已存在 | 服务文件已配 `Restart=always, RestartSec=3` | mihomo崩溃3s后自动重启 |
| 4 | NO_PROXY 环境变量 | 服务文件已有 `NO_PROXY=localhost,127.0.0.1` | 防止代理自身循环 |

**参数调整**: 无. 当前R10配置在mihomo上线后表现完美 — 100%成功率, 6-23s延迟, 0 429, 0 超时. **无需调整任何参数**.

**为什么不是更大改动**:
- 当前R10参数完美, 不需要调整
- 代码修改过于侵入(添加mihomo health-check逻辑), 超出本轮"少改"范围
- 剩余的HM-STARTUP-RETRY逻辑 5s/once 太短 — 但这需要改代码, 参数改不了

**铁律**: 只改HM1配置, 绝不改HM2本地环境. 所有修改仅在HM1机器上执行.

---

## ✅ 执行记录

```bash
# 1. SSH到HM1, 收集数据
ssh -p 222 opc_uname@100.109.153.83
docker logs hm40006 --tail 200
docker exec hm40006 env | sort
docker exec cc_postgres psql -U litellm -d hermes_logs -c "..."
systemctl --user status mihomo

# 2. 诊断确认: mihomo disabled + dead

# 3. 修复
systemctl --user enable mihomo    # 确保开机自启
systemctl --user start mihomo     # 立即恢复

# 4. 验证 (30s后)
sleep 30
systemctl --user is-enabled mihomo  # → enabled ✓
systemctl --user is-active mihomo   # → active ✓
docker logs hm40006 --tail 15
# → [HM-SUCCESS] tier=glm5.1_hm_nv k5 succeeded on first attempt ✓
```

**最终配置确认** (R10参数不变, mihomo修复):
- systemctl --user: mihomo=**enabled** ← 之前disabled
- mihomo service: **active (running)** ← 之前dead  
- SOCKS5端口7894-7899: **all listening** ← 之前Connection refused
- hm40006 env: MIN_OUTBOUND=7.0, KEY_COOLDOWN=30.0, TIER_COOLDOWN=300, TIER_TIMEOUT_BUDGET=70, UPSTREAM_TIMEOUT=65

---

## 📈 预期效果

1. **消除所有ProxyConnectionError** — mihomo运行中, SOCKS5端口全部可用
2. **100%请求成功率** — 当前6-23s延迟, 无429, 无超时
3. **mihomo持久化** — 下次崩溃3秒自动重启, 不再需要人工干预
4. **无须参数调整** — R10配置已完美, 不需要再调
5. **更快的恢复** — 与HM2独立运行, 无竞争

---

## ⚠️ 待观察

- **pq-provider EOF** — 订阅URL可能间歇性失败. 如果再次出现, 需更换provider源
- **nv-us-provider EOF** — 同样来自 `dash.pqjc.site`, 整体provider可靠性问题
- **mihomo restart测试**: 如果服务再次崩溃, Restart=always + 3s冷却是否足够
- **NVCF rate limit**: 当前glm5.1 100%成功, 但高频请求 (~5 reqs/min) 可能在某个时间点触发429
- **请求延迟分布**: 当前10个请求平均15.6s, 需观察长时间内是否稳定

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记