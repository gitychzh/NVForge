# R2348: HM2→HM1 — ROLLBACK NVU_BIG_INPUT_COOLDOWN_S 60→90 + 根因分析

## TL;DR
R2347 (NVU_BIG_INPUT_COOLDOWN_S 90→60) 触发了一个隐藏的结构性缺陷：**HM1 的 big_input_breaker 在 cooldown 到期时进入 HALF_OPEN 状态后，没有 HALF-OPEN 探测机制**，而是直接让下一个超大 input 请求尝试 **所有 5 key (非 big-input)**，结果 NVCF 仍坏时浪费 ~52s，而非 R2347 预期的 ~1 ATE 省 ~170s。对比看 R2340 中 ${NVU_EMPTY_200_FASTBREAK=2}$ 才是 HM1 缺失的 fast-break。因此本次回滚到 90s 安全基线，并指出真正需要补的是 fast-break 而非缩短 cooldown。铁律：只改 HM1 不改 HM2。

---

## 一、R2347 部署后数据（post-R2347, post-restart, ~40min 窗口）

| 指标 | 数值 |
|------|------|
| 部署后总请求 | 13 req (kimi_nv 6, dsv4p_nv 3, glm5_2_nv 4) |
| 部署后 OK | 8 req (kimi_nv 5, dsv4p_nv 3, glm5_2_nv 0) |
| 部署后 SR | **61.5%** (13 req 窗口) |
| dsv4p_nv 部署后 | 3/3 100% OK ✅ |
| kimi_nv 部署后 | 5/6 OK (1 ATE: empty_200→fastbreak→all_keys_exhausted, 124s浪费) |
| glm5_2_nv 部署后 | **0/4 OK, 4 ATE** ❌（全部 big-input retry 超时 ~52s） |

### 关键 bad case (glm5_2_nv, input=325683c):
```
[10:03:20] NV-REQ mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True
[10:03:20] k5 timeout 26965ms -> k2 timeout 26073ms -> PEXEC-FASTBREAK (saved keys)
[10:04:13] NV-TIER-FAIL all 5 keys failed: timeout=2, elapsed=52188ms -> ABORT-NO-FALLBACK
[10:04:13] NV-BIGINPUT-FAIL big_input nv hang, breaker=('CLOSED', 1, 0) -> OPEN, cooldown=60s
[10:04:13] next req same input=325683c -> NV-BIGINPUT-FB-OPEN breaker OPEN, ATE instant
[10:05:07] cooldown expired (60s) -> breaker HALF-OPEN
[10:05:07] next req same input=325683c -> **NOT** big-input open (HALF-OPEN state => False)
[10:05:07] -> all 5 keys retry AGAIN, timeout AGAIN ~52s -> ATE
```

这里的问题：**cooldown=60s 到期后进入 HALF_OPEN，但 HALF_OPEN 在 `is_big_input_open()` 中返回 False，于是请求被放行到 NVCF，结果 NVCF 仍坏 -> 全 key timeout ~52s -> ATE**。如果 cooldown=90s，HALF_OPEN 更晚到来，节约 30s 的 key-timeout 浪费。但根本问题不是 cooldown 长度，而是 **HALF-OPEN 状态没有 probe 逻辑**：应该只试 **1 个 key** 探测 NVCF 是否恢复，而不是放全部 5 key。

---

## 二、根因：big_input_breaker.py 的 HALF-OPEN gap

### HM1 breaker 状态机（当前有 bug）：
```
CLOSED --(N fails)--> OPEN --(cooldown)--> HALF_OPEN --(no probe)--> CLOSED (implicit)
         ^                                                    |
         |____________________________________________________|
```

问题：`is_big_input_open()` 中 `now >= _open_until` 返回 False（即 HALF_OPEN 允许通行），但 **没有显式 probe 逻辑**：请求直接走正常 5 key 全 retry 路径。而 NVCF 仍坏时，这 5 key 每个 timeout ~26s = ~52s 总浪费。

### 正确的 breaker 状态机（R2349 建议修复）：
```
CLOSED --(N fails)--> OPEN --(cooldown)--> HALF_OPEN --(probe 1 key)--> 
                                                              |-- success --> CLOSED
                                                              |-- fail    --> OPEN (re-arm)
```

即：HALF_OPEN 状态下，**只允许 1 个 key 尝试（不循环）**，成功 → CLOSED，失败 → 重新 OPEN cooldown。

### 与 R2340 的对比
R2340 增加了 `${NVU_EMPTY_200_FASTBREAK=2}$`（empty_200 fast-break）用于 kimi_nv 的 empty_200 场景。glm5_2_nv 的问题是 **PEXEC timeout fast-break 已存在（R2284, PEXEC_FASTBREAK=2）**，但 big-input 流中该 fast-break 触发后 breaker 进入 OPEN，cooldown 到期后无 probe 导致二次浪费。

---

## 三、决策分析

| 方案 | 改动 | 风险 | 决策 |
|------|------|------|------|
| A. 将 cooldown 从 60 回滚到 90 | 改 compose，重启 container | 低，90s 是 11+ 轮验证基线 | ✅ **执行** |
| B. 改 big_input_breaker.py 加 HALF-OPEN probe（1 key） | 改源码，重启 container | 中，需充分测试，跨轮积累 | ❌ **留到 R2349** |
| C. 改 PEXEC_FASTBREAK 从 2→1 | 改 compose，重启 | 高，timeout 误伤正常请求 | ❌ 不采纳 |
| D. 改 BIG_INPUT_FAIL_N 从 2→1 | 改 compose，重启 | 高，过早 OPEN 误伤 | ❌ 不采纳 |
| E. 改 BIG_INPUT_THRESHOLD 从 250000→300000 | 改 compose，重启 | 高，zombie 在 257K-283K 范围会被放过 | ❌ 不采纳 |

最终决策：**执行 A：回滚 NVU_BIG_INPUT_COOLDOWN_S 60→90**（保守修复 restore 稳定基线）。B 标记为 R2349 代码级修复任务。

---

## 四、执行记录

### 4.1 回滚 compose

```bash
# HM1: ssh opc_uname@100.109.153.83 -p 222
# 修改前:
#   NVU_BIG_INPUT_COOLDOWN_S=60  # R2327 ... # R2347 (HM2->HM1): 90->60
# 修改后:
#   NVU_BIG_INPUT_COOLDOWN_S=90  # R2327 ... # R2348 (HM2->HM1): ROLLBACK 60->90

sed -i \
  's/NVU_BIG_INPUT_COOLDOWN_S=60 .*$/NVU_BIG_INPUT_COOLDOWN_S=90  # R2327 (HM2->HM1): 180->120. # R2348 (HM2->HM1): ROLLBACK 60->90. R2347 60s exposed HALF-OPEN probe gap: cooldown expiry -> all 5 keys timeout ~52s instead of 1 ATE saved ~170s. 90s = safe proven baseline./' \
  /opt/cc-infra/docker-compose.yml
```

### 4.2 重建容器
```bash
cd /opt/cc-infra && docker compose up -d --no-deps --force-recreate nv_gw
```
→ `Container nv_gw Recreated/Started`

---

## 五、验证记录（Post-rollback）

| 源 | 指标 | 数值 | 状态 |
|----|------|------|------|
| compose | NVU_BIG_INPUT_COOLDOWN_S | 90 | ✅ |
| 容器 env | NVU_BIG_INPUT_COOLDOWN_S | 90 | ✅ |
| 容器 StartedAt | 2026-07-25T02:13:18Z | ✅ 已更新 |
| 启动日志 | clean start, listening :40006 | ✅ |
| ERROR/WARN | 0 in first 50 lines | ✅ |

---

## 六、结论与 R2349 建议

1. **R2348 完成**：回滚 `NVU_BIG_INPUT_COOLDOWN_S` 60→90，restore 经过 11+ 轮验证的安全基线。

2. **真正根因**：HM1 `big_input_breaker.py` **缺少 HALF-OPEN probe 机制**。当前实现：
   - `is_big_input_open()`：`_open_until == 0.0` 或 `time.monotonic() >= _open_until` 都返回 False（允许通行）
   - 没有区分 HALF_OPEN vs CLOSED 的 probe 逻辑

3. **R2349 建议修复**（代码级，跨轮积累）：
   ```python
   # big_input_breaker.py 新增 HALF-OPEN probe:
   _half_open = False   # True when in HALF-OPEN (cooldown expired, probing)
   
   def is_big_input_open():
       # OPEN (cooldown still active) -> True (blocked)
       # HALF_OPEN (cooldown expired) -> False (allow 1 probe)
       # CLOSED -> False (normal)
       pass
   
   def is_big_input_probe():
       # return _half_open  # caller in upstream.py uses this to limit to 1 key
       pass
   
   def record_big_input_probe_result(success):
       # success -> CLOSED; fail -> OPEN (re-arm cooldown)
       pass
   ```
   修改点 2 个文件：`big_input_breaker.py`（新增状态机）+ `upstream.py`（HALF_OPEN 时只走 1 key，不 cycle）。

4. **铁律重申**：只改 HM1 不改 HM2。所有改动均在 HM1 `/opt/cc-infra` 完成，HM2 本地零改动。

---

## ⏳ 轮到HM1优化HM2
