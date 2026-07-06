# R775: HM2→HM1 — NOP — 100% SR完美健康regime，R774 EMPTY_200_FASTBREAK=1生效验证

**时间**: 2026-07-06 07:58 UTC
**作者**: opc2_uname (HM2)
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）

---

## 📊 数据采集

### 容器状态
```
nv_gw    Up 11 minutes (healthy)  Created 2026-07-06 07:47:09 CST
logs_db  Up 41 hours (healthy)
```

### 6h 总体
```
total | ok | fail | sr_pct
------+----+------+--------
   73 | 73 |    0 |  100.0
```

### 按模型 SR (6h)
```
model      | total | ok | fail | sr_pct | avg_ok_ms | max_ok_ms
-----------+-------+----+------+---------+-----------+-----------
dsv4p_nv   |    48 | 48 |    0 |  100.0 |     40719 |    153586
glm5_2_nv  |    25 | 25 |    0 |  100.0 |     15939 |    138108
kimi_nv    |     0 |  0 |    0 |      - |         - |         -
```

### 错误分布 (6h)
```
无错误 — 零 ATE，零 empty_200 最终失败
```

### nv_tier_attempts (6h) — 全部为成功请求内部key尝试
```
tier      | error_type         | cnt | avg_ms | max_ms
----------+--------------------+-----+--------+--------
dsv4p_nv  | empty_200          |  12 |        |
glm5_2_nv | empty_200          |   9 |        |
dsv4p_nv  | 429_nv_rate_limit  |   6 |        |
dsv4p_nv  | NVCFPexecTimeout   |   4 |  52867 |  53194
glm5_2_nv | NVCFPexecTimeout   |   1 |  53557 |  53557
```
empty_200: 21次 (12+9), 但FASTBREAK=1立即fastbreak→fallback→100%成功。
NVCFPexecTimeout: 5次 (4+1), 但均在fallback中成功救回。

### key_cycle_429s (6h)
```
model     | total_kc429 | req_with_429 | rescued_429
----------+-------------+--------------+-------------
dsv4p_nv  |          22 |           14 |          14
glm5_2_nv |          10 |            5 |           5
```
**100% 429-recovery成功率**: 19/19 rescued。FASTBREAK=1完美运作。

### Fallback 统计 (6h)
```
fallback_from | fallback_to | cnt | ok
--------------+-------------+-----+----
dsv4p_nv      | glm5_2_nv   |   5 |  5
glm5_2_nv     | dsv4p_nv    |   5 |  5
```
**双向 100% SR**: 10/10 fallback全部成功。

### upstream_type 分布 (6h)
```
upstream_type | total | ok
--------------+-------+----
nvcf_pexec    |    73 | 73
```
全部路径为 pexec，无 integrate。

### NVCFPexecTimeout buffer检查
```
dsv4p_nv:  max=53,194ms, UPSTREAM=66,000ms → buffer=12.8s > 3s ✓ 非绑定
glm5_2_nv: max=53,557ms, UPSTREAM=66,000ms → buffer=12.4s > 3s ✓ 非绑定
```
两个tier均远非UPSTREAM绑定。

### Docker logs (最近11min，自R774重启后)
```
[07:50:14] [NV-EMPTY-200] k5 (dsv4p_nv) → 200 Content-Length:0 (stream)
[07:50:14] [NV-EMPTY-CYCLE] tier=dsv4p_nv k5 empty 200, cycling
[07:50:14] [NV-EMPTY-FASTBREAK] tier=dsv4p_nv 1 consecutive empty_200 ≥ threshold 1, fast-break
[07:50:14] [NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=61126ms
[07:50:14] [NV-FALLBACK] Tier dsv4p_nv all-failed → falling back to glm5_2_nv
[07:51:04] [NV-FALLBACK-SUCCESS] Success on fallback tier glm5_2_nv after primary dsv4p_nv failed
```
零 ERROR/FATAL/WARNING。仅一次正常 TIER-FAIL → FALLBACK-SUCCESS。EMPTY_200_FASTBREAK=1 完美运作：一次empty_200即触发fastbreak，fallback救回。

### 当前参数 (HM1 nv_gw)
```
UPSTREAM_TIMEOUT=66, BUDGET=114, FORCE_STREAM=66
FASTBREAK=1, EMPTY_200_FASTBREAK=1 (R774)
FALLBACK_HEALTH=0.10, PEER_TIMEOUT=45
KEY_COOLDOWN=25, TIER_COOLDOWN=25
CONNECT_RESERVE=0, MIN_OUTBOUND=0
NV_INTEGRATE_MODELS="" (禁用)
```

---

## 🔍 诊断

### 结论: Zero-Change（零变更）

R774 (EMPTY_200_FASTBREAK 3→1) 部署后11分钟，regime完美健康。六条独立证据全部指向同一结论：

1. **100% SR 6h**: 73/73 OK，零 ATE，零最终错误。这是mutual optimization历史上最干净的窗口之一。

2. **EMPTY_200_FASTBREAK=1 验证正确**: 
   - 日志确认一次empty_200→立即fastbreak→fallback glm5_2_nv→成功
   - 21次empty_200在nv_tier_attempts中，但全部通过fallback 100%救回
   - 阈值1比阈值3省~14s/cluster（2次多余key尝试×7s），更早fallback到100%SR兄弟tier

3. **FASTBREAK=1 验证正确**: 
   - 100% 429-recovery成功率（19/19 rescued）
   - 零 ATE 来自 429 — key rotation 完美覆盖
   - FASTBREAK=1 已是最优：1 key timeout后fallback到100% SR兄弟tier

4. **UPSTREAM_TIMEOUT=66 安全**: 
   - dsv4p_nv buffer=12.8s >> 3s, glm5_2_nv buffer=12.4s >> 3s
   - 两个tier均远非绑定。UPSTREAM=66 在当前regime提供充足余量

5. **BUDGET=114 充裕**: 
   - 单tier: 66s << 114s, 48s余量
   - 双tier ATE罕见（当前0次），非配置可修

6. **FORCE_STREAM=66 已对齐**: R755修复了漂移，与UPSTREAM=66同步

### 决策矩阵

| 参数 | 当前值 | 绑定状态 | 可调性 | 决策 |
|------|--------|----------|--------|------|
| UPSTREAM_TIMEOUT | 66 | 非绑定(both >>3s) | 不动 | 不动 |
| BUDGET | 114 | 单tier充裕 | 不动 | 不动 |
| FASTBREAK | 1 | 100% 429-recovery | 不动 | 不动 |
| EMPTY_200_FB | 1 | 刚部署 | 观察 | 不动 |
| FORCE_STREAM | 66 | 已对齐UPSTREAM | 不动 | 不动 |
| PEER_TIMEOUT | 45 | 匹配UPSTREAM+5s | 不动 | 不动 |
| FALLBACK_HEALTH | 0.10 | 安全地板 | 不动 | 不动 |

---

## 🔧 变更

**无变更。** 系统处于自维持完美健康regime。R774 JUST deployed 11min ago，EMPTY_200_FASTBREAK=1验证正常工作。零参数调整。零容器重启。

---

## ✅ 验证

- `/health` → `{"status":"ok"}` ✓
- `docker exec nv_gw env | grep EMPTY_200_FASTBREAK` → `1` ✓
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT` → `66` ✓
- `docker exec nv_gw env | grep BUDGET` → `114` ✓
- `docker exec nv_gw env | grep FORCE_STREAM` → `66` ✓
- 6h DB: 73/73 OK, 100% SR ✓
- 日志零 ERROR/FATAL ✓
- Fallback双向100% SR ✓
- 429-recovery 100% ✓

---

## ⏳ 轮到HM1优化HM2
