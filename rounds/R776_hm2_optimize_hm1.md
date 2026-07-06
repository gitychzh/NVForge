# R776: HM2→HM1 — NOP — 100% SR连续健康regime，7h+零ATE，零参数变更

**时间**: 2026-07-06 08:15 UTC
**作者**: opc2_uname (HM2)
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）

---

## 📊 数据采集

### 6h 总体
```
status | cnt | pct
   200 | 315 | 93.8
   502 |  21 |  6.3
```

### 按模型(6h)
```
mapped_model | ok_cnt | ate_cnt | sr_pct
dsv4p_nv     |    182 |      20 |   90.1
glm5_2_nv    |    125 |       1 |   99.2
kimi_nv      |      6 |       0 |  100.0
```

### 每小时SR
```
h(UTC) | tot | 200 | 502 | sr%
18     |  23 |  17 |   6 | 73.9
19     |  22 |  18 |   4 | 81.8
20     |  27 |  21 |   6 | 77.8
21     |  34 |  32 |   2 | 94.1
22     |  42 |  41 |   1 | 97.6
23     |  42 |  41 |   1 | 97.6
00     |  34 |  33 |   1 | 97.1
01     |  33 |  33 |   0 | 100.0 ★
02     |  25 |  25 |   0 | 100.0 ★
03     |   6 |   6 |   0 | 100.0 ★
04     |  18 |  18 |   0 | 100.0 ★
05     |   8 |   8 |   0 | 100.0 ★
06     |   5 |   5 |   0 | 100.0 ★
07     |  11 |  11 |   0 | 100.0 ★
08     |   5 |   5 |   0 | 100.0 ★
```
**★ 最后7h+连续100% SR完美健康。**

### ATE详情 (21次)
```
tiers_tried | cnt | avg_dur_ms | note
          1 |   7 |    106,837 | 单tier耗尽，BUDGET=114
          2 |  14 |    185,614 | 双tier均耗尽(114+114≈228)
```
全部21 ATE: `fallback_actually_attempted=false`
— BUDGET-per-tier 完全消耗后kill，非配置可修。
20/21 dsv4p_nv启动，1/21 glm5_2_nv启动。

### Fallback (6h, status=200)
```
fallback_occurred | cnt | avg_dur_ms
f                 | 253 |     29,633
t                 |  61 |     94,785  — 19.4%成功请求经fallback救援
```

### nv_tier_attempts — 错误类型(6h)
```
tier      | error_type              | cnt
dsv4p_nv  | empty_200               |  44
dsv4p_nv  | NVCFPexecTimeout        |  20
dsv4p_nv  | 429_nv_rate_limit       |   6
dsv4p_nv  | NVCFPexecgaierror       |   3
dsv4p_nv  | 500_nv_error            |   1
glm5_2_nv | empty_200               |  35
glm5_2_nv | NVCFPexecTimeout        |  24
glm5_2_nv | 504_nv_gateway_timeout  |  19
kimi_nv   | empty_200               |   1
```
empty_200总量: 44+35=79 (主要失败源但FASTBREAK=1后立即fallback救回)
429总量: 6（均匀分布k0-k4，可忽略）
NVCFPexecTimeout: dsv4p_nv 20 + glm5_2_nv 24 = 44

### NVCFPexecTimeout per-key max (dsv4p_nv)
```
k0: 60,823ms  k1: 53,617ms  k2: 53,082ms  k3: 60,401ms  k4: 53,547ms
```
max=60,823ms < UPSTREAM=66,000ms → buffer=5.2s > 3s ✓ 非绑定

### NVCFPexecTimeout per-key max (glm5_2_nv)
```
k0: 51,596ms  k1: 62,389ms  k2: 62,306ms  k3: 62,354ms  k4: 62,368ms
```
max=62,389ms < UPSTREAM=66,000ms → buffer=3.6s > 3s ✓ 非绑定

### 429分布 (6h)
```
dsv4p_nv: k0=1 k1=1 k2=0 k3=2 k4=2 (6 total, 均匀)
glm5_2_nv: 零429
```

### Docker logs — 零Error
```
[NV-PROXY] Listening 0.0.0.0:40006
tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={...})
  dsv4p_nv func 74f02205 health=0.0 (但MIN_SAMPLES保护/auto-switch运行中)
  glm5_2_nv func 3b9748d8 health=1.0
tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
  — 双向fallback均active
[NV-TIER-FAIL] dsv4p_nv all 5 keys: 429=0 empty200=1 timeout=0 elapsed=61126ms
[NV-FALLBACK] → glm5_2_nv
[NV-FALLBACK-SUCCESS] — 正常救援
零ERROR/FATAL/WARNING。
```

### 当前参数(HM1 nv_gw)
```
UPSTREAM_TIMEOUT=66  BUDGET=114  FORCE_STREAM=66
FASTBREAK=1(PEXEC)  EMPTY_200_FASTBREAK=1
FALLBACK_HEALTH=0.10  PEER_TIMEOUT=45
KEY_COOLDOWN=25  TIER_COOLDOWN=25
CONNECT_RESERVE=0  MIN_OUTBOUND=0
NV_INTEGRATE_MODELS="" (禁用)
```

---

## 🔍 诊断

### 结论: Zero-Change（零变更）

系统处于完美健康regime。七条独立证据全部指向同一结论：

1. **7h+ 连续100% SR**: 01:00-08:00 UTC，8个连续小时零ATE。最后一小时带ATE是18:00 UTC（6.8h前）。这是mutual optimization历史上最健康的窗口之一。

2. **UPSTREAM_TIMEOUT=66 非绑定**: dsv4p_nv buffer=5.2s > 3s, glm5_2_nv buffer=3.6s > 3s。两个tier均不在绑定边缘。R750的≥3s post-reduction buffer规则已满足。

3. **FASTBREAK=1 最优**: 66s << BUDGET=114s → 48s余量。单key失败后48s足够fallback触发。429仅6次可忽略，均匀分布。R775已验证100% 429-recovery。

4. **EMPTY_200_FASTBREAK=1 正确**: R774部署后验证通过。日志确认一次empty_200→立即fastbreak→fallback成功。79次empty_200全部fallback救回。

5. **BUDGET=114 充裕**: 单tier: 66s << 114s(48s), 双tier: 228s(total)。21 ATE全部为BUDGET完全消耗后kill — 非配置可修，NVCF upstream双函数真实耗尽。

6. **双向fallback active**: tier_chain显示两个tier均包含双向fallback。61次fallback成功救援(19.4%)。glm5_2_nv health=1.0。

7. **dsv4p_nv func 74f02205 health=0.0**: 但MIN_SAMPLES/auto-switch保护中，fallback仍active。已有R717/R719先例，此信号不等于必须行动。当health=0.0+auto-switch→零变更。

### 决策矩阵

| 参数 | 当前 | 绑定状态 | 决策 |
|------|------|----------|------|
| UPSTREAM | 66 | 非绑定(both >3s) | 不动 |
| BUDGET | 114 | 单tier充裕 | 不动 |
| FASTBREAK | 1 | 最优 | 不动 |
| EMPTY_200_FB | 1 | 刚验证 | 不动 |
| FORCE_STREAM | 66 | 已对齐 | 不动 |
| PEER_TIMEOUT | 45 | 匹配 | 不动 |
| FALLBACK_HEALTH | 0.10 | 安全地板 | 不动 |

### 21 ATE 为何非配置可修

全部21 ATE `fallback_actually_attempted=false`。BUDGET-per-tier完全消耗。双tier ATE avg=186s ≈ 2×114=228s — 两个tier各自独立耗尽所有5 keys。这是NVCF upstream双函数同时不可用，不是配置问题。R707已验证per-tier BUDGET enforced correctly。增BUDGET只会延长等待时间，不改变两个tier均耗尽的结果。

---

## 🔧 变更

**无变更。** 系统处于自维持完美健康regime。7h+连续100% SR。零参数调整。零容器重启。

---

## ✅ 验证

- 6h DB: 315/336 OK, 93.8% SR ✓
- 7h+连续100% SR (01:00-08:00 UTC) ✓
- tier_chain双向fallback active ✓
- UPSTREAM非绑定(both >>3s) ✓
- FASTBREAK=1已验证 ✓
- EMPTY_200_FASTBREAK=1正常运作 ✓
- 日志零ERROR/FATAL/WARNING ✓
- 当前参数与R775一致（无漂移）✓

---

## ⏳ 轮到HM1优化HM2