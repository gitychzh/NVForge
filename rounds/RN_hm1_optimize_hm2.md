# R289: HM1→HM2 — ⚠️ HM2不可达（持续SSH全断, 55分钟完全消失, Tailscale离线 rx=0）

> **Round**: R289 | **Actor**: HM1 → **Target**: HM2 | **Date**: 2026-06-29 15:47 UTC | **Type**: 阻断报告
> **Author**: opc_uname | **Commit**: [pending]

---

## 🚨 状况: HM2主机完全消失（R287→R288→R289, 累计55分钟无响应）

### 网络诊断（3-Layer 验证, 2026-06-29 15:47 UTC）
```
Layer 1 (ICMP): ping 100.109.57.26 → 100% packet loss (3/3, W=4s)
Layer 2 (TCP):   nc 100.109.57.26:222 → Connection timed out (5s)
Layer 3 (SSH):   ssh opc2_uname@100.109.57.26 -p 222 → Connection timed out (15s)

Tailscale 确认: opc2sname (100.109.57.26) → offline, last seen 55m ago, rx=0
  - tx=81744 (发送量正常) rx=0 (完全无回包) — 主机已掉电或网络完全断裂
  - relay "sfo" 已失联 — 无法通过Tailscale DERP中继
  - 与其他节点（opcsname-1, desktop-sgedrr5）直连正常 → 非Tailscale全局故障
```

### HM1侧健康确认（R289窗口, 15:46-15:49 UTC）
```
hm40006: 正常 (healthy, 2h uptime)
deepseek_hm_nv tier: 全key 100%成功 (k1-k5 连续 HM-SUCCESS on first attempt)
  - 15:46:27 k4 SUCCESS
  - 15:46:41 k5 SUCCESS
  - 15:47:15 k1 SUCCESS (1st attempt)
  - 15:47:20 k2 SUCCESS (1st attempt)
  - 15:47:40 k3 SUCCESS (1st attempt)
  - 15:48:01 k4 SUCCESS (1st attempt)
  - 15:48:18 k5 SUCCESS (1st attempt)
  - 15:48:37 k1 SUCCESS (1st attempt)
  - 15:48:55 k2 SUCCESS (1st attempt)
  - 15:49:15 k3 SUCCESS (1st attempt)

0 error | 0 fallback | 0 ATE | 0 429 | 0 BUDGET-break | 0 SSLEOF
PostgreSQL: 372 total requests (92 recent 30min) — 健康
```

### HM2侧状态推断（基于R287碎片 + Tailscale信号）
```
R287窗口 (14:42-14:50 UTC, 8min碎片):
- HM-TIER-FAIL: 4次all-5-keys-fail → ABORT-NO-FALLBACK
  - empty200=1 各次, timeout=2-3 (121,284ms ~ 162,532ms)
- 总耗时: 106-163s (P99=163s 超 BUDGET=128s)
- SSLEOFError: k2/k5 (3s backoff自愈成功)
- BUDGET-break: 剩余0.3s触发 ABORT
- single-tier glm5.1_hm_nv — 无fallback链

R288 (14:55): 确认不可达 (100% packet loss)
R289 (15:47): 确认仍然不可达 (55min, rx=0)

推断: HM2在14:50 UTC后彻底离线
  - 最后一次数据时间戳: 14:49:58 (162,532ms timeout)
  - Tailscale最后一次心跳: ~14:52 UTC (55min前)
  - rx=0: 主机已无响应（掉电/崩溃/网络断）
```

---

## 🧠 分析: 无法执行优化

### 计划中的优化方向（基于R287碎片数据, 延续R288计划）

| # | 参数 | 当前值 | 目标值 | Δ | 理由 |
|---|------|--------|--------|---|------|
| 1 | **TIER_TIMEOUT_BUDGET_S** | 128s | 135s | +7s | P99=163s > BUDGET=128s → 预算破裂; 覆盖106-163s实际范围 |
| 2 | **HM_CONNECT_RESERVE_S** | 22s | 24s | +2s | k2/k5高频SSLEOFError（每2-5分钟1次）; SSL握手headroom |
| 3 | **TIER_COOLDOWN_S** | 22s | 30s | +8s | 对齐KEY_COOLDOWN=38s; 避免单层tier冷却过短导致快速重试耗尽预算 |

### 预算计算验证（目标值 135s BUDGET）
```
BUDGET=135, UPSTREAM=70, RESERVE=24, MIN=13
1st key: 70s → remaining=65
2nd key: max(10, min(70, 65-24-13=28)) = 28s → remaining=37
3rd key: max(10, min(70, 37-24-13=0)) = 10s (floor)
Total: 70+28+10=108s ≤ 135s ✓ (理论, 3-key)
4th key (应急): max(10, min(70, ...)) = 10s (floor)
理论覆盖: 70+28+10+10=118s ≤ 135s
```

**关键**: 即使只有3个key成功（k2/k5 SSLEOF重试占据RESERVE时间），总预算108s也能覆盖106-163s的P90范围（106-127s）。P99=163s超过BUDGET但属于极端重试+网络延迟叠加的异常值——覆盖需要更大的BUDGET（如145s）但会引入更多风险（tier冷却死锁）。当前策略以覆盖P90为目标。

### 无法执行原因
```
❌ SSH到HM2完全断开（TCP 222端口, 持续55分钟）
❌ ping 100% 包丢失（3/3失败, 100.109.57.26）
❌ Tailscale: opc2sname offline, rx=0（零回包, 主机无响应）
❌ 无法读取HM2 docker-compose.yml / config.py
❌ 无法执行 docker compose up -d / docker compose restart
❌ 铁律: 只改HM2不改HM1 — 但HM2主机已整体消失
❌ ⚠️ 不得停止/重启/kill mihomo — 但HM2侧mihomo进程已随主机消失
```

### 可能原因分析
```
1. HM2主机掉电（最可能: rx=0, 无任何TCP/ICMP响应, tailscale完全消失）
2. HM2主机内核崩溃（OOM killer? docker overcommit? — 无日志可查）
3. HM2主机的网络接口/路由完全断开（物理链路或云网络故障）
4. 非Tailscale自身故障 — HM1侧其他节点正常（opcsname-1, desktop, ebg-an00 均在线）
```

---

## 📋 判定

| 评判标准 | 状态 |
|----------|------|
| 更少报错 | ⚠️ 无法评估（HM2数据不可达, 55分钟无响应） |
| 更快请求 | ⚠️ 无法评估（HM2数据不可达） |
| 超低延迟 | ⚠️ 无法评估（HM2数据不可达） |
| 稳定优先 | ⚠️ HM2完全消失, HM1侧deepseek_hm_nv正常但单侧运行 |
| 只改HM2 | ❌ HM2不可达, 无法修改任何配置 |

**结论**: R289因HM2主机完全离线（55分钟, rx=0, 3-layer全断）而无法执行任何优化。R287的碎片数据（14:42-14:50 UTC）显示glm5.1_hm_nv单层链路的3个缺陷：BUDGET破裂（128s < 163s P99）、SSLEOF高频（k2/k5）、tier冷却过短（22s vs KEY 38s）。优化计划已拟定3项（BUDGET+7s, RESERVE+2s, TIER_COOLDOWN+8s对齐）但需HM2主机恢复后才能执行。当前HM1侧deepseek_hm_nv全key健康（100%成功, 0 error），双机不对称运行但HM1侧无降级。

本报告写入后，检测脚本将检测到 `## ⏳ 轮到HM2优化HM1` 标记，当HM2恢复上线时自动触发其优化回合。

---

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记