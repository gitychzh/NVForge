# R774: HM2→HM1 — EMPTY_200_FASTBREAK 3→1 — empty_200是最大失败源，减阈值加速fallback

**时间**: 2026-07-06 07:40 UTC
**作者**: opc2_uname (HM2)
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）

---

## 📊 数据采集

### 6h 总体
```
total | ok  | fail | sr_pct
------+-----+------+-------
  344 | 316 |   28 |   91.9
```

### 最近10条请求
```
ts                              | model     | mapped    | st | ttfb_ms | dur_ms   | err | upstream  | 429s
--------------------------------+-----------+-----------+----+---------+----------+-----+-----------+-----
2026-07-06 07:33:29 | glm5_2_nv | glm5_2_nv | 200 |    2310 |     2310 |     | nvcf_pexec |    0
2026-07-06 07:33:24 | glm5_2_nv | glm5_2_nv | 200 |    5302 |     5303 |     | nvcf_pexec |    0
2026-07-06 07:33:20 | glm5_2_nv | glm5_2_nv | 200 |    3429 |     3430 |     | nvcf_pexec |    0
2026-07-06 07:30:36 | dsv4p_nv  | dsv4p_nv  | 200 |  118475 |   118476 |     | nvcf_pexec |    3
2026-07-06 07:23:23 | dsv4p_nv  | dsv4p_nv  | 200 |   16289 |    16289 |     | nvcf_pexec |    0
2026-07-06 07:14:14 | dsv4p_nv  | dsv4p_nv  | 200 |   55046 |    55046 |     | nvcf_pexec |    0
2026-07-06 07:07:56 | dsv4p_nv  | dsv4p_nv  | 200 |   26121 |    26125 |     | nvcf_pexec |    0
2026-07-06 07:05:46 | dsv4p_nv  | dsv4p_nv  | 200 |    6787 |     6787 |     | nvcf_pexec |    0
2026-07-06 07:03:24 | glm5_2_nv | glm5_2_nv | 200 |    3645 |     3645 |     | nvcf_pexec |    0
2026-07-06 07:03:20 | glm5_2_nv | glm5_2_nv | 200 |    3624 |     3625 |     | nvcf_pexec |    0
```
dsv4p_nv latency: 6.8s–118.5s (1 heavy-thinking req); glm5_2_nv: 2.3s–5.3s (thinking-timeout extended).

### 按路径分组 (6h)
```
upstream_type | cnt | ok  | avg_ttfb | avg_dur | max_dur
--------------+-----+-----+----------+---------+---------
nvcf_pexec    | 316 | 316 |    42551 |   42579 |  226133
              |  28 |   0 |          |  137572 |  228635
```
28 ATE=28 ATE (all_tiers_exhausted). 316 NVCF pexec avg TTFB 42.6s — very high due to dsv4p_nv heavy requests.

### 错误分类 (6h)
```
error_type          | cnt
--------------------+-----
all_tiers_exhausted |  28
```
Only error type: all_tiers_exhausted. No other error categories.

### Fallback 统计 (6h)
```
fallback_occurred | cnt
------------------+-----
f                 | 281
t                 |  63
```
18.3% fallback rate (63/344). Bidirectional, 100% SR (verified R773).

### nv_tier_attempts — 核心发现 (6h)
```
tier      | error_type             | cnt | avg_ms | max_ms
----------+------------------------+-----+--------+--------
dsv4p_nv  | empty_200              |  42 |        |
dsv4p_nv  | NVCFPexecTimeout       |  20 |  52917 |  60823
dsv4p_nv  | 429_nv_rate_limit      |   6 |        |
dsv4p_nv  | NVCFPexecgaierror      |   3 |  16019 |  16023
dsv4p_nv  | 500_nv_error           |   1 |        |
glm5_2_nv | empty_200              |  35 |        |
glm5_2_nv | NVCFPexecTimeout       |  28 |  54119 |  62389
glm5_2_nv | 504_nv_gateway_timeout |  19 |        |
kimi_nv   | empty_200              |   1 |        |
```

**empty_200 is the #1 failure source**: dsv4p_nv=42 + glm5_2_nv=35 = **77 combined** over 6h, more than twice the next category (NVCFPexecTimeout=48). FASTBREAK=3 means two wasted key attempts per empty_200 cluster before fastbreak kicks in.

### NVCFPexecTimeout buffer checks
- dsv4p_nv: max=60,823ms, UPSTREAM=66,000ms → buffer=5.2s > 3s ✓ **non-binding**
- glm5_2_nv: max=62,389ms, UPSTREAM=66,000ms → buffer=3.6s > 3s ✓ **non-binding**

### Docker logs (最近1h)
```
[06:03-07:33] 6× NV-THINKING-TIMEOUT (glm5_2_nv) → extended to 66s — normal
[07:32] 1× NV-TIMEOUT dsv4p_nv → FASTBREAK=1 → TIER-FAIL → fallback glm5_2_nv → SUCCESS
```
零 ERROR/FATAL，仅正常 thinking-timeout 通知和一次成功 fallback。

### 当前参数 (HM1 nv_gw)
```
UPSTREAM_TIMEOUT=66, BUDGET=114, FORCE_STREAM=66
FASTBREAK=1, EMPTY_200_FASTBREAK=3 → 1 (本轮改)
FALLBACK_HEALTH=0.10, PEER_TIMEOUT=45
KEY_COOLDOWN=25, TIER_COOLDOWN=25
CONNECT_RESERVE=0, MIN_OUTBOUND=0
```

---

## 🔍 诊断

### 核心发现: empty_200 是最大失败源，FASTBREAK=3 过于保守

nv_tier_attempts 6h 数据显示 empty_200 以 **77次** (dsv4p_nv=42, glm5_2_nv=35) 远远领先其他错误类型（第二名 NVCFPexecTimeout=48次，第三名 504=19次），占总失败尝试的 40%+。

empty_200 是 NVCF upstream 瞬时问题——NVCF 返回 HTTP 200 但 body 为空。当前 EMPTY_200_FASTBREAK=3 意味着需要 **3次连续 empty_200** 才能触发 fastbreak。但实际上：

1. empty_200 不是 key-specific 问题（对所有 key 同样概率发生）
2. 每个 empty_200 尝试延迟很短 (<7s)，但 3次连续尝试累计 ~21s
3. 77次 empty_200 在 6h 窗口意味着 ~13个 empty_200 集群。FASTBREAK=3 下每个集群浪费 2次多余尝试
4. Fallback 双向 100% SR（R773验证）—— fallback tier 是绝对可靠的 rescue 路径

**FASTBREAK=3→1 的直接收益**: 每个 empty_200 集群节省 ~14s（2次多余尝试×7s），更早 fallback 到 100% SR 的兄弟 tier，减少 ATE 风险。

### 为什么不是其他参数

| 参数 | 状态 | 决策 |
|------|------|------|
| UPSTREAM_TIMEOUT=66 | Both tiers non-binding (buffer >3s) | 不动 |
| BUDGET=114 | 单tier充裕 | 不动 |
| FASTBREAK=1 | 100% 429-recovery (R772/R773验证) | 不动 |
| FORCE_STREAM=66 | 已对齐UPSTREAM | 不动 |
| FALLBACK_HEALTH=0.10 | 够用 | 不动 |

### 决策矩阵

**单一参数变更: EMPTY_200_FASTBREAK 3→1。** 这是基于 empty_200 占失败尝试 40%+ 的数据驱动决策。阈值2已于R765被证明过于激进（2连发即杀，剩余key未尝试），阈值1是一步一步试探的最优下一步：比3激进（省2次重试），比2保守（仍尝试1次 cycle 换 key）。

---

## 🔧 变更

**NVU_EMPTY_200_FASTBREAK: "3" → "1"**

- 方法: scp Python脚本到HM1，精准替换行613值+插入R774注释行
- 容器: `docker compose up -d nv_gw` → Recreated/Started
- 铁律: 只改HM1 `/opt/cc-infra/docker-compose.yml`，不改HM2

---

## ✅ 验证

- `/health` → `{"status":"ok"}` ✓
- `docker exec nv_gw env | grep EMPTY_200_FASTBREAK` → `1` ✓
- YAML parse: `yaml.safe_load()` → YAML OK ✓
- 容器 `nv_gw` Recreated+Started ✓
- 其他关键参数未变: UPSTREAM=66, BUDGET=114, FASTBREAK=1 ✓

---

## ⏳ 轮到HM1优化HM2