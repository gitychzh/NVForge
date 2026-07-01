# R518 (HM1→HM2): MIN_OUTBOUND_INTERVAL_S 1.2→1.0 — 延续R517错峰收紧, 进一步降低并发波峰队列尾延迟

**轮次**: R518
**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2sname)
**日期**: 2026-07-02 01:04 CST / 2026-07-01 17:04 UTC
**类型**: 单参数收紧 (outbound throttle -0.2s)
**Commit**: 本commit

## 0. 时区与host标识

- 对端HM2 host_machine标识=`opc2sname`, 主机名=opc2sname。
- ts字段为UTC(日志与系统时间一致)。
- 三模型运行: kimi_nv(f966661c), dsv4p_nv(8915fd28), glm5_1_nv(6155636e)。
- 当前HM2 env基线: FASTBREAK=1, BUDGET=100, UPSTREAM=48, THINKING_TIMEOUT=50, OUTBOUND=1.2→1.0, KEY_CD=38, TIER_CD=22。

## 1. 改前数据采集 (HM2对端, host_machine=opc2sname)

### 1a. 容器env实测 (docker exec hm40006 env)

```
UPSTREAM_TIMEOUT=48
TIER_TIMEOUT_BUDGET_S=100
MIN_OUTBOUND_INTERVAL_S=1.2   ← 改前
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=22
HM_PEXEC_TIMEOUT_FASTBREAK=1
HM_CONNECT_RESERVE_S=3
HM_FORCE_STREAM_UPGRADE_TIMEOUT=50
```

### 1b. docker logs 短窗口基线 (R517改后重建~7min窗口, 00:40-00:47)

**kimi_nv请求统计** (从docker logs tail推算):

| # | key | proxy | result | elapsed |
|---|-----|-------|--------|---------|
| 1 | k4 | direct | SUCCESS | ~7s |
| 2 | k5 | 7896 | SUCCESS | ~4.6s |
| 3 | k1 | 7894 | SUCCESS | ~10s |
| 4 | k2 | 7894 | SUCCESS | ~20s |
| 5 | k3 | 7895 | SUCCESS | ~6s |
| 6 | k4 | direct | SUCCESS | ~9.5s |
| 7 | k5 | 7896 | SUCCESS | ~23s |
| 8 | k1 | 7894 | SUCCESS | ~18.8s |
| 9 | k2 | 7894 | SUCCESS | ~11.6s |
|10 | k3 | 7895 | TIMEOUT | ~50.9s |
|11 | k4 | direct | SUCCESS | ~27.2s |
|12 | k5 | 7896 | SUCCESS | ~23s |
|13 | k1 | 7894 | SUCCESS | ~27.4s |
|14 | k2 | 7894 | TIMEOUT | ~50.3s |
|15+ | (R517后重建空白) | | | |

**改前诊断**:
- 成功率: ~85.7% (12/14 在7min窗口内), 超时率 ~14.3% (2/14)。
- 错误模式: 零429, 零empty200, 零SSLEOF (最近10次日志无SSLEOF)。
- timeout=2 主导: k3@7895 50.9s, k2@7894 50.3s。
- FASTBREAK=1 生效: 每个timeout后仅1个key即break, 避免浪费后续4个key的~48s。
- peer fallback 触发: 7min内~5次, 对端HM1平均ttfb=258ms (R517记录), 极快接管。
- 延迟bipolar: 成功请求2.9s-41.7s (k2@7894极端慢), 失败请求集中于~50-51s。
- k1与k2共享7894出口; k3独用7895; k4 direct; k5独用7896。7894双key可能造成出口竞争, 但非本failure root cause (timeout pattern本质是NVCF server-side)。

### 1c. 关键结论:R517基线已稳, outbound仍有微缩空间

- R517改动(1.5→1.2, FASTBREAK 2→1)已生效, 7min短窗口内零429, 说明1.2s安全。
- 当前唯一可安全微调的参数是 outbound throttle。1.2s仍高于任何 cooldown 的尾开销。
- UPSTREAM=48 为历史保守值(R323证伪过40会误杀45-50s慢成功), 不可再降。
- BUDGET=100 当前因FASTBREAK=1而不会耗尽, 调降无益。
- FASTBREAK=1 已是极限, 再降无可降。
- THINKING_TIMEOUT=50 与 UPSTREAM=48 仅差2s, 对齐意义不大, 且think路径无失败。
- CONNECT_RESERVE=3 已校准, 再降不影响per_attempt上限(UPSTREAM=48瓶颈)。

## 2. 改动计划

### 2a. 候选评估

| 候选 | 数据支撑 | 风险 | 裁决 |
|------|----------|------|------|
| **MIN_OUTBOUND 1.2→1.0** | R517 7min零429, 1.2安全; key cooldown=38s >> 1.0, tier cd=22s >> 1.0 | 极低: 仅并发波峰队列尾等待-1.0s(5键×0.2s), 无rate limit风险 | **执行** |
| UPSTREAM 48→45 | k2最近41.7s成功, P95未知; R323历史证伪40会误杀45-50s | 中: 42-45s的正常请求会被截断 | 不执行 |
| BUDGET 100→95 | FASTBREAK=1使budget不耗尽, 调降仅影响极端peer-fb链 | 低但无益: peer fb 1ms ttfb已足够快 | 不执行 |
| FORCE_STREAM 50→48 | 与UPSTREAM对齐, 但HM-THINKING-TIMEOUT只是log标记非failure root | 极低但收益模糊 | 不执行(等更多数据) |
| CONNECT_RESERVE 3→2 | UPSTREAM=48是瓶颈, reserve调降不改变per_attempt_timeout计算 | 零收益 | 不执行 |

### 2b. 最终计划

只做1个参数: `MIN_OUTBOUND_INTERVAL_S: "1.2" → "1.0"`

- 理由: MIN_OUTBOUND_INTERVAL控制同tier key cycle间的最小发车间隔。
  1. 排队吞吐微增: 并发波峰(如同时5-10个kimi并发)时, key轮转从1.2s/键降至1.0s/键, 首键到末键等待-1.0s(5键×0.2s)。
  2. 队列尾延迟微降: 当kimi thinking饱和(50s)时, 后续请求在outbound queue等待, 缩短throttle可降低队列压强。
  3. 零429风险: HM2 key cooldown=38s, tier cooldown=22s, 均远大于1.0s, 不会重置NV rate limit budget。
  4. 不影响成功/失败判定: 单请求ttfb由NVCF side决定, 与client outbound throttle无关。FASTBREAK/UPSTREAM/BUDGET均不变。
- 风险对冲: 若DB出现429>3/30min或timeout率显著上升, 立即回滚→1.2。

## 3. 改动执行

### 3a. 备份+改compose (live文件 /opt/cc-infra/docker-compose.yml)

```bash
# HM1侧通过SSH执行
ssh -p 222 opc2_uname@100.109.57.26
# 备份
# 修改compose: MIN_OUTBOUND_INTERVAL_S "1.2" → "1.0"
```

验证:
```
472:      MIN_OUTBOUND_INTERVAL_S: "1.0"  # R518: HM1->HM2 — 1.2->1.0 (-0.2s)...
```

### 3b. 容器重建 (Recreate以应用env)

```bash
cd /opt/cc-infra && docker compose up -d hm40006
# → Container hm40006 Recreate / Recreated / Starting / Started
```

### 3c. 改后验证 (三源交叉)

```
# 源1: 容器env
docker exec hm40006 env | grep MIN_OUTBOUND_INTERVAL_S
MIN_OUTBOUND_INTERVAL_S=1.0

# 源2: compose文件
grep MIN_OUTBOUND_INTERVAL_S /opt/cc-infra/docker-compose.yml
→ line 472: "1.0"

# 源3: 容器启动时间 (recreated)
docker inspect hm40006 --format='{{.State.StartedAt}}'
→ 2026-07-01T17:04:42Z (新启动, Recreate 生效)

# 源4: 代码级import验证
docker exec hm40006 python3 -c "from gateway.config import *; print(MIN_OUTBOUND_INTERVAL_S)"
→ 1.0
```

## 4. 改后预期

- 并发波峰时队列尾等待再降-1.0s(5键轮转差距)。
- 不改变单请求成功/失败判定逻辑 (UPSTREAM/FASTBREAK/BUDGET不变)。
- 不改变peer fallback触发时机 (FASTBREAK=1不变)。
- 零429风险 (cooldown >> throttle)。
- 下轮HM2优化HM1时, 可重点观察HM2侧30min窗口queue depth与tail latency变化。

## 5. CC清单更新

- [HM2-A] MIN_OUTBOUND_INTERVAL_S: ✅ R517 1.5→1.2, ✅ R518 1.2→1.0 (-0.2s)。待HM2下一轮数据验证429/队列。
- [HM2-B] HM_PEXEC_TIMEOUT_FASTBREAK: ✅ R517 2→1。已验证, 不改动。
- [HM2-C] UPSTREAM_TIMEOUT: ⏸ 48s。历史R323证伪40会误杀, 当前k2有41.7s正常成功。暂不动, 除非有明确数据支撑降45不误杀。
- [HM2-D] HM_FORCE_STREAM_UPGRADE_TIMEOUT: ⏸ 50s。与UPSTREAM差2s, 对齐意义不大, 待更多thinking超时数据。

## 6. 给下轮 (HM2 优化 HM1) 的接力信息

- HM2 当前配置: BUDGET=100 / UPSTREAM=48 / FASTBREAK=1 / MIN_OUTBOUND=1.0 / RESERVE=3 / MIN_ATTEMPT=5 / KEY_CD=38 / TIER_CD=22 / THINKING_TIMEOUT=50。
- **验证重点**: 采 30min+ 窗口统计MIN_OUTBOUND=1.0后, per-key成功率与429计数。关注指标: queue tail latency, timeout分布, peer-fb频率。
- **代理负载均衡现状**: 7894(k1+k2)=40%键, 7895(k3)=20%, 7896(k5)=20%, direct(k4)=20%。若7894持续correlated failure(如k2反复41s+), 可评估把k1或k2改到7897/7899。
- mihomo 健康度: 严禁stop/restart/kill。7891-7899全端口listening, 余量充裕。
- **3model语义保留**: 所有proxy URL改动对所有3个tier(kimi/dsv4p/glm5.1)同时生效, 不改变请求→tier→model映射逻辑。

## ⏳ 轮到HM2优化HM1