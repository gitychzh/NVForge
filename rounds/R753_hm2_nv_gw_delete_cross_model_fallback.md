# R753: HM2 nv_gw 删除跨 model fallback (FALLBACK_GRAPH)

> 日期: 2026-07-05  机器: HM2 (实验床)  前置: R750-R752 (5 agent 41xx 适配器全解耦)
> **HM1 全程未动** (本地生产冻结)

## 背景

R750-R752 完成 5 agent → 41xx 适配器全解耦后, 41xx 适配器内部已做跨后端同模型 fallback
(nv_gw→ms_gw, 保持模型一致)。nv_gw 内部的 FALLBACK_GRAPH (跨 model fallback, 如
glm5_2_nv→dsv4p_nv) 变成重复且有害: 它会让 agent 看到的模型不一致 (glm5.2 请求可能
返回 dsv4p 输出), 违反"一个 agent 一个模型"的模型一致性原则。

用户决策: 删 nv_gw FALLBACK_GRAPH (A 类跨模型 fallback), 保留 func_health (B 类 intra-model
function 选择) + PEER-FB (跨机同 model) + key cooldown (B 类)。

## 删除范围

### config.py
- 删 `FALLBACK_GRAPH = {"glm5_2_nv": ["dsv4p_nv"]}` 字典
- 删 `FALLBACK_HEALTH_THRESHOLD` (只 FALLBACK_GRAPH 用, dead import)
- 改成注释说明 R753 删除原因

### upstream.py
- 删 import `FALLBACK_GRAPH, FALLBACK_HEALTH_THRESHOLD`
- 删 `for alt in FALLBACK_GRAPH.get(mapped_model, []):` 循环 (8 行)
- 删 `if len(tier_order) > 1:` 双分支日志
- 固化 `tier_order = [mapped_model]` (单 tier)
- 保留 `func_health.select_healthy_function` (intra-model, line 423) 和 `func_health.record_result` (line 888)

### 保留 (B 类, 不删)
- `func_health.py` 整个文件 (intra-model function 选择: 同 model 多 function_id 时选健康度高的)
- `PEER-FB` 跨机 fallback (handlers.py `_peer_fallback`, NVU_PEER_FALLBACK_URL 指向 HM1)
- `key cooldown` (per-key 429/timeout 冷却)
- `func_health.record_result` (记录 function 健康度, 供 select_healthy_function 用)

## 验收

### tier_chain 单 model (核心验证)
```
[NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=False tier_chain=['glm5_2_nv'] (no cross-model fallback, R753)
[NV-ALL-TIERS-FAIL] All 1 tiers failed (ring tiers tried: ['glm5_2_nv']), elapsed=110053ms, ABORT-NO-FALLBACK
```
- 之前: `All 2 tiers failed (ring tiers tried: ['glm5_2_nv', 'dsv4p_nv'])` (跨 model 切了 dsv4p)
- 现在: `All 1 tiers failed` (单 model, 不跨 model)

### B 类功能保留完好
- `func_health.select_healthy_function` (line 423): kimi_nv 请求成功, NV-SUCCESS 1.6s ✅
- `func_health.record_result` (line 888): 记录 function 健康度 ✅
- `PEER-FB`: `[NV-PEER-FB] peer fallback OK: status=200 bytes=1629 ttfb=0ms` ✅
- `key cooldown`: NV-TIMEOUT/429 后 per-key 冷却 ✅

### 41xx fallback 链路不受影响
- opclaw4103: nv_gw glm5_2_nv 5xx → 切 ms_gw, reminder 注入 (R752 已验证, 链路不变)
- nv_gw 返 5xx 后 41xx 接管跨后端 fallback (同模型, 保持模型一致)

## 模型一致性恢复

删除前: agent 发 glm5_2_nv 请求, nv_gw 全挂时悄悄切 dsv4p_nv, agent 收到 dsv4p 输出 (思考质量/风格全变).
删除后: agent 发 glm5_2_nv, nv_gw 单 model 全挂返 5xx, 41xx 切 ms_gw/glm5_2_ms (同模型, 思考质量一致).

## 备份

- `config.py.bak.R753`, `upstream.py.bak.R753` (HM2 `/opt/cc-infra/proxy/nv-gw/gateway/`)
- bind-mount, `docker restart nv_gw` 即生效 (无需 rebuild)

## 验证清单

- [x] config.py: FALLBACK_GRAPH + FALLBACK_HEALTH_THRESHOLD 删除, ast.parse 通过
- [x] upstream.py: import 删 + tier_order 循环删, ast.parse 通过
- [x] nv_gw restart 成功, /health 200
- [x] NV-REQ tier_chain=['glm5_2_nv'] 单 model
- [x] NV-ALL-TIERS-FAIL "All 1 tiers failed" (不再跨 model)
- [x] func_health.select_healthy_function 保留, kimi 请求成功
- [x] PEER-FB 保留, peer fallback OK 200
- [x] HM1 全程未动 (HM1 仍有自己的 FALLBACK_GRAPH, 待 HM1 同步时一起改)
