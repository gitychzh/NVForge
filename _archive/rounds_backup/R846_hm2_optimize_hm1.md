# R846: HM2→HM1 — 修 rr_counter glm5_2_nv 漏映射 (与 dsv4p_nv 共享 counter 瑕疵)

**Date**: 2026-07-08 04:15 UTC
**Author**: opc2_uname (HM2)
**Target**: HM1 (100.109.153.83) nv_gw
**Type**: CODE FIX (gateway/rr_counter.py, bind-mount, restart only)

---

## 改前数据 (铁律1)

### R845 修复后 metrics 恢复确认

R845 重启后真实 openclaw 批次 (04:03 UTC) 3 条入库:
```
04:03:21 glm5_2_nv 200 dur=13192 k2
04:03:35 glm5_2_nv 200 dur=6593  k3
04:03:42 glm5_2_nv 200 dur=2635  k4
```
**R845 metrics gap 修复确认** — DB/JSONL 恢复正常写入.

### 静默 except 审计 (R845 同类瑕疵排查)

| 文件 | bare_pass | 评估 |
|------|-----------|------|
| handlers.py | 9 | 全是 conn.close()/解析fallback, 合理低危 |
| db.py | 5 | R845 已修 _log_metrics 2处, 余为 _get_conn 内部 close |
| upstream.py | 3 | 全是 conn.close() 资源清理, 合理 |
| logger.py | 3 | R845 已修 2处 (_log 1处合理) |
| rr_counter.py | 2 | _save_rr_counter 已有 print; **_next_nv_key fallback 静默 — 真瑕疵** |

近 3h nv_tier_attempts 错误 = 0 行 (链路超健康, 无性能瓶颈可调).

### 真瑕疵: glm5_2_nv 漏映射 → 共享 dsv4p_nv counter

`rr_counter.py` 注释明说"三模型各自独立 RR counter key", 但 `_TIER_RR_KEYS` 只映射两个:

```python
_TIER_RR_KEYS = {
    "kimi_nv": "nv_kimi",
    "dsv4p_nv": "nv_dsv4p",
    # glm5_2_nv 漏了!
}
def _next_nv_key(tier_model):
    rr_key = _TIER_RR_KEYS.get(tier_model, "nv_dsv4p")  # ← glm5_2_nv fallback 到 nv_dsv4p
```

**数据印证**: `rr_counter.json = {"nv_dsv4p": 2145, "nv_kimi": 13}`.
- nv_dsv4p=2145 主要由 glm5_2_nv 推进 (dsv4p_nv 极少用, 仅 fallback 时触发)
- glm5_2_nv 是 openclaw primary (高频), 却与 dsv4p_nv **共享 counter**, 互相干扰 key 轮转位置
- 这是 R845 静默吞异常的同类瑕疵: 静默 fallback, 不可见

---

## 改动 (2 编辑点, 1 文件, ≤5)

### 1. `gateway/rr_counter.py` — `_TIER_RR_KEYS` 补 glm5_2_nv

```python
_TIER_RR_KEYS = {
    "kimi_nv": "nv_kimi",
    "dsv4p_nv": "nv_dsv4p",
    "glm5_2_nv": "nv_glm5_2",   # R846: 补独立 key
}
```

### 2. `gateway/rr_counter.py` — `_next_nv_key` fallback 加告警 (防未来遗漏)

```python
_UNKNOWN_TIER_WARNED = set()

def _next_nv_key(tier_model):
    rr_key = _TIER_RR_KEYS.get(tier_model)
    if rr_key is None:
        # R846: 未映射 tier 不再静默 fallback 到 nv_dsv4p, 按名生成独立 key + 一次性告警
        rr_key = f"nv_{tier_model}"
        if tier_model not in _UNKNOWN_TIER_WARNED:
            _UNKNOWN_TIER_WARNED.add(tier_model)
            print(f"[NV-RR] WARN tier '{tier_model}' not in _TIER_RR_KEYS; ...", ...)
    ...
```

---

## 备份

- `gateway/rr_counter.py.bak.R846`

## 部署

```bash
scp -P 222 rr_counter.py → HM1 /opt/cc-infra/proxy/nv-gw/gateway/
docker restart nv_gw
```

## 改后验证 (铁律2)

### 启动
| 检查 | 结果 |
|------|------|
| `curl /health` | ok |
| 启动日志 | `[NV-RR] restored ... {'nv_dsv4p': 2145, 'nv_kimi': 13}` 无 WARN (glm5_2_nv 已映射) |
| traceback | 0 |

### 真实最小请求验证 (R845 + R846 双重)
发 `glm5_2_nv stream=false max_tokens=8` 测试请求:
- 响应: `"Okay."` 200, prompt=11/completion=3 ✓
- **DB**: 新增 `04:14:06 glm5_2_nv 200 dur=9503 k0` → R845 metrics 持续恢复 ✓
- **rr_counter.json**: `{"nv_dsv4p": 2145, "nv_kimi": 13, "nv_glm5_2": 1}` ✓
  - **nv_glm5_2 出现且=1** (glm5_2_nv 用独立 counter)
  - **nv_dsv4p 保持 2145** (未被 glm5_2_nv 推进, 独立性确认)

---

## 预期效果

- glm5_2_nv key 轮转独立持久化, 不再与 dsv4p_nv 互相干扰.
- 未来新增 tier 若漏映射, `[NV-RR] WARN` 一次性告警, 不再静默共享 (R845 同类防护).

## 回滚预案

```bash
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra/proxy/nv-gw/gateway && \
  cp rr_counter.py.bak.R846 rr_counter.py && docker restart nv_gw'
```
