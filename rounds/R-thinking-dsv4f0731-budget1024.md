# R-thinking: dsv4f0731_nv 启用 thinking:{type:enabled, budget:1024}

**Date**: 2026-08-12
**Hosts**: HM2 (40666) → HM1 (40006)
**Change type**: config.py inject thinking

## 改前数据

dsv4f0731_nv 思考深度探测 (9 组参数 × 2 轮, 详见 probe):

| 参数 | HTTP | reasoning_content |
|---|---|---|
| 无思考参数 | ✅ 200 | ❌ 0c |
| `thinking:{type:enabled}` | ✅ 200 | ✅ 376c |
| `thinking:{type:disabled}` | ❌ 529 | — |
| `reasoning_effort:low/medium/high` | ✅ 200 | ❌ 0c (只影响回答详细度) |
| `chat_template_kwargs:{enable_thinking:true}` | ✅ 200 | ✅ 393c |
| `thinking_budget:512/2048` (单独) | ❌ 400 | — |
| `thinking:{type:enabled,budget:256}` | ❌ timeout | — |
| **`thinking:{type:enabled,budget:1024}`** | **✅ 200** | **✅ 548c** |
| `thinking:{type:enabled,budget:4096}` | ✅ 200 | ✅ 960c (42s 延迟) |

结论: `thinking:{type:enabled,budget:1024}` 是最佳平衡 (思考 548c, 延迟 13.35s).

## 改动

`/opt/cc-infra/proxy/nv-gw/gateway/config.py` → `dsv4f0731_nv` 块:

```python
# BEFORE:
"strip_params": ["reasoning_effort", "stream_options", "thinking"],
"inject": {},

# AFTER:
"strip_params": ["reasoning_effort", "stream_options"],  # 移除 "thinking"
"inject": {"thinking": {"type": "enabled", "budget": 1024}},
```

- `strip_params` 移除 `"thinking"` — 客户端自带 thinking 参数不再被剥离
- `inject` 注入 `{"thinking":{"type":"enabled","budget":1024}}` — 客户端未发 thinking 时网关自动注入
- 其他模型 (dsv4p_nv, dsv4f_nv, glm5_2_nv) 不受影响

### 副作用 (预期)

`handlers.py:378` `is_thinking_req = bool(nvcf_cfg.get("inject"))` → 现在 inject 非空,
所有 dsv4f0731_nv 请求被识别为 thinking 请求, 获得 `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` (50s/55s)
扩展超时 (替代默认 45s). 这是正确的 — thinking 请求需要更多时间.

## 部署

### HM2 (40666) — 11:17 UTC
1. Backup: `config.py.bak.R-thinking`
2. Edit config.py (sed)
3. `docker restart dsvf0731_nv40666` (bind-mount, no rebuild)
4. Health: ✅ ok

### HM1 (40006) — 11:31 UTC
1. Backup: `config.py.bak.R-thinking`
2. Edit config.py (Edit tool, precise dsv4f0731_nv block only)
3. `docker restart nv_gw`
4. Health: ✅ ok

## 验证

### HM2 40666 E2E (5 rounds)

| r | status | latency | reasoning | content | ct |
|---|---|---|---|---|---|
| 1 | ✅ 200 | 27.55s | 806c | 792c | 521 |
| 2 | ✅ 200 | 18.08s | 675c | 712c | 456 |
| 3 | ✅ 200 | 104.95s | 651c | 599c | 408 |
| 4 | ✅ 200 | 23.27s | 453c | 719c | 389 |
| 5 | ✅ 200 | 15.12s | 375c | 607c | 331 |

SR=5/5=100%, 全部有 reasoning_content.

### HM1 40006 E2E (5 rounds)

| r | status | latency | reasoning | content | ct |
|---|---|---|---|---|---|
| 1 | ✅ 200 | 54.41s | 1066c | 747c | 538 |
| 2 | ✅ 200 | 15.36s | 1273c | 634c | 594 |
| 3 | ✅ 200 | 21.34s | 748c | 708c | 456 |
| 4 | ✅ 200 | 45.93s | 1646c | 680c | 661 |
| 5 | ✅ 200 | 41.45s | 2118c | 754c | 799 |

SR=5/5=100%, 全部有 reasoning_content.

### DB 对比 (HM2 40666)

| 期间 | n | SR | avg latency | avg output_tokens |
|---|---|---|---|---|
| BEFORE (2h before) | 36 | 77.8% | 46.88s | 1 |
| AFTER (post-deploy) | 5 | 100.0% | 37.79s | 421 |

output_tokens 从 ~1 → ~421: 明确证据 thinking 已生效 (思考链消耗大量 tokens).

### 日志确认

HM2 40666:
```
[NV-INJECT-THINKING] (dsv4f0731_nv) body had no thinking → injected thinking={'type': 'enabled', 'budget': 1024}
[NV-THINKING-TIMEOUT] (dsv4f0731_nv) thinking request stream=False → extended timeout 55s
```

HM1 40006:
```
[NV-INJECT-THINKING] (dsv4f0731_nv) body had no thinking → injected thinking={'type': 'enabled', 'budget': 1024}
[NV-THINKING-TIMEOUT] (dsv4f0731_nv) thinking request stream=False → extended timeout 50s
```

## 结论

✅ `thinking:{type:enabled,budget:1024}` 已成功部署到 HM2 (40666) 和 HM1 (40006).
- 网关自动注入 thinking 参数 (客户端无需修改)
- 所有 dsv4f0731_nv 请求现在都产生 reasoning_content
- SR=100% (5/5 on both hosts)
- 延迟 avg 15-55s (thinking 增加推理时间, 可接受)
