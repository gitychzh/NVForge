# R2286: HM2优化HM1 — big_input_breaker模型过滤: dsv4p_nv不再被glm5_2_nv的breaker误杀

## 数据采集 (6h窗口: ~2026-07-23 06:35-12:45 UTC, 含R2285重启后)

| 指标 | 数值 |
|---|---|
| 总请求 | 43 |
| 成功 | 14 |
| 失败 | 29 |
| 成功率 | 32.6% |

### 错误分布

| 错误类型 | dsv4p_nv | glm5_2_nv |
|---|---|---|
| ATE (all_tiers_exhausted) | 21 | 8 |

### 每模型SR

| 模型 | 总请求 | 成功 | 成功率 | 平均延迟(ms) |
|---|---|---|---|---|
| dsv4p_nv | 23 | 2 | 8.7% | 20518 |
| glm5_2_nv | 20 | 12 | 60.0% | 34665 |

### 0-tier_attempts ATE分析

```
dsv4p_nv ATE: 21个全部0 tier_attempts, duration 6-11ms, 373K input
glm5_2_nv ATE: 8个全部0 tier_attempts, 7ms(@381K) 或 35087ms(@373K)
```

- **dsv4p_nv**: 21个ATE全部瞬间拒绝(6-11ms), 0 tier_attempts, 组成时间簇(~每30min一批3个)
- **glm5_2_nv**: 8个ATE全部0 tier_attempts, 4个instant-reject(7ms, 381K>370K threshold), 4个peer-fb rescue(35087ms, 373K)

### 429速率限制分析

| key_cycle_429s | 请求数 |
|---|---|
| 0 | 42 |
| 1 | 1 |
| 2+ | 0 |

## 根因分析

**R2285后dsv4p_nv仍然91.3%失败率 — 根因不是KEY_COOLDOWN_S, 而是big_input_breaker误杀:**

```
execute_request() 在 tier loop 之前有一个 big_input_breaker 检查 (upstream.py:1369-1377):

    if (big_input_breaker.is_big_input(_bi_input)
            and big_input_breaker.is_big_input_open()):
        → 返回 all_tiers_exhausted, 0 tier_attempts

这个检查没有过滤模型! 当 big_input_breaker 是 OPEN 状态时,
ALL 模型的大输入请求 (>370K threshold) 都被直接拒绝,
不管 NVU_BIG_INPUT_MODELS 配置的是哪个模型.
```

**实际现象印证:**

1. **big_input_breaker状态**: OPEN (从glm5_2_nv大输入失败触发)
2. **NVU_BIG_INPUT_MODELS**: `glm5_2_nv` — 只有glm5_2_nv应该被breaker影响
3. **dsv4p_nv请求**: 全部21个请求input=371K-379K > 370K threshold
4. **结果**: dsv4p_nv请求在execute_request()入口就被breaker拦截, 0 tier_attempts, 6-11ms, 从未到达tier loop
5. **R2285的KEY_COOLDOWN_S=0是正确的**: 但breaker先于tier loop拦截, 所以KEY_COOLDOWN_S=0的效果完全被掩盖

**代码缺陷**: `execute_request()` 的 big_input_breaker 检查缺少 `mapped_model in NVU_BIG_INPUT_MODELS` 条件。breaker的模型列表配置了但从未被检查 — 任何模型的大输入请求都会被拦截。

## 修复

### 代码变更 (upstream.py:1370-1371)

```python
# 修复前:
    if (big_input_breaker.is_big_input(_bi_input)
            and big_input_breaker.is_big_input_open()):

# 修复后:
    if (big_input_breaker.is_big_input(_bi_input)
            and mapped_model in big_input_breaker.NVU_BIG_INPUT_MODELS
            and big_input_breaker.is_big_input_open()):
```

**文件**: `/opt/cc-infra/proxy/nv-gw/gateway/upstream.py` (容器内挂载)
**变更类型**: 代码补丁, 非参数变更

**逻辑**: 只有 breaker 配置的模型 (`NVU_BIG_INPUT_MODELS=glm5_2_nv`) 在 breaker OPEN 时被拦截。其他模型 (dsv4p_nv, kimi_nv, minimax_m3_nv) 的大输入请求正常进入 tier loop。

**为什么这是HM1修复不是HM2**: 这是HM1 gateway代码的bug — HM1的 `NVU_BIG_INPUT_MODELS` 配置了模型过滤但代码没有使用它。修复后HM1正确行为: 只对配置的模型应用breaker。

## 验证

```
$ docker exec nv_gw sed -n '1369,1372p' /app/gateway/upstream.py
    _bi_input = metrics.get("total_input_chars", 0) or 0
    if (big_input_breaker.is_big_input(_bi_input)
            and mapped_model in big_input_breaker.NVU_BIG_INPUT_MODELS
            and big_input_breaker.is_big_input_open()):

$ docker exec nv_gw env | grep NVU_BIG_INPUT_MODELS
NVU_BIG_INPUT_MODELS=glm5_2_nv

$ curl -s -o /dev/null -w "%{http_code}" http://localhost:40006/health
200
```

**重启后1h数据**: 4个glm5_2_nv请求 (380K-383K input) 正常进入tier loop, non-zero tier_attempts。breaker因重启重置, 当glm5_2_nv再次触发breaker OPEN时, 只有glm5_2_nv会被拦截, dsv4p_nv不受影响。

## 约束检查

- [x] Iron law: 只改HM1代码, 绝不改HM2本地
- [x] 代码补丁, 非参数变更 (no compose change)
- [x] 不改变现有行为: glm5_2_nv breaker行为不变, 只修复了误杀其他模型
- [x] 与R2285 (KEY_COOLDOWN_S=0) 配合: 现在dsv4p_nv可以正常进入tier loop, KEY_COOLDOWN_S=0的5-key效果可以发挥
- [x] 全局预算不变: 所有compose参数不变

## 预期效果

- dsv4p_nv: 不再被big_input_breaker误杀 → 输入>370K的请求正常进入tier loop → 配合R2285的5-key能力, 预期SR从8.7% → 50%+
- glm5_2_nv: 行为不变, breaker OPEN时仍被拦截 (符合设计意图)
- 两模型独立: dsv4p_nv的SR不再受glm5_2_nv breaker状态影响

## ⏳ 轮到HM1优化HM2