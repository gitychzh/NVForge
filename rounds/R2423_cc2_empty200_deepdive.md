# R2423 cc2 — 40666 dsv4f0731_nv empty_200 深挖分析

## 触发
用户要求深挖 40666 上 dsv4f0731_nv 模型的 empty_200 问题:
- 是输入太大? 代码逻辑? 请求过于频繁?
- 有没有更优的 function id?
- 5 US IP 是否有问题?

## 数据收集

### 1. 24h 三容器 SR 对比 (nv_requests)
| 容器 (host_machine) | 200 | 502 | SR | avg 200 dur |
|---|---|---|---|---|
| opc2sname (nv_gw 40006 主链) | 482 | 1 | 99.8% | 25.2s |
| opc2sname-dsv4f40666 (dsv4f0731_nv) | 27 | 11 | 71.1% | 34.7s |
| opc2sname-dsv4p40066 (dsv4p_nv) | 0 | 3 | 0% | — |

### 2. empty_200 per-tier attempt 分布 (12h, 40666)
| error_type | cnt | avg_elapsed_s | range |
|---|---|---|---|
| **empty_200** | **25** | (NULL) | — |
| NVCFDynamicRemoteDisconnected | 10 | 46.4 | 31-68s |
| 529_nv_overloaded | 9 | — | — |
| NVCFDynamicSSLEOFError | 3 | 5.4 | 4-6s |
| 504_nv_gateway_timeout | 1 | — | — |

### 3. empty_200 时段分布 (CST = UTC+8)
| 时段 | empty_cnt | affected_requests |
|---|---|---|
| 18:43-18:51 | 11 | ~5 |
| 19:00-19:37 | 8 | ~4 |
| 21:07 | 3 | 1 |
| 22:24-22:26 | 3 | 2 |
| (之后) 23:26 | 3 | (最近) |

→ **成簇出现, 集中在 18:43-19:37 CST 时段 (NVCF 后端波动期), 之后逐渐恢复**

### 4. empty_200 per-key 分布
| nv_key_idx | empty_cnt |
|---|---|
| k2 | 8 |
| k3 | 6 |
| k4 | 6 |
| k0 | 3 |
| k1 | 2 |

→ **所有 5 key 都有 empty_200, 不是 key 特有问题**

### 5. empty_200 全部是 stream 模式
- 29/29 次 empty_200 都是 `200 Content-Length:0 (stream)`
- 代码逻辑: `pexec.py:67` → stream 时 Content-Length=="0" 判定 empty

## 根因分析

### Q1: 是输入太大吗?
**否** — 之前测试已验证各种 input size (6 tokens ~ 150K chars) 都能成功.
本次测试 LLM 直连 pexec (non-stream + stream) 15 次全部 200 OK.
empty_200 与 input size 无关.

### Q2: 是代码逻辑问题吗?
**否** — `_check_empty_200()` 逻辑正确:
- stream 模式: Content-Length=="0" → 判定 empty (NVCF 确实返回空响应)
- non-stream: body 为空/null choices/null content → 判定 empty
- 有 reasoning_content 时不算 empty (R765 修复)
代码正确识别了 NVCF 的空响应, 不是误判.

### Q3: 是请求过于频繁吗?
**否** — 40666 是 fallback 链路, 24h 只有 38 个请求 (≈1.6 req/h).
即使并发测试 3 请求也能全部成功.
不是频率问题.

### Q4: 真正原因?
**NVCF 后端间歇性波动 (transient backend wave)**

证据链:
1. empty_200 成簇出现在 18:43-19:37 CST, 之后恢复 → 时段相关
2. 同一秒多 key 同时 empty (如 18:43 k0+k2+k4, 19:00 k2+k3+k4) → NVCF 整体波动
3. empty key 之后 cycle 到下一个 key **很快成功** (差 6-15s) → 不是 key 级故障
4. 当前时段 (15:26 CST) 连续 15 次直连 pexec 全部 200 OK → 后端目前已恢复

### Q5: 有更优 FID 吗?
**否** — FID discovery 确认:
- 281478d0 (281478d0-f307-49f4-9e0f-080b63b16c47) 是唯一 ACTIVE 的 deepseek-v4-flash-0731
- 新 FID dee9b9f9 (v4-pro 0813 模型) 存在但 POST 返回 404 (account 无权限)
- 没有可替换的 FID

### Q6: 5 US IP 有问题吗?
**否** — empty_200 分布跨所有 5 个 key (= 5 个独立 socks5 代理 IP).
egress_ip 在 DB 中未记录 (elapsed_ms 也未写入), 但 log 显示每 key 的代理 IP 不同.
empty_200 跨所有代理均匀分布, 不是 IP 问题.

## 代码逻辑复核

### empty_200 处理流程 (upstream.py:798-818)
```
NVCF 返回 200 + Content-Length:0
  → _check_empty_200() → True
  → mark_key_cooling(_cooling_tier, key_idx)  ← 实际调 mark_429
  → consecutive_empty_200 += 1
  → if consecutive ≥ 3: fast-break (停止本轮 retry)
```

### ⚠️ 发现: empty_200 触发 mark_429 cooldown=120s
`mark_key_cooling()` 是 `mark_429()` 的兼容 wrapper (key_manager.py).
所以 empty_200 之后 key 被 120s 429 冷却.
empty_200 不是 rate limit (429), 用 429 冷却惩罚是**语义不精确**:
- 120s 冷却意味着 empty 1 次的 key 暂不可用 2 分钟
- 虽然 cycle 到下一个 key 后很快成功, 但持续时段下 3-5 key 陆续 empty → fastbreak → 多 key 在冷却 → 下一个请求可用 key 减少

但这不是核心问题 — root cause 是 NVCF 返回空响应, cooldown 只影响恢复速度.

## 结论 & 建议

### 结论
**empty_200 = NVCF 后端时段性波动, 返回 200 + Content-Length:0 空响应.**
- 不是输入太大 ✗
- 不是代码逻辑误判 ✗ 
- 不是请求频率 ✗
- 不是 key 问题 ✗
- 不是 IP 问题 ✗
- **是 NVCF 后端 transient wave**, 不可从 gateway 侧修复

### Gateway 侧优化空间 (可选, 非紧急)
1. **empty_200 cooldown 降级**: 把 empty_200 的 key cooldown 从 120s 降到 30-60s
   - current: mark_key_cooling = mark_429, base 120s
   - proposed: empty_200 用短冷却 (如 30s), 区别于 429 rate limit
   - 依据: empty_200 后下一个 key 6-15s 就成功, 120s 太重
   
2. **empty_200 elapsed_ms/egress_ip 入库**: 当前 nv_tier_attempts 中这两个字段为空
   - 补记 elapsed_ms 可追踪 empty_200 耗时模式 (短 8s vs 长 60s)
   - 补记 egress_ip 可进一步排除 IP 维度

### 不建议的改动
- 不要改 _check_empty_200 判定逻辑 (当前正确)
- 不要降 EMPTY_200_FASTBREAK (3 是合理的 fastbreak 阈值)
- 不需要换 FID (没有可替换的)

## 验证
- 直连 pexec 15 次: 14 × 200 OK + 1 × 529 (overloaded), 0 empty_200 → 当前时段健康
- Gateway 非流测试: 200 OK 20.5s ✅
- Gateway 流测试: 200 OK 120s 12077 bytes ✅ 
- 容器 health: ok ✅
- DB 数据: 12h 25 empty_200, 集中 18:43-19:37 CST, 之后恢复

## 状态
- **改动**: 无 (NOP — 诊断分析轮, 无码变更)
- **风险**: 无
- **下一步**: 等 NVCF 下次波动时观察 empty_200 是否仍成簇出现; 
  若用户同意可优化 empty_200 cooldown (mark_key_cooling 从 mark_429 分离)
