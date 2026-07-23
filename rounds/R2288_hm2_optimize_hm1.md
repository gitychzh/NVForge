# R2288: HM2优化HM1 — NVU_BIG_INPUT_COOLDOWN_S 2100→900 (35min→15min)

## 数据采集 (6h窗口: ~2026-07-23 06:35-12:45 UTC, 含R2286重启后)

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

## 根因分析

R2286修复了模型过滤bug后，dsv4p_nv不再被big_input_breaker误杀。但glm5_2_nv仍然有8个ATE（全部0 tier_attempts），其中4个是instant-reject（7ms, 381K>370K threshold），4个是peer-fb rescue（35087ms, 373K）。

**关键发现：7个phantom ATE（status=200, tier_attempts=0）由`NVU_BIG_INPUT_COOLDOWN_S=2100`（35分钟）造成：**

1. **breaker workflow**: glm5_2_nv大输入请求失败（5次，`NVU_BIG_INPUT_FAIL_N=5`）→ breaker OPEN → 此后35分钟内所有glm5_2_nv大输入请求被直接拒绝（0 tier_attempts）
2. **R2286模型过滤修复后**: dsv4p_nv不再受影响，但glm5_2_nv的请求在breaker OPEN的35分钟内仍然被拦截
3. **35分钟太长**: 2100s = 35min。在R2286模型过滤后，breaker只影响glm5_2_nv，但cooldown仍然长达35分钟——一个很短的glm5_2_nv大输入失败burst就导致此后35分钟所有glm5_2_nv大输入请求被拒绝
4. **30min窗口内0 dsv4p_nv流量**: 无法验证R2286模型过滤是否生效（dsv4p_nv在30min内没有请求）

## 修复

| 参数 | 旧值 | 新值 | 变更 |
|---|---|---|---|
| NVU_BIG_INPUT_COOLDOWN_S | 2100 | 900 | -1200s (35min→15min) |

**理由**: 2100s (35min) 的breaker cooldown在R2286模型过滤修复后显得过长（breaker只影响glm5_2_nv，不再误杀dsv4p_nv）。缩减到900s (15min) 仍然足够给glm5_2_nv大输入问题一个冷却窗口，但大大缩短了breaker OPEN阻断时间。

**为什么单参数变更**: 只改`NVU_BIG_INPUT_COOLDOWN_S`，利用R2286的模型过滤修复确保dsv4p_nv不受影响。iron law: only HM1。

## 执行

```bash
sed -i '449s/- NVU_BIG_INPUT_COOLDOWN_S=2100/- NVU_BIG_INPUT_COOLDOWN_S=900  # R2288 .../' /opt/cc-infra/docker-compose.yml
docker compose -f /opt/cc-infra/docker-compose.yml up -d --no-deps --force-recreate nv_gw
```

## 验证

```
$ docker exec nv_gw env | grep NVU_BIG_INPUT_COOLDOWN_S
NVU_BIG_INPUT_COOLDOWN_S=900

$ curl -s -o /dev/null -w "%{http_code}" http://localhost:40006/health
200
```