# R361: HM2→HM1 — ⏸️ 无操作 · 全参数已达天花板 · 第11轮连续nop · 铁律:只改HM1不改HM2

**轮次**: HM2 优化 HM1 (HM2=执行者, HM1=反对者)
**角色**: HM2=执行者, HM1=反对者
**日期**: 2026-06-30 14:00 UTC+08 (CST)

## 📊 数据采集 (HM1: 100.109.153.83, hm-40006)

### Docker 日志 (tail 500, ~11:36–12:16 UTC, 40min窗口)
| 指标 | 值 |
|------|-----|
| 总请求成功 | 54 |
| SSLEOF错误 | 4 (k1×3, k5×1) |
| NVCF Pexec 超时 | 1 (k1, 48.7s) |
| 空响应 (empty200) | 0 |
| HTTP 429 | 0 |
| 请求级成功率 | **100%** (全部retry救回) |

错误详情:
```
k1 SSLEOF ✗ (3次, 11:36/11:43/12:13) → retry 3.0s → k2 ✓
k5 SSLEOF ✗ (1次, 12:14) → retry 3.0s → k1 ✓
k1 TIMEOUT 48.7s (12:15) → retry k2 ✓ (5.4s)
```

### 环境变量 (docker exec hm40006 env)
```
BUDGET=100, UPSTREAM_TIMEOUT=45, KEY_COOLDOWN_S=38, TIER_COOLDOWN_S=38
MIN_OUTBOUND_INTERVAL_S=6.0, CONNECT_RESERVE_S=10, SSLEOF_RETRY_DELAY_S=3.0
FASTBREAK=3 (default, pexec timeout counter)
PROXY_TIMEOUT=300, TZ=Asia/Shanghai
```
路由: k1=SOCKS5(7894), k2/k3=DIRECT, k4=SOCKS5(7897), k5=SOCKS5(7899)
function_id=4e533b45, 架构: R38.12 NVCF pexec 直连(单模型 deepseek_hm_nv)

### DB 状态 (PostgreSQL cc_postgres)
- 最后10条请求: 全部status=200, 0 errors
- 延迟: ttfb 0.8s–55.2s (中位数~12s), duration 0.8s–55.3s
- 键分布: k1(2), k2(3), k3(2), k4(1), k5(2) — 均衡
- 1h计数: 0, 30m计数: 0
- ⚠️ DB最后写入04:16 UTC (~10h前), 容器日志为唯一可信数据源

## 🔍 分析

### 全参数已达天花板 — 无可优化空间
所有7个可调参数均已达到最优值:
- BUDGET=100: 已达上限, 足够覆盖最慢请求(48.7s)
- UPSTREAM=45: 已达上限, 超时后retry机制完美救回
- KEY_COOLDOWN=38: 已达上限, SSLEOF后3s retry全部成功
- TIER_COOLDOWN=38: 已达上限, 同R341设定
- MIN_OUTBOUND=6.0: 已达上限, 零429零empty200
- CONNECT_RESERVE=10: 已达上限, R336减至10后稳定
- SSLEOF_RETRY=3.0: 已达上限, 所有SSLEOF 3s内retry成功

### 错误模式分析
- **SSLEOF (4次)**: 全部发生在SOCKS5键(k1/k5) — 网络层SSL中断, 非代码缺陷
  - 3次k1(7894 SOCKS5), 1次k5(7899 SOCKS5) — 隧道SSL握手偶发中断
  - 每次3s后重试成功 — SSLEOF_RETRY=3.0s已是最优值
  - k2/k3 DIRECT零SSLEOF — DIRECT连接更稳定但需轮转
- **TIMEOUT (1次)**: k1响应48.7s — NVCF上游慢响应, 非HM1配置问题
  - retry到k2仅5.4s成功 — 证明是上游偶发慢而非系统性问题

### 为什么不能改任何参数
| 参数 | 当前值 | 如果改 | 后果 |
|------|--------|--------|------|
| SSLEOF_RETRY ↑ | 3.0s | 4.0s | 无意义延长等待, SSLEOF已3s内恢复 |
| SSLEOF_RETRY ↓ | 3.0s | 2.0s | 可能来不及重连, 增加连续失败风险 |
| CONNECT_RESERVE ↑ | 10s | 12s | 增加冷启动延迟, 当前10s已足够 |
| KEY_COOLDOWN ↑ | 38s | 40s | 无意义延长, 当前38s无429 |
| TIER_COOLDOWN ↑ | 38s | 40s | 无意义延长 |
| MIN_OUTBOUND ↑ | 6.0s | 7.0s | 降低吞吐, 当前6.0s零阻塞 |
| BUDGET ↑ | 100s | 105s | 已超最大请求耗时(48.7s) |

### 少改多轮验证
- R345-R360: 连续10轮零变更 — 证明全参数已达稳定天花板
- 每轮独立采集40min窗口日志 — 持续100%成功率
- SSLEOF: 网络层偶发(4次/40min), 非配置相关
- TIMEOUT: 上游偶发(1次/40min), 非配置相关

### DB问题: 独立于代理性能
DB写入停止10h不影响请求路由(容器内存中运行). 这是独立运维问题, 不属于本优化循环.

## ✅ 决策: ⏸️ 无操作

**理由**:
1. 40min窗口100%请求级成功率
2. 4个SSLEOF+1个TIMEOUT全部retry救回 — 零用户可见失败
3. 7个参数全部已达天花板 — 任何改动只会引入劣化
4. 连续11轮零变更验证 — 系统已进入稳态
5. SSLEOF是网络层问题(DIRECT键零发生), 非配置可解

**铁律**: 只改HM1配置, 绝不改HM2本地.

## 📝 提交信息
- commit: R361: HM2→HM1 — ⏸️ 无操作 · 全参数已达天花板 · 第11轮连续nop
- author: opc2_uname
- 文件: rounds/RN_hm2_optimize_hm1.md

## ⏳ 轮到HM1优化HM2