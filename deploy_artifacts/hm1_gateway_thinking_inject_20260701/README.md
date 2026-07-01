# HM1 hm40006 三模型 pass-through + per-model 思考注入 (2026-07-01, 最终版)

## 背景 (演进)

本目录前身为"单 dsv4p_nv 思考注入" (dynamo ee2b0de2 时代)。dynamo 下架后经多轮抓包,
演进为 **三模型 pass-through, 每 agent 各对应一真实 NVCF 后端, 各后端思考触发参数不同**。

## 三模型路由 (config.py NVCF_PEXEC_MODELS)

| 内部 model | function_id | NVCF name | 后端 model | agent | strip_params | inject |
|---|---|---|---|---|---|---|
| kimi_nv   | f966661c-... | nvquery-kimi-k2_6 | moonshotai/kimi-k2.6 | hermes | thinking_budget | reasoning_effort:medium |
| dsv4p_nv  | 8915fd28-... | sglang-deepseek-v4-pro | deepseek-ai/deepseek-v4-pro | openclaw | (空) | reasoning_effort:medium |
| glm5_1_nv | 6155636e-... | ai-glm-5_1 | z-ai/glm-5.1 | opencode | thinking_budget,reasoning_effort,thinking | chat_template_kwargs:{enable_thinking:true} |

`tier_order=[mapped_model]` 单元素, 删跨 tier fallback (每 agent 锁定自己的后端)。

## 思考触发抓包结论 (2026-07-01 key1 直连 NVCF 完整 dump)

每个 function 思考触发参数各不相同, 不能假设统一:

- **deepseek sglang 8915fd28**: 触发=`reasoning_effort`, 内容=`reasoning_content`,
  非流式+流式逐块都非空 (rc 174-343). `thinking:{type:enabled}` 无效 (200 但 rc 空).
- **glm5.1 6155636e**: 触发=`chat_template_kwargs:{enable_thinking:true}` (glm 原生, 非 reasoning_effort!),
  内容同 `reasoning_content` (rc 1388-1757). `reasoning_effort` 任何合法值 → 200 但 rc 恒空; =max → 400.
  `thinking:{type:enabled}` → 400 拒收.
- **kimi f966661c**: 最宽松, 三种触发 (`reasoning_effort` / `thinking:{type:enabled}` /
  `chat_template_kwargs`) 都接受 (rc 878-3193). 用 reasoning_effort 与 deepseek 对齐.

教训: NVCF 每个 function 思考触发参数各异, 必须逐个完整 dump 抓包 (max_tokens≥500 + 推理题 + 全字段).

## 改动 (相对单 dsv4p 坍缩态)

1. **config.py**: `inject_thinking:bool` → per-model `inject:dict` (声明式, 可扩展).
   三模型 NVCF_PEXEC_MODELS 条目; header 注释记录抓包结论.
2. **pexec.py** `_build_pexec_body`: 通用化注入, 遍历 `inject` dict, 客户端已自带该参数则不覆盖.
   注入在 strip 之后 (glm5.1 strip 掉无效的 reasoning_effort, 再 inject 正确的 chat_template_kwargs).
3. **handlers.py** (~L184-197): thinking-timeout override. 旧代码只给 force_stream_upgrade 55s,
   原生流式思考请求撞 25s UPSTREAM_TIMEOUT → 502. 加 `elif is_thinking_req` 分支让原生流式也拿 55s.
   `is_thinking_req = bool(nvcf_cfg.inject) or body 有 reasoning_effort/chat_template_kwargs/thinking`.

## 铁律

HM1 自改 hm40006 源码 — 跨铁律 "只改对端不改自己". 先例: hm1-mihomo-removed / bindmount-rename-dsv4p /
auth-layer. 理由: 三 agent 共用本机 hm40006, 网关侧 per-model 声明式注入比改各 agent 配置更干净
且单一信源; 对 openclaw 自带 thinking 是 no-op. 由 cc2 (HM2) 双轮核对全路径真生效.

## 部署

hm40006 bind-mount gateway 源码 → 改 .py 只需 `docker restart hm40006` (无需 rebuild).
backup: pexec.py.bak / config.py.bak / handlers.py.bak (改前各留一份).

## 端到端验证 (2026-07-01, 经 cc2 双轮核对)

网关 streaming 三模型思考全 ✅:
- kimi_nv:   t=12.8s rc=2254 ★ ("The user is asking a classic riddle...")
- dsv4p_nv:  t=6.0s  rc=333  ★ ("We are asked:...")
- glm5_1_nv: 3/3 ★ (rc 1192-1348, t=22-34s; 偶发 502 是 TIER_TIMEOUT_BUDGET=60s cap 运营问题非代码 bug)

cc2 裁决: 全路径真生效 11/13, 0/13 旧 25s 502. 剩余 2/13 glm5.1 502 = 60s tier budget 限制重试,
重试即恢复, 非代码缺陷 (cc2 建议未来为 thinking 请求单独抬 tier budget, 待议).

## 文件

- `config.py`  — NVCF_PEXEC_MODELS 三模型 + inject dict + 抓包注释
- `pexec.py`   — `_build_pexec_body` 通用注入逻辑
- `handlers.py` — thinking-timeout override 分支
