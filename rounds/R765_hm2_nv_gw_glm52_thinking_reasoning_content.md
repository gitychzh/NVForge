# R765: HM2 nv_gw glm5_2_nv thinking content=null 不再误判 empty_200

> 根因: glm5_2_nv thinking 模式下 content=null, 思考输出在 reasoning_content.
> _check_empty_200 把 content is None 误判 empty_200 → cycle → ALL-TIERS-FAIL → 502.
> 修复: content=null 时检查 reasoning_content, 有内容则视为有效.

## 改前数据 (10min)

### glm5_2_nv 连续 NV-ALL-TIERS-FAIL (empty200=2)
```
02:06:32 [NV-TIER-FAIL] glm5_2_nv all 5 keys failed: empty200=2, elapsed=21522ms
02:07:41 [NV-TIER-FAIL] glm5_2_nv all 5 keys failed: empty200=2, elapsed=3275ms
02:08:06 [NV-TIER-FAIL] glm5_2_nv all 5 keys failed: empty200=2, elapsed=10483ms
02:08:17 [NV-TIER-FAIL] glm5_2_nv all 5 keys failed: empty200=2, elapsed=5980ms
```
EMPTY_200_FASTBREAK=2 → 2 次 empty 即 fast-break abort.

### 根因 (直接测 5 key pexec glm5_2_nv thinking 非流式)
```
k1: status=200 content=None reasoning_content='1. **分析输入...**' finish_reason=length
k2: status=200 content=None reasoning_content='1. **分析输入...**' finish_reason=length
k3: status=403 Forbidden
k4: status=200 content=None reasoning_content='1. **分析输入...**' finish_reason=length
k5: status=200 content=None reasoning_content='1. **分析输入...**' finish_reason=length
```
NVCF glm5.2 thinking 模式: 思考阶段输出在 reasoning_content, content 为 null 直到思考结束.
max_tokens 不足时思考被截断 (finish_reason=length), content 始终为 null.
_check_empty_200 line 104: `if content is None: return True` → 误判 empty_200.

### 影响
openclaw primary=glm5_2_nv, thinking 请求非流式时全挂 (502). peer-fb 兜底但慢.

## 改动 (pexec.py _check_empty_200)

| 项 | 改前→改后 | 理由 |
|---|---|---|
| content is None 判断 | 直接 return True (empty) | 误杀 thinking 响应 |
| content is None (改后) | 检查 reasoning_content, 有内容则 return False (有效) | thinking 模式正常响应 |

### 代码
```python
content = msg.get("content")
if content is None:
    reasoning = msg.get("reasoning_content")
    if reasoning:
        _log("NV-THINKING-OK", f"... content=null but reasoning_content present ({len} chars), treating as valid")
        return False
    _log("NV-EMPTY-200", f"... content=null and no reasoning_content")
    return True
```

### 不改
- stream 路径 (流式 thinking 不走这里, Content-Length:0 仍是 empty)
- 429/timeout/auth-fail 逻辑 (R762/R764 保留)
- nv_gw/ms_gw 其他逻辑 (模块化)
- HM1 (冻结)
- 41xx 适配器 (不受影响)
- 不改 max_tokens (agent 自己的事, openclaw 配置)

## 改后验证

### 3 个非流式 thinking 请求全 200 OK
```
req1: 200 7.5s, req2: 200 14.9s, req3: 200 11.7s
```

### NV-THINKING-OK 日志确认
```
02:12:00 [NV-THINKING-OK] k4 → content=null but reasoning_content present (410 chars), treating as valid
02:12:00 [NV-SUCCESS] tier=glm5_2_nv k4 succeeded after 1 cycle attempts
02:12:15 [NV-THINKING-OK] k4 → reasoning_content present (436 chars)
02:12:26 [NV-THINKING-OK] k5 → reasoning_content present (405 chars)
```

### 完整响应透传
```
content: None
reasoning_content: '1. **分析输入...**'
finish_reason: length
```
(content=null 透传给 openclaw, 由 agent 自行处理 — nv_gw 职责是不误杀, 不是补 content)

### NV-ALL-TIERS-FAIL 改后 2min: 0 次 (改前 10min 4 次)
### DB 改后 5min: 10 成功 / 0 个 502 (100% SR)

## 预期
- openclaw 非流式 thinking 请求不再 502
- glm5_2_nv empty_200 只在真无内容 (content=null + reasoning_content=null) 时触发
- NV-THINKING-TIMEOUT 日志仍记录 (thinking 请求识别), 但不再误判 empty

## 风险
- 低: reasoning_content 有内容 = 思考确实在进行, 非空响应
- content=null 透传: openclaw 收到 content=null 可能需要自己处理 (加大 max_tokens 或流式), 但这是 agent 侧
- 回滚: pexec.py.bak.R765

## 遗留
- k3 NVAPI key 待用户换 (R762/R764 已隔离)
- HM1 同步待授权 (HM1 glm5_2_nv 同问题)
- ms_gw stream_no_data cycle (非阻塞)
- openclaw thinking max_tokens 不足致 content=null (agent 侧, 非 nv_gw)
