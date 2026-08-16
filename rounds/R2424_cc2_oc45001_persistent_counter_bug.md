# R2424 — oc45001 PersistentCounter `next()` bug fix

**时间**: 2026-08-16 10:55 UTC+8
**触发**: hermes 报错 "primary 和 fallback 均不可用"

## 诊断

### 报错来源
- 报错来自 **openclaw 链路** (opclaw4103), 不是 cc2 主链路 (cc4101→nv_gw)
- cc4101→nv_gw 主链路完全正常: 6h 45 请求全 200, SR 100%

### 根因链
1. **opclaw4103 primary (oc45001)**: 502 `'PersistentCounter' object is not an iterator`
   - oc45001 代理代码 bug: `rot_state.py` R8 更新引入 `PersistentCounter` 类替代 `itertools.count`
   - `PersistentCounter` 实现 `.next()` 方法但**没有 `__next__` dunder**
   - `handlers.py:356` 和 `egress_health.py:113` 仍用 `next(counter)` 内置函数调用
   - `next()` 需要 `__next__`, `PersistentCounter` 没实现 → TypeError → 502
   - **每个请求都触发**, oc45001 完全不可用

2. **opclaw4103 fallback (dsv4f0731_nv40666)**: 502 `all_tiers_exhausted`
   - NVCF `deepseek-v4-flash-0731` (fid 281478d0) 后端返回 200 + Content-Length:0 空响应
   - 5 key 轮转全部空 200, 连续 3 次 fast-break → all_tiers_exhausted
   - NVCF 后端问题, 不可侧修复

3. **结果**: primary 502 + fallback 502 → "primary 和 fallback 均不可用"

## 修复

### 文件 1: `handlers.py:356`
```diff
- return next(_proxy_counter) % n
+ return _proxy_counter.next() % n
```

### 文件 2: `egress_health.py:113`
```diff
- start = next(_rot) % k
+ start = _rot.next() % k
```

### 备份
- `handlers.py.bak.R2424`
- `egress_health.py.bak.R2424`

## 验证

### oc45001 直接测试
```
curl → 200 OK, 2.4s (big-pickle model)
```

### openclaw4103 端到端
```
curl opclaw4103 → 200 OK, 8.5s (primary→oc45001→opencode.ai)
```

### cc2 主链路确认
```
cc4101→nv_gw → 200 OK, 17s (glm5_2_nv)
nv_gw 6h: 45/45 = 100% SR
cc4101 6h: 46/46 = 100% SR (0 failures)
```

## 影响范围
- openclaw 链路 (opclaw4103) 全面恢复
- cc2 主链路未受影响 (一直正常)
- dsv4f0731_nv40666 fallback 的 NVCF 空响应问题持续存在但属后端问题

## 下一步
- 监控 openclaw 链路下个窗口稳定性
- 40666 NVCF 空响应问题保持观察 (NOP, 等 NVCF 自愈)
- 可以考虑给 PersistentCounter 加 `__next__` dunder 作为更彻底的修复 (但当前 `.next()` 修复已足够)
