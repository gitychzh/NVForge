# R-dsv4f-adaptive: pexec-first 自适应路径选择 — integrate 连续 529 后跳过

**Date:** 2026-08-04
**Container:** dsvf0731_nv40666 (port 40666, HM2)
**Commit:** (this round)

## 背景

R-dsv4f-dynamic 的 `attempt_idx % 2` 盲目交替 pexec↔integrate 在 integrate 持续 529 时浪费 ~50% 的尝试。2h 窗口数据显示:

- integrate tier_attempts: **0% SR** (71/71 全 529), 平均延迟 **119.82s**
- pexec tier_attempts: 50% SR, 平均延迟 **33.78s**
- 每次交替到 integrate 浪费 ~86s, 在 180s budget 内少试 2-3 次 pexec
- 529 占总错误的 **50.4%** — NVCF 账户级过载是主要故障

## 改动

### upstream.py `_try_dsv4f_dynamic_keys()` — 4 处补丁

**1. pexec-first 策略**: 替换 `use_integrate = (attempt_idx % 2 == 1)` 为自适应逻辑:
- 默认全走 pexec
- pexec 连续 N 次 529 (`NVU_DSV4F_PEXEC_CONSEC_529=3`) 后才尝试 integrate
- integrate 连续 M 次 529 (`NVU_DSV4F_INTEG_529_SKIP=2`) 后跳过剩余 integrate

**2. 529 追踪**: 在 cycling 分支新增 per-path 连续 529 计数:
```python
if resp.status == 529:
    if use_integrate:
        _integ_consecutive_529 += 1
        if _integ_consecutive_529 >= _INTEG_529_SKIP:
            _integrate_skipped = True
    else:
        _pexec_consecutive_529 += 1
else:
    _pexec_consecutive_529 = 0
    _integ_consecutive_529 = 0
```

**3. 成功日志**: 新增 adaptive 状态 (pexec_529, integ_529, integ_skipped)

**4. 启动日志**: 显示 pexec-first 策略参数

### 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `NVU_DSV4F_PEXEC_CONSEC_529` | 3 | pexec 连续 529 多少次后才尝试 integrate |
| `NVU_DSV4F_INTEG_529_SKIP` | 2 | integrate 连续 529 多少次后跳过剩余 integrate |

## 数据验证

### Before/After 对比 (补丁前 53min vs 补丁后)

| 指标 | 补丁前 | 补丁后 | 改善 |
|------|--------|--------|------|
| pexec SR | 61.1% | 78.6% | +17.5pp |
| pexec avg latency | 34.28s | 10.40s | -70% |
| pexec max latency | 173.41s | 43.70s | -75% |
| integrate 请求数 | 22 | 2 | -91% |
| integrate avg latency | 183.77s | 9.73s | -95% |

### E2E 测试 (15 次请求)
- 13/15 = **86.7% SR** (补丁前 ~75%)
- 成功请求延迟: 2.8-9.8s (补丁前 2.8-79.6s)
- 502 请求延迟: 10-43.7s (补丁前 420s+)

### 日志验证
自适应逻辑正确工作:
- pexec 成功时: "succeeded after N cycle attempts (pexec_529=N, integ_529=0, integ_skipped=False)"
- pexec 全 529 后尝试 integrate: "attempt 4/7: k4 path=integrate"
- integrate 529 后跳过: 回到 pexec ���续尝试

## 文件改动

| 文件 | 改动 | 说明 |
|------|------|------|
| `gateway/upstream.py` | ~30 行改动 | pexec-first 自适应 + 529 追踪 + 日志增强 |
